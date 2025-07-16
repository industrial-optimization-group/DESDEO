"""Use the auto_SCORE function to generate the SCORE bands visualization.

This module contains the functions which generate SCORE bands visualizations. It also contains functions to calculate
the order and positions of the objective axes, as well as a heatmap of correlation matrix.

This file is just copied from the old SCORE bands repo.
It is very much out of date and is missing documentation.
"""

import numpy as np
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
from matplotlib import cm
from scipy.stats import pearsonr
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from tsp_solver.greedy import solve_tsp


def _gaussianmixtureclusteringwithBIC(data: pd.DataFrame):
    data = StandardScaler().fit_transform(data)
    lowest_bic = np.inf
    bic = []
    n_components_range = range(1, min(11, len(data)))
    cv_types = ["spherical", "tied", "diag", "full"]
    for cv_type in cv_types:
        for n_components in n_components_range:
            # Fit a Gaussian mixture with EM
            gmm = GaussianMixture(n_components=n_components, covariance_type=cv_type)
            gmm.fit(data)
            bic.append(gmm.score(data))
            # bic.append(gmm.bic(data))
            if bic[-1] < lowest_bic:
                lowest_bic = bic[-1]
                best_gmm = gmm

    return best_gmm.predict(data)


def _gaussianmixtureclusteringwithsilhouette(data: pd.DataFrame):
    X = StandardScaler().fit_transform(data)
    best_score = -np.inf
    best_labels = []
    n_components_range = range(1, min(11, len(data)))
    cv_types = ["spherical", "tied", "diag", "full"]
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


def _DBSCANClustering(data: pd.DataFrame):
    X = StandardScaler().fit_transform(data)
    eps_options = np.linspace(0.01, 1, 20)
    best_score = -np.inf
    best_labels = [1] * len(X)
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


def cluster(data: pd.DataFrame, algorithm: str = "DBSCAN", score: str = "silhoutte"):
    if not (score == "silhoutte" or score == "BIC"):
        raise ValueError()
    if not (algorithm == "GMM" or algorithm == "DBSCAN"):
        raise ValueError()
    if algorithm == "DBSCAN":
        return _DBSCANClustering(data)
    if score == "silhoutte":
        return _gaussianmixtureclusteringwithsilhouette(data)
    else:
        return _gaussianmixtureclusteringwithBIC(data)


def SCORE_bands(
    data: pd.DataFrame,
    axis_signs: np.ndarray = None,
    color_groups: list | np.ndarray = None,
    axis_positions: np.ndarray = None,
    solutions: bool = True,
    bands: bool = False,
    medians: bool = False,
    quantile: float = 0.25,
    scales: pd.DataFrame = None,
) -> go.Figure:
    """Generate SCORE bands figure from the provided data.

    Args:
        data (pd.DataFrame): Pandas dataframe where each column represents an objective and each row is an objective
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
        scales = pd.DataFrame([data.min(axis=0), data.max(axis=0)], index=["min", "max"]) * axis_signs
    
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
    corr = pd.DataFrame(correlation_matrix, index=col_names, columns=col_names)
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


def order_objectives(data: pd.DataFrame, use_absolute_corr: bool = False):
    """Calculate the order of objectives.

    Also returns the correlation matrix.

    Args:
        data (pd.DataFrame): Data to be visualized.
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


def calculate_axes_positions(data, obj_order, corr, dist_parameter, distance_formula: int = 1):
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
    # Axis signs (normalizing negative correlations)
    axis_signs = np.cumprod(np.sign(np.hstack((1, corr[order[:, 0], order[:, 1]]))))
    return data.iloc[:, obj_order], axis_dist, axis_signs


def auto_SCORE(
    data: pd.DataFrame,
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
        data (pd.DataFrame): Dataframe of objective values. The column names should be the objective names. Each row
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
