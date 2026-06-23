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
from sklearn.cluster import DBSCAN, KMeans
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
    axis_colours: dict[str, str] | None = Field(default=None)
    """Optional dictionary to set the colour of the axes corresponding to each objective. The keys should be the
        same as in the 'dimensions' field. The values should be a valid plotly color string. Defaults to None.

        Valid plotly color strings include:
            - A hex string (e.g. '#ff0000')
            - An rgb/rgba string (e.g. 'rgb(255,0,0)')
            - An hsl/hsla string (e.g. 'hsl(0,100%,50%)')
            - An hsv/hsva string (e.g. 'hsv(0,100%,100%)')
            - A named CSS color: see https://plotly.com/python/css-colors/ for a list
    """
    highlight_cluster: int | None = Field(default=None)
    """Cluster ID to highlight in the visualization. If None, no cluster is highlighted. Defaults to None.
        If a cluster ID is provided, the corresponding cluster is highlighted in the visualization by having a
        pattern fill in the band.
    """
    clustering_algorithm: ClusteringOptions = Field(
        default=DBSCANOptions(),
    )
    """
    Clustering algorithm to use. Currently supports one of `ClusteringOptions`.
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
    cluster_names: dict[int, str] | None = Field(default=None)
    """Optional dictionary mapping cluster IDs to descriptive names for display in the visualization.
        If None, the cluster IDs themselves are used as names. Defaults to None."""
    cluster_hover_info: dict[int, str] | None = Field(default=None)
    """Optional dictionary mapping cluster IDs to hover information for display in the visualization.
        If None, no additional hover information is displayed. Defaults to None."""
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


def _gaussianmixtureclusteringwithBIC(data: pl.DataFrame) -> np.ndarray:  # noqa: N802
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
    x = StandardScaler().fit_transform(data.to_numpy())
    best_score = -np.inf
    best_labels = np.ones(len(data))
    n_components_range = range(1, min(11, len(data)))
    cv_types: list[Literal["full", "tied", "diag", "spherical"]] = ["spherical", "tied", "diag", "full"]
    for cv_type in cv_types:
        for n_components in n_components_range:
            # Fit a Gaussian mixture with EM
            gmm = GaussianMixture(n_components=n_components, covariance_type=cv_type)
            labels = gmm.fit_predict(x)
            try:
                score = silhouette_score(x, labels, metric="cosine")
            except ValueError:
                score = -np.inf
            if score > best_score:
                best_score = score
                best_labels = labels
    # print(best_score)
    return best_labels


def _DBSCANClustering(data: pl.DataFrame) -> np.ndarray:  # noqa: N802
    """Cluster the data using DBSCAN with silhouette scoring to choose eps."""
    x = StandardScaler().fit_transform(data.to_numpy())
    eps_options = np.linspace(0.01, 1, 20)
    best_score = -np.inf
    best_labels = np.ones(len(data))
    for eps_option in eps_options:
        db = DBSCAN(eps=eps_option, min_samples=10, metric="cosine").fit(x)
        core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        core_samples_mask[db.core_sample_indices_] = True
        labels = db.labels_
        try:
            score = silhouette_score(x, labels, metric="cosine")
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
        SMALL_VALUE = 1e-8  # noqa: N806
        thresholds = np.linspace(
            min_val * (1 - SMALL_VALUE),  # Ensure the minimum value is included in the first cluster
            max_val * (1 + SMALL_VALUE),  # Ensure the maximum value is included in the last cluster
            options.n_clusters + 1,
        )
        return np.digitize(dimension.to_numpy(), thresholds)  # Cluster IDs start at 1
    if options.kind == "EqualFrequency":
        levels: list[float] = [dimension.quantile(i / options.n_clusters) for i in range(1, options.n_clusters)]
        thresholds = [-np.inf, *levels, np.inf]
        return np.digitize(dimension.to_numpy(), thresholds)  # Cluster IDs start at 1
    raise ValueError(f"Unknown clustering kind: {options.kind}")


def cluster(data: pl.DataFrame, options: ClusteringOptions) -> np.ndarray:
    """Cluster the data using the specified clustering algorithm and options."""
    if isinstance(options, DimensionClusterOptions):
        return cluster_by_dimension(data, options)
    if isinstance(options, KMeansOptions):
        x = StandardScaler().fit_transform(data.to_numpy())
        kmeans = KMeans(n_clusters=options.n_clusters, random_state=0).fit(x)
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


def score_json(data: pl.DataFrame, options: SCOREBandsConfig) -> SCOREBandsResult:
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
    # some constants for the figure, can be made configurable in the future if needed
    num_ticks = 6  # number of ticks to show on each axis
    max_dist_percent = 0.02  # Maximum distance between equidistant tick position vs a rounded tick position.
    column_names = result.ordered_dimensions

    clusters = np.sort(np.unique(result.clusters))

    cluster_th = 8  # max number of clusters to use 'Accent' color map with, otherwise use 'tab20'
    colorscale = (
        cm.get_cmap("Accent", len(clusters)) if len(clusters) <= cluster_th else cm.get_cmap("tab20", len(clusters))
    )
    if result.options.scales is None:
        raise ValueError("Scales must be provided in the SCOREBandsResult to plot the figure.")

    # Original scaling (not used in final version, but keeping for reference)
    # scaled_data = data.select((pl.all() - pl.all().min()) / (pl.all().max() - pl.all().min()))
    # Scaling with respect to the provided scales, which may not aling with the actual min and max in the data
    # (e.g. if user wants to use fixed scales across multiple visualizations)
    scaled_data = data.with_columns(
        [
            (pl.col(col) - result.options.scales[col][0])
            / (result.options.scales[col][1] - result.options.scales[col][0])
            for col in column_names
        ]
    )
    fig = go.Figure()
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")

    cluster_column_name = "cluster"
    # Avoid overwriting existing column just in case data has a 'cluster' column
    if cluster_column_name in scaled_data.columns:
        cluster_column_name = "cluster_id"
    scaled_data = scaled_data.with_columns(pl.Series(cluster_column_name, result.clusters))

    if result.options.descriptive_names is None:
        descriptive_names = {name: name for name in column_names}
    else:
        descriptive_names = result.options.descriptive_names
    units = dict.fromkeys(column_names, "") if result.options.units is None else result.options.units

    # Add axes
    for _, col_name in enumerate(column_names):
        # check if axis_colours is provided, otherwise use black
        current_axis_colour = "black"
        if result.options.axis_colours is not None and col_name in result.options.axis_colours:
            current_axis_colour = result.options.axis_colours[col_name]
        # Calculate "nice" tick positions and values
        label_text, heights = smart_axis_tick_placement(
            axis_min=result.options.scales[col_name][0],
            axis_max=result.options.scales[col_name][1],
            num_ticks=num_ticks,
            max_dist_percent=max_dist_percent,
        )
        # Axis lines
        fig.add_scatter(
            x=[result.axis_positions[col_name]] * num_ticks,
            y=heights,
            text=label_text,
            textposition="middle left",
            mode="markers+lines+text",
            line={"color": current_axis_colour},
            showlegend=False,
            hoverinfo="skip",
            zorder=100,
        )
        # Objective Name
        name = descriptive_names[col_name]
        splits = name.split()
        # If the name is too long, add a line break at the second space
        if len(splits) > 2:  # noqa: PLR2004
            splits[2] = "<br>" + splits[2]
        name = " ".join(splits)
        fig.add_scatter(
            x=[result.axis_positions[col_name]],
            y=[1.20],
            text=f"{name}",
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
        highlight = None
        if result.options.highlight_cluster is not None and cluster_id == result.options.highlight_cluster:
            highlight = {"shape": "x"}
        hovertext = (
            result.cluster_hover_info.get(cluster_id, f"Cluster {cluster_id}")
            if result.cluster_hover_info is not None
            else f"Cluster {cluster_id}"
        )
        color_bands = f"rgba({r}, {g}, {b}, {a})"
        color_solutions = f"rgba({r}, {g}, {b}, 0.5)"
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

        current_cluster_name = "Cluster " + str(cluster_id)
        if result.cluster_names is not None and cluster_id in result.cluster_names:
            current_cluster_name = result.cluster_names[cluster_id]
        fig.add_scatter(
            x=[result.axis_positions[col_name] for col_name in column_names],
            y=lows,
            line={"color": color_bands},
            name=f"{int(100 * result.options.interval_size)}% band: {current_cluster_name}",
            mode="lines",
            legendgroup=f"{int(100 * result.options.interval_size)}% band: {current_cluster_name}",
            showlegend=True,
            line_shape="spline",
            hovertext=hovertext,
            hoverinfo="text",
        )
        # upper bound of the band
        fig.add_scatter(
            x=[result.axis_positions[col_name] for col_name in column_names],
            y=highs,
            line={"color": color_bands},
            name=f"{current_cluster_name}",
            fillcolor=color_bands,
            mode="lines",
            fillpattern=go.scatter.Fillpattern(highlight),
            legendgroup=f"{int(100 * result.options.interval_size)}% band: {current_cluster_name}",
            showlegend=False,
            line_shape="spline",
            fill="tonexty",
            hovertext=hovertext,
            hoverinfo="text",
        )

        if result.options.include_medians:
            # median
            fig.add_scatter(
                x=[result.axis_positions[col_name] for col_name in column_names],
                y=medians,
                line={"color": color_bands},
                name=f"Median: {current_cluster_name}",
                mode="lines+markers",
                marker={"line": {"color": "Black", "width": 2}},
                legendgroup=f"Median: {current_cluster_name}",
                showlegend=True,
            )
        # Drawing each solution as a single trace (like how it was done in the past) can make the figure very heavy
        # and make interactions (showing/hiding traces) very laggy.
        # Thus here, we draw all solutions in a cluster as a single trace. Basically we make a huge zig-zag trace for
        # each cluster. E.g. imagine two solutions with obj vals (1, 2, 3) and (4, 5, 6) on three objectives. These
        # become the y values in the parallel coordinates plot in this order (1, 2, 3, 6, 5, 4). Subsets of these points
        # which belong to the same solution are given the same hovertext
        if result.options.include_solutions:
            cluster_solutions = scaled_data.filter(pl.col(cluster_column_name) == cluster_id).select(column_names)

            x = []
            y = []
            ax_pos = [result.axis_positions[col_name] for col_name in column_names]
            hovertexts = []
            rev_ax_pos = ax_pos[::-1]
            for i, row in enumerate(cluster_solutions.iter_rows()):
                if i % 2 == 0:
                    x = x + ax_pos
                    y = y + list(row)
                else:
                    x = x + rev_ax_pos
                    y = y + list(row)[::-1]
                # Scale values back to original scale for hovertext
                hovertext = [
                    (
                        f"<b>{col}</b>: "
                        f"{
                            (
                                val * (result.options.scales[col][1] - result.options.scales[col][0])
                                + result.options.scales[col][0]
                            ):.2f} <br>"
                    )
                    for col, val in zip(column_names, row, strict=True)
                ]
                hovertext = "".join(hovertext)
                hovertext = [hovertext] * len(column_names)
                hovertexts = hovertexts + hovertext
            fig.add_scatter(
                x=x,
                y=y,
                line={"color": color_solutions, "width": 1},
                name=f"{result.cardinalities[cluster_id]} Solutions: {current_cluster_name}",
                mode="lines",
                legendgroup=f"{result.cardinalities[cluster_id]} Solutions: {current_cluster_name}",
                hovertext=hovertexts,
                hoverinfo="text",
                hoveron="points+fills",
                showlegend=True,
            )
    fig.update_layout(font_size=18)
    fig.update_layout(legend={"orientation": "h", "yanchor": "top"})
    return fig


def smart_axis_tick_placement(
    axis_min: float, axis_max: float, num_ticks: int, max_dist_percent: float
) -> tuple[list[str], list[float]]:
    """Calculate smart tick placement for the axes in the SCORE bands visualization."""
    min_label_delta = 100
    label_text = np.linspace(axis_min, axis_max, num_ticks)
    heights = [0.0] * num_ticks
    max_distance = (axis_max - axis_min) * max_dist_percent

    # Get a range of candidate tick values around each label_text value
    # and choose the one with the least number of significant digits
    for j in range(len(label_text)):
        if j == 0 or j == len(label_text) - 1:
            # skip rounding for the first and last labels to ensure they are exactly the min and max values
            continue
        label_max = label_text[j] + max_distance
        label_min = label_text[j] - max_distance
        # Find the closest "nice" number to label_text[j] within the range [label_min, label_max]
        # i.e., least number of significant digits
        # while still being within the max distance from the original label text value.
        label_delta = label_max - label_min
        # All calculations are done in integers so we multiply the label_min and label_max by a power of 10
        # such that the label_delta is at least 100.
        multiplier = 1
        while label_delta * multiplier < min_label_delta:
            multiplier *= 10
        label_min = label_min * multiplier
        label_max = label_max * multiplier
        if label_max > 0:
            changing_point = label_max
            stable_point = label_min
        else:
            changing_point = label_min
            stable_point = label_max
        # Remove the least significant digits until the changing_point is too far from the original label_text value
        # then reverse one step back to get the final label value. This gives us a tick label within the max distance
        # from the original label_text value, but with as few significant digits as possible for better readability.
        divider = 1
        while True:
            divider *= 10
            if abs(int(changing_point / divider) * divider) < abs(stable_point):
                break
        divider = divider / 10  # reverse one step back
        label_text[j] = int(changing_point / divider) * divider / multiplier
        # Get the correct height for the label_text[j] value based on the original axis_min and axis_max values
        heights[j] = (label_text[j] - axis_min) / (axis_max - axis_min)
    heights[-1] = 1.0  # Ensure the last label is exactly at the max scale value
    label_text = [f"{label:.6g}" for label in label_text]
    return label_text, heights
