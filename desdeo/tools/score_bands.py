"""Use the auto_SCORE function to generate the SCORE bands visualization.

This module contains the functions which generate SCORE bands visualizations. It also contains functions to calculate
the order and positions of the objective axes, as well as a heatmap of correlation matrix.

To run the SCORE bands visualization, use the `score_json` function to generate the data for the visualization, and then
use the `plot_score` function to generate the figure. You can also pass the result of `score_json` to other frontends
for visualization.
"""

import itertools
from copy import deepcopy
from enum import Enum
from typing import Literal
from warnings import warn

import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go
import polars as pl
from matplotlib import cm
from pydantic import BaseModel, ConfigDict, Field
from scipy.stats import pearsonr
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from tsp_solver.greedy import solve_tsp


class GMMOptions(BaseModel):
    """Options for Gaussian Mixture Model clustering algorithm."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(default="GMM")
    """Gaussian Mixture Model clustering algorithm."""
    scoring_method: Literal["BIC", "silhouette"] = Field(default="silhouette")
    """Scoring method to use for GMM. Either "BIC" or "silhouette". Defaults to "silhouette".
        This option determines how the number of clusters is chosen."""


class DBSCANOptions(BaseModel):
    """Options for DBSCAN clustering algorithm."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(default="DBSCAN")
    """DBSCAN clustering algorithm."""


class KMeansOptions(BaseModel):
    """Options for KMeans clustering algorithm."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(default="KMeans")
    """KMeans clustering algorithm."""
    n_clusters: int = Field(default=5)
    """Number of clusters to use. Defaults to 5."""


class DimensionClusterOptions(BaseModel):
    """Options for clustering by one of the objectives/decision variables."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(default="DimensionCluster")
    """Clustering by one of the dimensions."""
    dimension_name: str
    """Dimension to use for clustering."""
    n_clusters: int = Field(default=5)
    """Number of clusters to use. Defaults to 5."""
    kind: Literal["EqualWidth", "EqualFrequency"] = Field(default="EqualWidth")
    """Kind of clustering to use. Either "EqualWidth", which divides the dimension range into equal width intervals,
        or "EqualFrequency", which divides the dimension values into intervals with equal number of solutions.
        Defaults to "EqualWidth"."""


class CustomClusterOptions(BaseModel):
    """Options for custom clustering provided by the user."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(default="Custom")
    """Custom user-provided clusters."""
    clusters: list[int]
    """List of cluster IDs (one for each solution) indicating the cluster to which each solution belongs."""


ClusteringOptions = GMMOptions | DBSCANOptions | KMeansOptions | DimensionClusterOptions | CustomClusterOptions


class DistanceFormula(int, Enum):
    """Distance formulas supported by SCORE bands. See the paper for details."""

    FORMULA_1 = 1
    FORMULA_2 = 2


class SCOREBandsConfig(BaseModel):
    """Configuration options for SCORE bands visualization."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    dimensions: list[str] | None = Field(default=None)
    """List of variable/objective names (i.e., column names in the data) to include in the visualization.
        If None, all columns in the data are used. Defaults to None."""
    descriptive_names: dict[str, str] | None = Field(default=None)
    """Optional dictionary mapping dimensions to descriptive names for display in the visualization.
        If None, the original dimension names are used. Defaults to None."""
    units: dict[str, str] | None = Field(default=None)
    """Optional dictionary mapping dimensions to their units for display in the visualization.
        If None, no units are displayed. Defaults to None."""
    axis_positions: dict[str, float] | None = Field(default=None)
    """Dictionary mapping objective names to their positions on the axes in the SCORE bands visualization. The first
        objective is at position 0.0, and the last objective is at position 1.0. Use this option if you want to
        manually set the axis positions. If None, the axis positions are calculated automatically based on correlations.
        Defaults to None."""
    clustering_algorithm: ClusteringOptions = Field(
        default=DBSCANOptions(),
    )
    """
    Clustering algorithm to use. Currently supported options: "GMM", "DBSCAN",
        and "KMeans". Defaults to "DBSCAN".
    """
    distance_formula: DistanceFormula = Field(default=DistanceFormula.FORMULA_1)
    """Distance formula to use. The value should be 1 or 2. Check the paper for details. Defaults to 1."""
    distance_parameter: float = Field(default=0.05)
    """Change the relative distances between the objective axes. Increase this value if objectives are placed too close
        together. Decrease this value if the objectives are equidistant in a problem with objective clusters. Defaults
        to 0.05."""
    use_absolute_correlations: bool = Field(default=False)
    """Whether to use absolute value of the correlation to calculate the placement of axes. Defaults to False."""
    include_solutions: bool = Field(default=False)
    """Whether to include individual solutions. Defaults to False. If True, the size of the resulting figure may be
        very large for datasets with many solutions. Moreover, the individual traces are hidden by default, but can be
        viewed interactively in the figure."""
    include_medians: bool = Field(default=False)
    """Whether to include cluster medians. Defaults to False. If True, the median traces are hidden by default, but
        can be viewed interactively in the figure."""
    interval_size: float = Field(default=0.95)
    """The size (as a fraction) of the interval to use for the bands. Defaults to 0.95, meaning that 95% of the
    middle solutions in a cluster will be included in the band. The rest will be considered outliers."""
    scales: dict[str, tuple[float, float]] | None = Field(default=None)
    """Optional dictionary specifying the min and max values for each objective. The keys should be the
        objective names (i.e., column names in the data), and the values should be tuples of (min, max).
        If not provided, the min and max will be calculated from the data."""


