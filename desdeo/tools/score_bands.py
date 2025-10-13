"""Use the auto_SCORE function to generate the SCORE bands visualization.

This module contains the functions which generate SCORE bands visualizations. It also contains functions to calculate
the order and positions of the objective axes, as well as a heatmap of correlation matrix.

This file is just copied from the old SCORE bands repo.
It is very much out of date and is missing documentation.
"""

import numpy as np
import polars as pl
import plotly.figure_factory as ff
import plotly.graph_objects as go
from matplotlib import cm
from scipy.stats import pearsonr
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from tsp_solver.greedy import solve_tsp

from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Literal


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


class ObjectiveClusterOptions(BaseModel):
    """Options for clustering by one of the objectives."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(default="ObjectiveCluster")
    """Clustering by one of the objectives."""
    objective_name: str
    """Objective to use for clustering."""
    n_clusters: int = Field(default=5)
    """Number of clusters to use. Defaults to 5."""
    kind: Literal["EqualWidth", "EqualFrequency"] = Field(default="EqualWidth")
    """Kind of clustering to use. Either "EqualWidth", which divides the objective range into equal width intervals,
        or "EqualFrequency", which divides the objective values into intervals with equal number of solutions.
        Defaults to "EqualWidth"."""


ClusteringOptions = GMMOptions | DBSCANOptions | KMeansOptions | ObjectiveClusterOptions


class DistanceFormula(int, Enum):
    """Distance formulas supported by SCORE bands. See the paper for details."""

    FORMULA_1 = 1
    FORMULA_2 = 2


class SCOREBandsConfig(BaseModel):
    """Configuration options for SCORE bands visualization."""

    model_config = ConfigDict(use_attribute_docstrings=True)

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
    objective_names: list[str]
    """List of objective names (i.e., column names in the data). Ordered according to their placement in the given
        dataset."""
    ordered_objective_names: list[str]
    """List of objective names (i.e., column names in the data). Ordered according to their placement in the SCORE bands
        visualization."""
    correlation_matrix: dict[str, dict[str, float]]
    """Correlation matrix as a nested dictionary. The keys are objective names, and the values are dictionaries
        mapping objective names to their correlation values."""
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


def cluster_by_objective(data: pl.DataFrame, options: ObjectiveClusterOptions) -> np.ndarray:
    """Cluster the data by a specific objective."""
    if options.objective_name not in data.columns:
        raise ValueError(f"Objective '{options.objective_name}' not found in data.")

    # Select the objective column for clustering
    objective_data = data[options.objective_name]

    # Perform clustering based on the specified method
    if options.kind == "EqualWidth":
        min_val: float = objective_data.min()
        max_val: float = objective_data.max()
        SMALL_VALUE = 1e-8
        thresholds = np.linspace(
            min_val * (1 - SMALL_VALUE),  # Ensure the minimum value is included in the first cluster
            max_val * (1 + SMALL_VALUE),  # Ensure the maximum value is included in the last cluster
            options.n_clusters + 1,
        )
        return np.digitize(objective_data.to_numpy(), thresholds)  # Cluster IDs start at 1
    elif options.kind == "EqualFrequency":
        levels: list[float] = [objective_data.quantile(i / options.n_clusters) for i in range(1, options.n_clusters)]
        thresholds = [-np.inf] + levels + [np.inf]
        return np.digitize(objective_data.to_numpy(), thresholds)  # Cluster IDs start at 1
    raise ValueError(f"Unknown clustering kind: {options.kind}")


def cluster(data: pl.DataFrame, options: ClusteringOptions) -> np.ndarray:
    """Cluster the data using the specified clustering algorithm and options."""
    if isinstance(options, ObjectiveClusterOptions):
        raise NotImplementedError()
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
    raise ValueError(f"Unknown clustering algorithm: {options}")


def SCORE_bands(
    data: pl.DataFrame,
    axis_signs: np.ndarray = None,
    color_groups: list | np.ndarray = None,
    axis_positions: np.ndarray = None,
    solutions: bool = True,
    bands: bool = False,
    medians: bool = False,
    quantile: float = 0.25,
    scales: pl.DataFrame = None,
) -> go.Figure:
    """Generate SCORE bands figure from the provided data.

    Args:
        data (pl.DataFrame): Pandas dataframe where each column represents an objective and each row is an objective
        vector. The column names are displayed as the objective names in the generated figure. Each element in the
        dataframe must be numeric.

        color_groups (Union[List, np.ndarray], optional): List or numpy array of the same length as the number of
        objective vectors. The elements should be contiguous set of integers starting at 1. The element value represents
        the Cluster ID of the corresponding objective vector. Defaults to None (though this behaviour is not fully
        tested yet).

        axis_positions (np.ndarray, optional): 1-D numpy array of the same length as the number of objectives. The value
        represents the horizontal position of the corresponding objective axes. The value of the first and last element
        should be 0 and 1 respectively, and all intermediate values should lie between 0 and 1.
        Defaults to None, in which case all axes are positioned equidistant.

        axis_signs (np.ndarray, optional): 1-D Numpy array of the same length as the number of objectives. Each element
        can either be 1 or -1. A value of -1 flips the objective in the SCORE bands visualization. This feature is
        experimental and should be ignored for now. Defaults to None.

        solutions (bool, optional): Show or hide individual solutions. Defaults to True.

        bands (bool, optional): Show or hide cluster bands. Defaults to False.

        medians (bool, optional): Show or hide cluster medians. Defaults to False.

        quantile (float, optional): The quantile value to calculate the band. The band represents the range between
        (quantile) and (1 - quantile) quantiles of the objective values. Defaults to 0.25.

    Returns:
        go.Figure: SCORE bands plot.

    """
    # show on render
    show_solutions = "legendonly"
    bands_visible = True
    if bands:
        show_medians = "legendonly"
    if medians:
        show_medians = True
    # pio.templates.default = "simple_white"
    column_names = data.columns
    num_columns = len(column_names)
    if axis_positions is None:
        axis_positions = np.linspace(0, 1, num_columns)
    if axis_signs is None:
        axis_signs = np.ones_like(axis_positions)
    if color_groups is None:
        color_groups = "continuous"
        colorscale = cm.get_cmap("viridis")
    elif isinstance(color_groups, (np.ndarray, list)):
        groups = list(np.unique(color_groups))
        if len(groups) <= 8:
            colorscale = cm.get_cmap("Accent", len(groups))
            # print(len(groups))
            # print("hi!")
        else:
            colorscale = cm.get_cmap("tab20", len(groups))
    # colorscale = cm.get_cmap("viridis_r", len(groups))
    data = data * axis_signs
    num_labels = 6

    # Scaling the objective values between 0 and 1.
    if scales is None:
        scales = pl.DataFrame([data.min(axis=0), data.max(axis=0)], index=["min", "max"]) * axis_signs

    scaled_data = data - scales.loc["min"]
    scaled_data = scaled_data / (scales.loc["max"] - scales.loc["min"])

    fig = go.Figure()
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")

    scaled_data.insert(0, "group", value=color_groups)
    for cluster_id, solns in scaled_data.groupby("group"):
        # TODO: Many things here are very inefficient. Improve when free.
        num_solns = len(solns)

        r, g, b, a = colorscale(cluster_id - 1)  # Needed as cluster numbering starts at 1
        a = 0.6
        a_soln = 0.6
        color_bands = f"rgba({r}, {g}, {b}, {a})"
        color_soln = f"rgba({r}, {g}, {b}, {a_soln})"

        low = solns.drop("group", axis=1).quantile(quantile)
        high = solns.drop("group", axis=1).quantile(1 - quantile)
        median = solns.drop("group", axis=1).median()

        if bands is True:
            # lower bound of the band
            fig.add_scatter(
                x=axis_positions,
                y=low,
                line={"color": color_bands},
                name=f"{int(100 - 200 * quantile)}% band: Cluster {cluster_id}; {num_solns} Solutions        ",
                mode="lines",
                legendgroup=f"{int(100 - 200 * quantile)}% band: Cluster {cluster_id}",
                showlegend=True,
                line_shape="spline",
                hovertext=f"Cluster {cluster_id}",
                visible=bands_visible,
            )
            # upper bound of the band
            fig.add_scatter(
                x=axis_positions,
                y=high,
                line={"color": color_bands},
                name=f"Cluster {cluster_id}",
                fillcolor=color_bands,
                mode="lines",
                legendgroup=f"{int(100 - 200 * quantile)}% band: Cluster {cluster_id}",
                showlegend=False,
                line_shape="spline",
                fill="tonexty",
                hovertext=f"Cluster {cluster_id}",
                visible=bands_visible,
            )
        if medians is True:
            # median
            fig.add_scatter(
                x=axis_positions,
                y=median,
                line={"color": color_bands},
                name=f"Median: Cluster {cluster_id}",
                mode="lines+markers",
                marker={"line": {"color": "Black", "width": 2}},
                legendgroup=f"Median: Cluster {cluster_id}",
                showlegend=True,
                visible=show_medians,
            )
        if solutions is True:
            # individual solutions
            legend = True
            for _, soln in solns.drop("group", axis=1).iterrows():
                fig.add_scatter(
                    x=axis_positions,
                    y=soln,
                    line={"color": color_soln},
                    name=f"Solutions: Cluster {cluster_id}              ",
                    legendgroup=f"Solutions: Cluster {cluster_id}",
                    showlegend=legend,
                    visible=show_solutions,
                )
                legend = False
    # Axis lines
    for i, col_name in enumerate(column_names):
        # better = "Upper" if axis_signs[i] == -1 else "Lower"
        label_text = np.linspace(scales[col_name]["min"], scales[col_name]["max"], num_labels)
        # label_text = ["{:.3g}".format(i) for i in label_text]
        heights = np.linspace(0, 1, num_labels)
        scale_factors = []
        for current_label in label_text:
            try:
                with np.errstate(divide="ignore"):
                    scale_factors.append(int(np.floor(np.log10(np.abs(current_label)))))
            except OverflowError:
                pass

        scale_factor = int(np.median(scale_factors))
        if scale_factor == -1 or scale_factor == 1:
            scale_factor = 0

        # TODO: This sometimes doesn't generate the correct label text. Check with datasets where objs lie between (0,1).
        label_text = label_text / 10 ** (scale_factor)
        label_text = ["{:.1f}".format(i) for i in label_text]
        scale_factor_text = f"e{scale_factor}" if scale_factor != 0 else ""

        # Bottom axis label
        fig.add_scatter(
            x=[axis_positions[i]],
            y=[heights[0]],
            text=[label_text[0] + scale_factor_text],
            textposition="bottom center",
            mode="text",
            line={"color": "black"},
            showlegend=False,
        )
        # Top axis label
        fig.add_scatter(
            x=[axis_positions[i]],
            y=[heights[-1]],
            text=[label_text[-1] + scale_factor_text],
            textposition="top center",
            mode="text",
            line={"color": "black"},
            showlegend=False,
        )
        label_text[0] = ""
        label_text[-1] = ""
        # Intermediate axes labels
        fig.add_scatter(
            x=[axis_positions[i]] * num_labels,
            y=heights,
            text=label_text,
            textposition="middle left",
            mode="markers+lines+text",
            line={"color": "black"},
            showlegend=False,
        )

        fig.add_scatter(
            x=[axis_positions[i]],
            y=[1.10],
            text=f"{col_name}",
            textfont={"size": 20},
            mode="text",
            showlegend=False,
        )
        """fig.add_scatter(
            x=[axis_positions[i]], y=[1.1], text=better, mode="text", showlegend=False,
        )
        fig.add_scatter(
            x=[axis_positions[i]],
            y=[1.05],
            text="is better",
            mode="text",
            showlegend=False,
        )"""
    fig.update_layout(font_size=18)
    fig.update_layout(legend={"orientation": "h", "yanchor": "top", "font": {"size": 24}})
    return fig


def annotated_heatmap(correlation_matrix: np.ndarray, col_names: list, order: list | np.ndarray) -> go.Figure:
    """Create a heatmap of the correlation matrix. Probably should be named something else.

    Args:
        correlation_matrix (np.ndarray): 2-D square array of correlation values between pairs of objectives.
        col_names (List): Objective names.
        order (Union[List, np.ndarray]): Order in which the objectives are shown in SCORE bands.

    Returns:
        go.Figure: The heatmap
    """  # noqa: D212, D213, D406, D407
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


def order_objectives(data: pl.DataFrame, use_absolute_corr: bool = False):
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
    data: pl.DataFrame, obj_order, corr, dist_parameter, distance_formula: int = 1
) -> tuple[pl.DataFrame, np.ndarray]:
    # axes positions
    order = np.asarray(list((zip(obj_order[:-1], obj_order[1:]))))
    axis_len = corr[order[:, 0], order[:, 1]]
    if distance_formula == 1:
        axis_len = 1 - axis_len  # TODO Make this formula available to the user
    elif distance_formula == 2:
        axis_len = 1 / (np.abs(axis_len) + 1)  #  Reciprocal for reverse
    else:
        raise ValueError("distance_formula should be either 1 or 2 (int)")
    # axis_len = np.abs(axis_len)
    # axis_len = axis_len / sum(axis_len) #TODO Changed
    axis_len = axis_len + dist_parameter  # Minimum distance between axes
    axis_len = axis_len / sum(axis_len)
    axis_dist = np.cumsum(np.append(0, axis_len))
    return data[obj_order], axis_dist


def auto_SCORE(
    data: pl.DataFrame,
    solutions: bool = True,
    bands: bool = True,
    medians: bool = False,
    dist_parameter: float = 0.05,
    use_absolute_corr: bool = False,
    distance_formula: int = 1,
    flip_axes: bool = False,
    clustering_algorithm: str = "DBSCAN",
    clustering_score: str = "silhoutte",
    quantile: float = 0.05,
):
    """Generate the SCORE Bands visualization for a dataset with predefined values for the hyperparameters.

    Args:
        data (pl.DataFrame): Dataframe of objective values. The column names should be the objective names. Each row
        should be an objective vector.

        solutions (bool, optional): Show or hide individual solutions. Defaults to True.
        bands (bool, optional): Show or hide the cluster bands. Defaults to True.
        medians (bool, optional): Show or hide the cluster medians. Defaults to False.
        dist_parameter (float, optional): Change the relative distances between the objective axes. Increase this value
        if objectives are placed too close together. Decrease this value if the objectives are equidistant in a problem
        with objective clusters. Defaults to 0.05.
        use_absolute_corr (bool, optional): Use absolute value of the correlation to calculate the placement of axes.
        Defaults to False.
        distance_formula (int, optional): The value should be 1 or 2. Check the paper for details. Defaults to 1.
        flip_axes (bool, optional): Do not use this option. Defaults to False.
        clustering_algorithm (str, optional): Currently supported options: "GMM" and "DBSCAN". Defaults to "DBSCAN".
        clustering_score (str, optional): If "GMM" is chosen for clustering algorithm, the scoring mechanism can be
        either "silhoutte" or "BIC". Defaults to "silhoutte".

    Returns:
        _type_: _description_
    """
    # Calculating correlations and axes positions
    corr, obj_order = order_objectives(data, use_absolute_corr=use_absolute_corr)

    ordered_data, axis_dist, axis_signs = calculate_axes_positions(
        data,
        obj_order,
        corr,
        dist_parameter=dist_parameter,
        distance_formula=distance_formula,
    )
    if not flip_axes:
        axis_signs = None
    groups = cluster(ordered_data, algorithm=clustering_algorithm, score=clustering_score)
    groups = groups - np.min(groups) + 1  # translate minimum to 1.
    fig1 = SCORE_bands(
        ordered_data,
        color_groups=groups,
        axis_positions=axis_dist,
        axis_signs=axis_signs,
        solutions=solutions,
        bands=bands,
        medians=medians,
        quantile=0.05,
    )
    return fig1, corr, obj_order, groups, axis_dist


def score_json(
    data: pl.DataFrame,
    options: SCOREBandsConfig,
) -> SCOREBandsResult:
    """Generate the SCORE Bands data for a given dataset and configuration options.

    Args:
        data (pl.DataFrame): Dataframe of objective values. The column names should be the objective names. Each row
        should be an objective vector.

        options (SCOREBandsConfig): Configuration options for generating the SCORE bands.

    Returns:
        SCOREBandsResult: The result containing all relevant data for the SCORE bands visualization.
    """
    # Calculating correlations and axes positions
    corr, obj_order = order_objectives(data, use_absolute_corr=options.use_absolute_correlations)

    ordered_data, axis_dist = calculate_axes_positions(
        data,
        obj_order,
        corr,
        dist_parameter=options.distance_parameter,
        distance_formula=options.distance_formula.value,
    )

    ordered_objective_names = ordered_data.columns

    axes_positions = {name: axis_dist[i] for i, name in enumerate(ordered_objective_names)}

    clusters = cluster(ordered_data, options.clustering_algorithm)
    if min(clusters) <= 0:
        clusters = clusters - np.min(clusters) + 1  # translate minimum to 1.

    cluster_column_name = "cluster"
    if cluster_column_name in ordered_data.columns:
        cluster_column_name = "cluster_id"

    ordered_data = ordered_data.with_columns(pl.Series(cluster_column_name, clusters))
    grouped = ordered_data.group_by(cluster_column_name)
    mins = grouped.min()
    maxs = grouped.max()
    medians = grouped.median()
    frequencies = grouped.len()
    bands_dict = {
        cluster_id: {
            col_name: (
                mins.filter(pl.col(cluster_column_name) == cluster_id)[col_name][0],
                maxs.filter(pl.col(cluster_column_name) == cluster_id)[col_name][0],
            )
            for col_name in ordered_data.columns
        }
        for cluster_id in mins[cluster_column_name].to_list()
    }
    medians_dict = {
        cluster_id: {
            col_name: medians.filter(pl.col(cluster_column_name) == cluster_id)[col_name][0]
            for col_name in ordered_data.columns
        }
        for cluster_id in medians[cluster_column_name].to_list()
    }
    frequencies_dict = {
        cluster_id: frequencies.filter(pl.col(cluster_column_name) == cluster_id)["len"][0]
        for cluster_id in frequencies[cluster_column_name].to_list()
    }

    corr_mat_dict = {
        name1: {name2: float(corr[i, j]) for j, name2 in enumerate(ordered_data.columns)}
        for i, name1 in enumerate(ordered_data.columns)
    }

    if options.scales is None:
        scales: dict[str, tuple[float, float]] = {
            objective: (data[objective].min(), data[objective].max()) for objective in data.columns
        }
        options.scales = scales
    return SCOREBandsResult(
        options=options,
        objective_names=data.columns,
        ordered_objective_names=ordered_objective_names,
        correlation_matrix=corr_mat_dict,
        clusters=clusters.tolist(),
        axis_positions=axes_positions,
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
    column_names = result.ordered_objective_names

    clusters = np.sort(np.unique(result.clusters))

    if len(clusters) <= 8:
        colorscale = cm.get_cmap("Accent", len(clusters))
    else:
        colorscale = cm.get_cmap("tab20", len(clusters))

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

    num_ticks = 6
    # Add axes
    for i, col_name in enumerate(column_names):
        label_text = np.linspace(result.options.scales[col_name][0], result.options.scales[col_name][1], num_ticks)
        label_text = ["{:.3g}".format(i) for i in label_text]
        label_text[0] = ""
        label_text[-1] = ""
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
            y=[1.10],
            text=f"{col_name}",
            textfont={"size": 20},
            mode="text",
            showlegend=False,
        )
    return fig