class SCOREBandsResult(BaseModel):
    """Pydantic/JSON model for representing SCORE Bands."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    options: SCOREBandsConfig
    """Configuration options used to generate the SCORE bands."""
    ordered_dimensions: list[str]
    """List of variable/objective names (i.e., column names in the data).
        Ordered according to their placement in the SCORE bands visualization."""
    clusters: list[int]
    """List of cluster IDs (one for each solution) indicating the cluster to which each solution belongs."""
    axis_positions: dict[str, float]
    """Dictionary mapping objective names to their positions on the axes in the SCORE bands visualization. The first
        objective is at position 0.0, and the last objective is at position 1.0."""
    bands: dict[int, dict[str, tuple[float, float]]]
    """Dictionary mapping cluster IDs to dictionaries of objective names and their corresponding band
        extremes (min, max)."""
    medians: dict[int, dict[str, float]]
    """Dictionary mapping cluster IDs to dictionaries of objective names and their corresponding median values."""
    cardinalities: dict[int, int]
    """Dictionary mapping cluster IDs to the number of solutions in each cluster."""


def _gaussianmixtureclusteringwithBIC(data: pl.DataFrame) -> np.ndarray:
    """Cluster the data using Gaussian Mixture Model with BIC scoring."""
    data_copy = data.to_numpy()
    data_copy = StandardScaler().fit_transform(data_copy)
    lowest_bic = np.inf
    bic = []
    n_components_range = range(1, min(11, len(data_copy)))
    cv_types: list[Literal["full", "tied", "diag", "spherical"]] = ["spherical", "tied", "diag", "full"]
    for cv_type in cv_types:
        for n_components in n_components_range:
            # Fit a Gaussian mixture with EM
            gmm = GaussianMixture(n_components=n_components, covariance_type=cv_type)
            gmm.fit(data_copy)
            bic.append(gmm.score(data_copy))
            # bic.append(gmm.bic(data))
            if bic[-1] < lowest_bic:
                lowest_bic = bic[-1]
                best_gmm = gmm

    return best_gmm.predict(data_copy)


def _gaussianmixtureclusteringwithsilhouette(data: pl.DataFrame) -> np.ndarray:
    """Cluster the data using Gaussian Mixture Model with silhouette scoring."""
    X = StandardScaler().fit_transform(data.to_numpy())
    best_score = -np.inf
    best_labels = np.ones(len(data))
    n_components_range = range(1, min(11, len(data)))
    cv_types: list[Literal["full", "tied", "diag", "spherical"]] = ["spherical", "tied", "diag", "full"]
    for cv_type in cv_types:
        for n_components in n_components_range:
            # Fit a Gaussian mixture with EM
            gmm = GaussianMixture(n_components=n_components, covariance_type=cv_type)
            labels = gmm.fit_predict(X)
            try:
                score = silhouette_score(X, labels, metric="cosine")
            except ValueError:
                score = -np.inf
            if score > best_score:
                best_score = score
                best_labels = labels
    # print(best_score)
    return best_labels


def _DBSCANClustering(data: pl.DataFrame) -> np.ndarray:
    """Cluster the data using DBSCAN with silhouette scoring to choose eps."""
    X = StandardScaler().fit_transform(data.to_numpy())
    eps_options = np.linspace(0.01, 1, 20)
    best_score = -np.inf
    best_labels = np.ones(len(data))
    for eps_option in eps_options:
        db = DBSCAN(eps=eps_option, min_samples=10, metric="cosine").fit(X)
        core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        core_samples_mask[db.core_sample_indices_] = True
        labels = db.labels_
        try:
            score = silhouette_score(X, labels, metric="cosine")
        except ValueError:
            score = -np.inf
        if score > best_score:
            best_score = score
            best_labels = labels
    # print((best_score, chosen_eps))
    return best_labels


def cluster_by_dimension(data: pl.DataFrame, options: DimensionClusterOptions) -> np.ndarray:
    """Cluster the data by a specific dimension."""
    if options.dimension_name not in data.columns:
        raise ValueError(f"Objective '{options.dimension_name}' not found in data.")

    # Select the dimension column for clustering
    dimension = data[options.dimension_name]

    # Perform clustering based on the specified method
    if options.kind == "EqualWidth":
        min_val: float = dimension.min()
        max_val: float = dimension.max()
        SMALL_VALUE = 1e-8
        thresholds = np.linspace(
            min_val * (1 - SMALL_VALUE),  # Ensure the minimum value is included in the first cluster
            max_val * (1 + SMALL_VALUE),  # Ensure the maximum value is included in the last cluster
            options.n_clusters + 1,
        )
        return np.digitize(dimension.to_numpy(), thresholds)  # Cluster IDs start at 1
    if options.kind == "EqualFrequency":
        levels: list[float] = [dimension.quantile(i / options.n_clusters) for i in range(1, options.n_clusters)]
        thresholds = [-np.inf] + levels + [np.inf]
        return np.digitize(dimension.to_numpy(), thresholds)  # Cluster IDs start at 1
    raise ValueError(f"Unknown clustering kind: {options.kind}")


def cluster(data: pl.DataFrame, options: ClusteringOptions) -> np.ndarray:
    """Cluster the data using the specified clustering algorithm and options."""
    if isinstance(options, DimensionClusterOptions):
        return cluster_by_dimension(data, options)
    if isinstance(options, KMeansOptions):
        from sklearn.cluster import KMeans

        X = StandardScaler().fit_transform(data.to_numpy())
        kmeans = KMeans(n_clusters=options.n_clusters, random_state=0).fit(X)
        return kmeans.labels_
    if isinstance(options, DBSCANOptions):
        return _DBSCANClustering(data)
    if isinstance(options, GMMOptions):
        if options.scoring_method == "silhouette":
            return _gaussianmixtureclusteringwithsilhouette(data)
        if options.scoring_method == "BIC":
            return _gaussianmixtureclusteringwithBIC(data)
    if isinstance(options, CustomClusterOptions):
        if len(options.clusters) != len(data):
            raise ValueError("Length of custom clusters must match number of solutions in data.")
        return np.array(options.clusters)
    raise ValueError(f"Unknown clustering algorithm: {options}")


def annotated_heatmap(correlation_matrix: np.ndarray, col_names: list, order: list | np.ndarray) -> go.Figure:
    """Create a heatmap of the correlation matrix. Probably should be named something else.

    Args:
        correlation_matrix (np.ndarray): 2-D square array of correlation values between pairs of objectives.
        col_names (List): Objective names.
        order (Union[List, np.ndarray]): Order in which the objectives are shown in SCORE bands.

    Returns:
        go.Figure: The heatmap
    """
    corr = pl.DataFrame(correlation_matrix, index=col_names, columns=col_names)
    corr = corr[col_names[order]].loc[col_names[order[::-1]]]
    corr = np.rint(corr * 100) / 100  # Take upto two significant figures only to make heatmap readable.
    fig = ff.create_annotated_heatmap(
        corr.to_numpy(),
        x=list(corr.columns),
        y=list(corr.index),
        annotation_text=corr.astype(str).to_numpy(),
    )
    fig.update_layout(title="Pearson correlation coefficients")
    return fig


def order_dimensions(data: pl.DataFrame, use_absolute_corr: bool = False) -> tuple[np.ndarray, list[int]]:
    """Calculate the order of objectives.

    Also returns the correlation matrix.

    Args:
        data (pl.DataFrame): Data to be visualized.
        use_absolute_corr (bool, optional): Use absolute value of the correlation to calculate order. Defaults to False.

    Returns:
        tuple: The first element is the correlation matrix. The second element is the order of the objectives.
    """
    # Calculating correlations
    # corr = spearmanr(data).correlation  # Pearson's coeff is better than Spearmann's, in some cases
    corr = np.asarray(
        [
            [pearsonr(data.to_numpy()[:, i], data.to_numpy()[:, j])[0] for j in range(len(data.columns))]
            for i in range(len(data.columns))
        ]
    )
    # axes order: solving TSP
    distances = corr
    if use_absolute_corr:
        distances = np.abs(distances)
    obj_order = solve_tsp(-distances)
    return corr, obj_order


def calculate_axes_positions(
    dimension_order: list[int],
    corr: np.ndarray,
    dist_parameter: float,
    distance_formula: DistanceFormula = DistanceFormula.FORMULA_1,
) -> np.ndarray:
    """Calculate the position of the axes for the SCORE bands visualization based on correlations.

    Args:
        dimension_order (list[int]): Order of the variables to be plotted.
        corr (np.ndarray): Correlation (pearson) matrix.
        dist_parameter (float): Change the relative distances between the axes. Increase this value if the axes are
            placed too close together. Decrease this value if the axes are equidistant.
        distance_formula (DistanceFormula, optional): The value should be 1 or 2. Check the paper for details.
            Defaults to DistanceFormula.FORMULA_1.

    Returns:
        np.ndarray: Positions of the axes in the range [0, 1].
    """
    # axes positions
    order = np.asarray(list(itertools.pairwise(dimension_order)))
    axis_len = corr[order[:, 0], order[:, 1]]
    if distance_formula == DistanceFormula.FORMULA_1:
        axis_len = 1 - axis_len
    elif distance_formula == DistanceFormula.FORMULA_2:
        axis_len = 1 / (np.abs(axis_len) + 1)  #  Reciprocal for reverse
    else:
        # Should never reach here
        raise ValueError("distance_formula should be either 1 or 2 (int)")
    axis_len = axis_len + dist_parameter
    axis_len = axis_len / sum(axis_len)
    return np.cumsum(np.append(0, axis_len))


def score_json(
    data: pl.DataFrame,
    options: SCOREBandsConfig,
) -> SCOREBandsResult:
    """Generate the SCORE Bands data for a given dataset and configuration options.

    Args:
        data (pl.DataFrame): Dataframe of variable (decision or objective) values.
            The column names should be the names of the variables to be plotted. Each row should be a solution.

        options (SCOREBandsConfig): Configuration options for generating the SCORE bands.

    Returns:
        SCOREBandsResult: The result containing all relevant data for the SCORE bands visualization.
    """
    options = deepcopy(options)
    # Calculating correlations and axes positions
    if options.dimensions is None:
        options.dimensions = data.columns
    data_copy = data.select([pl.col(col) for col in options.dimensions])

    if options.axis_positions is None:
        corr, dimension_order = order_dimensions(data_copy, use_absolute_corr=options.use_absolute_correlations)

        axis_dist = calculate_axes_positions(
            dimension_order,
            corr,
            dist_parameter=options.distance_parameter,
            distance_formula=options.distance_formula,
        )

        ordered_dimension_names = [data_copy.columns[i] for i in dimension_order]
        axis_positions = {name: axis_dist[i] for i, name in enumerate(ordered_dimension_names)}
    else:
        axis_positions = options.axis_positions
        ordered_dimension_names = sorted(axis_positions.keys(), key=axis_positions.get)

    clusters = cluster(data_copy, options.clustering_algorithm)

    if min(clusters) <= 0:
        clusters = clusters - np.min(clusters) + 1  # translate minimum to 1.

    # some sanity check: check if all cluster IDs are contiguous integers starting at 1, ending at number of clusters
    unique_clusters = np.unique(clusters)
    max_cluster_id = max(clusters)
    if not all(i in unique_clusters for i in range(1, max_cluster_id + 1)):
        warn(
            """Cluster IDs are not contiguous integers starting at 1.
            This may cause issues with the color mapping in the visualization.""",
            category=UserWarning,
            stacklevel=2,
        )

    cluster_column_name = "cluster"
    if cluster_column_name in data_copy.columns:
        cluster_column_name = "cluster_id"

    data_copy = data_copy.with_columns(pl.Series(cluster_column_name, clusters))
    grouped = data_copy.group_by(cluster_column_name)
    min_percentile = (1 - options.interval_size) / 2
    max_percentile = 1 - min_percentile
    mins = grouped.quantile(min_percentile)
    maxs = grouped.quantile(max_percentile)
    medians = grouped.median()
    frequencies = grouped.len()
    bands_dict = {
        cluster_id: {
            col_name: (
                mins.filter(pl.col(cluster_column_name) == cluster_id)[col_name][0],
                maxs.filter(pl.col(cluster_column_name) == cluster_id)[col_name][0],
            )
            for col_name in ordered_dimension_names
        }
        for cluster_id in mins[cluster_column_name].to_list()
    }
    medians_dict = {
        cluster_id: {
            col_name: medians.filter(pl.col(cluster_column_name) == cluster_id)[col_name][0]
            for col_name in ordered_dimension_names
        }
        for cluster_id in medians[cluster_column_name].to_list()
    }
    frequencies_dict = {
        cluster_id: frequencies.filter(pl.col(cluster_column_name) == cluster_id)["len"][0]
        for cluster_id in frequencies[cluster_column_name].to_list()
    }

    if options.scales is None:
        scales: dict[str, tuple[float, float]] = {
            dimension: (data_copy[dimension].min(), data_copy[dimension].max()) for dimension in ordered_dimension_names
        }
        options.scales = scales
    return SCOREBandsResult(
        options=options,
        ordered_dimensions=ordered_dimension_names,
        clusters=clusters.tolist(),
        axis_positions=axis_positions,
        bands=bands_dict,
        medians=medians_dict,
        cardinalities=frequencies_dict,
    )


def plot_score(data: pl.DataFrame, result: SCOREBandsResult) -> go.Figure:
    """Generate the SCORE Bands figure from the SCOREBandsResult data.

    Args:
        data (pl.DataFrame): Dataframe of objective values. The column names should be the objective names. Each row
            should be an objective vector.
        result (SCOREBandsResult): The result containing all relevant data for the SCORE bands visualization.

    Returns:
        go.Figure: The SCORE bands plot.
    """
    column_names = result.ordered_dimensions

    clusters = np.sort(np.unique(result.clusters))

    cluster_th = 8  # max number of clusters to use 'Accent' color map with, otherwise use 'tab20'
    colorscale = (
        cm.get_cmap("Accent", len(clusters)) if len(clusters) <= cluster_th else cm.get_cmap("tab20", len(clusters))
    )
    if result.options.scales is None:
        raise ValueError("Scales must be provided in the SCOREBandsResult to plot the figure.")

    scale_min = pl.DataFrame({name: result.options.scales[name][0] for name in result.options.scales})
    scale_max = pl.DataFrame({name: result.options.scales[name][1] for name in result.options.scales})

    scaled_data = (data[column_names] - scale_min) / (scale_max - scale_min)

    fig = go.Figure()
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")

    cluster_column_name = "cluster"
    if cluster_column_name in scaled_data.columns:
        cluster_column_name = "cluster_id"
    scaled_data = scaled_data.with_columns(pl.Series(cluster_column_name, result.clusters))

    if result.options.descriptive_names is None:
        descriptive_names = {name: name for name in column_names}
    else:
        descriptive_names = result.options.descriptive_names
    units = dict.fromkeys(column_names, "") if result.options.units is None else result.options.units

    num_ticks = 6
    # Add axes
    for i, col_name in enumerate(column_names):
        label_text = np.linspace(result.options.scales[col_name][0], result.options.scales[col_name][1], num_ticks)
        label_text = [f"{i:.5g}" for i in label_text]
        # label_text[0] = "<<"
        # label_text[-1] = ">>"
        heights = np.linspace(0, 1, num_ticks)
        # Axis lines
        fig.add_scatter(
            x=[result.axis_positions[col_name]] * num_ticks,
            y=heights,
            text=label_text,
            textposition="middle left",
            mode="markers+lines+text",
            line={"color": "black"},
            showlegend=False,
        )
        # Column Name
        fig.add_scatter(
            x=[result.axis_positions[col_name]],
            y=[1.20],
            text=f"{descriptive_names[col_name]}",
            textfont={"size": 20},
            mode="text",
            showlegend=False,
        )
        # Units
        fig.add_scatter(
            x=[result.axis_positions[col_name]],
            y=[1.10],
            text=f"{units[col_name]}",
            textfont={"size": 12},
            mode="text",
            showlegend=False,
        )
    # Add bands
    for cluster_id in sorted(result.bands.keys()):
        r, g, b, a = colorscale(cluster_id - 1)  # Needed as cluster numbering starts at 1
        a = 0.6
        color_bands = f"rgba({r}, {g}, {b}, {a})"
        # color_soln = f"rgba({r}, {g}, {b}, {a})"

        lows = [
            (result.bands[cluster_id][col_name][0] - result.options.scales[col_name][0])
            / (result.options.scales[col_name][1] - result.options.scales[col_name][0])
            for col_name in column_names
        ]
        highs = [
            (result.bands[cluster_id][col_name][1] - result.options.scales[col_name][0])
            / (result.options.scales[col_name][1] - result.options.scales[col_name][0])
            for col_name in column_names
        ]
        medians = [
            (result.medians[cluster_id][col_name] - result.options.scales[col_name][0])
            / (result.options.scales[col_name][1] - result.options.scales[col_name][0])
            for col_name in column_names
        ]

        fig.add_scatter(
            x=[result.axis_positions[col_name] for col_name in column_names],
            y=lows,
            line={"color": color_bands},
            name=f"{int(100 * result.options.interval_size)}% band: Cluster {cluster_id}; "
            f"{result.cardinalities[cluster_id]} Solutions        ",
            mode="lines",
            legendgroup=f"{int(100 * result.options.interval_size)}% band: Cluster {cluster_id}",
            showlegend=True,
            line_shape="spline",
            hovertext=f"Cluster {cluster_id}",
        )
        # upper bound of the band
        fig.add_scatter(
            x=[result.axis_positions[col_name] for col_name in column_names],
            y=highs,
            line={"color": color_bands},
            name=f"Cluster {cluster_id}",
            fillcolor=color_bands,
            mode="lines",
            legendgroup=f"{int(100 * result.options.interval_size)}% band: Cluster {cluster_id}",
            showlegend=False,
            line_shape="spline",
            fill="tonexty",
            hovertext=f"Cluster {cluster_id}",
        )

        if result.options.include_medians:
            # median
            fig.add_scatter(
                x=[result.axis_positions[col_name] for col_name in column_names],
                y=medians,
                line={"color": color_bands},
                name=f"Median: Cluster {cluster_id}",
                mode="lines+markers",
                marker={"line": {"color": "Black", "width": 2}},
                legendgroup=f"Median: Cluster {cluster_id}",
                showlegend=True,
            )
    fig.update_layout(font_size=18)
    fig.update_layout(legend={"orientation": "h", "yanchor": "top"})
    return fig
