"""Functions related to the E-NAUTILUS method are defined here.

Reference of the method:

Ruiz, A. B., Sindhya, K., Miettinen, K., Ruiz, F., & Luque, M. (2015).
E-NAUTILUS: A decision support system for complex multiobjective optimization
problems based on the NAUTILUS method. European Journal of Operational Research,
246(1), 218-231.
"""

import numpy as np
import polars as pl
from pydantic import BaseModel, Field
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist

from desdeo.problem import (
    Problem,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
)


from desdeo.tools import SolverResults, flip_maximized_objective_values


class ENautilusResult(BaseModel):
    """The result of an iteration of the E-NAUTILUS method."""

    current_iteration: int = Field(description="Number of the current iteration.")
    iterations_left: int = Field(description="Number of iterations left.")
    intermediate_points: list[dict[str, float]] = Field(description="New intermediate points")
    reachable_best_bounds: list[dict[str, float]] = Field(
        description="Best bounds of the objective function values reachable from each intermediate point."
    )
    reachable_worst_bounds: list[dict[str, float]] = Field(
        description="Worst bounds of the objective function values reachable from each intermediate point."
    )
    closeness_measures: list[float] = Field(description="Closeness measures of each intermediate point.")
    reachable_point_indices: list[list[int]] = Field(
        description="Indices of the reachable points from each intermediate point."
    )


def enautilus_get_representative_solutions(
    problem: Problem, result: ENautilusResult, non_dominated_points: pl.DataFrame
) -> list[SolverResults]:
    """Returns the solution corresponding to the intermediate points.

    The representative points are selected based on the current intermediate points.
    If the number of iterations left is 0, then the intermediate and representative points
    are equal.

    Args:
        problem (Problem): the problem being solved.
        result (ENautilusResult): an ENautilusResponse returned by `enautilus_step`.
        non_dominated_points (pl.DataFrame): a dataframe from which the
            representative solutions are taken.

    Returns:
        SolverResults: full information about the solutions. If information
            other than just objective function values are expected, then the
            supplied `non_dominated_points` should contain this information.
    """
    obj_syms = [obj.symbol for obj in problem.objectives]
    var_syms = [var.symbol for var in problem.variables]
    const_syms = [con.symbol for con in problem.constraints] if problem.constraints else None
    extra_syms = [extra.symbol for extra in problem.extra_funcs] if problem.extra_funcs else None
    scal_syms = [scal.symbol for scal in problem.scalarization_funcs] if problem.scalarization_funcs else None

    # Objective matrix (rows = ND points, cols = objectives, original senses)
    obj_matrix = non_dominated_points.select(obj_syms).to_numpy()

    solver_results: list[SolverResults] = []

    for interm in result.intermediate_points:
        interm_vec = np.array([interm[sym] for sym in obj_syms], dtype=float)

        # Find index of closest ND point (Euclidean distance)
        idx = int(np.argmin(np.linalg.norm(obj_matrix - interm_vec, axis=1)))

        row = non_dominated_points[idx]

        var_dict = {sym: row[sym] for sym in var_syms if sym in row}
        obj_dict = {sym: row[sym] for sym in obj_syms}
        const_dict = {sym: row[sym] for sym in const_syms if sym in row} if const_syms is not None else None
        extra_dict = {sym: row[sym] for sym in extra_syms if sym in row} if extra_syms is not None else None
        scal_dict = {sym: row[sym] for sym in scal_syms if sym in row} if scal_syms is not None else None

        solver_results.append(
            SolverResults(
                optimal_variables=var_dict,
                optimal_objectives=obj_dict,
                constraint_values=const_dict,
                extra_func_values=extra_dict,
                scalarization_values=scal_dict,
                success=True,
                message="E-NAUTILUS: nearest non-dominated point selected for intermediate point.",
            )
        )

    return solver_results


def enautilus_step(  # noqa: PLR0913
    problem: Problem,
    non_dominated_points: pl.DataFrame,
    current_iteration: int,
    iterations_left: int,
    selected_point: dict[str, float],
    reachable_point_indices: list[int],
    total_number_of_iterations: int,
    number_of_intermediate_points: int,
) -> ENautilusResult:
    """Compute one iteration of the E-NAUTILUS method.

    It is assumed that information from a previous iteration (selected point,
    etc.) is available either from a previous iteration of E-NAUTILUS, or if
    this is the first iteration, then the selected (intermediate) point
    `selected_point` should be the approximated nadir point from
    `non_dominated_points`. In this case, the `reachable_point_indices` should
    cover the whole of `non_dominated_points`. After the first iteration, all
    the information for computing the next iteration is always available from
    the previous iteration's result of this function (plus the `selected_point`
    provided by e.g., a decision maker).

    Args:
        problem (Problem): the problem being solved. Used mainly for manipulating the other arguments.
        non_dominated_points (pl.DataFrame): a set of non-dominated points
            approximating the Pareto front of `Problem`. This should be a Polars
            dataframe with at least columns that match the objective function
            symbols in `Problem` and the corresponding minimization value column.
            I.e., for an objective with symbol 'f1' the dataframe should have the
            symbols 'f1' and 'f1_min', where the column 'f1_min has the
            corresponding values of 'f1', but assuming minimization (N.B. if 'f1' is
            minimized, then 'f1_min' would have identical values as 'f1').
        current_iteration (int): the number of the current iteration. For the first iteration, this should be zero.
        iterations_left (int): how many iteration are left (counting the current one).
        selected_point (dict[str, float]): the selected intermediate point in
            the previous iteration. If this is the first iteration, then this should
            be the nadir point approximated from `non_dominated_points`.
        reachable_point_indices (list[int]): the indices of the points in
            `non_dominated_points` that are reachable from
            `current_iteration_point`.
        total_number_of_iterations (int): how many iterations are to be carried in total.
        number_of_intermediate_points (int): how many intermediate points are generated.

    Returns:
        ENautilusResult: the result of the iteration.
    """
    # treat everything as minimized
    # selected point as numpy array, correct for minimization
    z_h = objective_dict_to_numpy_array(problem, flip_maximized_objective_values(problem, selected_point))

    # subset of reachable solutions, take _min column
    non_dom_objectives = non_dominated_points[[f"{obj.symbol}_min" for obj in problem.objectives]].to_numpy()
    p_h = non_dom_objectives[reachable_point_indices]

    # estimate nadir from non-dominated points, treating as minimized problem
    z_nadir = non_dom_objectives.max(axis=0)

    # compute representative points
    representative_points = prune_by_average_linkage(non_dom_objectives, number_of_intermediate_points)

    # calculate intermediate points
    intermediate_points = calculate_intermediate_points(z_h, representative_points, iterations_left)

    # calculate lower bounds
    intermediate_lower_bounds = [
        calculate_lower_bounds(p_h, intermediate_point) for intermediate_point in intermediate_points
    ]

    # calculate closeness measures
    closeness_measures = [
        calculate_closeness(intermediate_point, z_nadir, representative_point)
        for (intermediate_point, representative_point) in zip(intermediate_points, representative_points, strict=True)
    ]

    # calculate the indices of the reachable points for each intermediate point
    reachable_from_intermediate = [
        calculate_reachable_subset(non_dom_objectives, lower_bounds, z_h) for lower_bounds in intermediate_lower_bounds
    ]

    best_bounds = [
        flip_maximized_objective_values(problem, numpy_array_to_objective_dict(problem, bounds))
        for bounds in intermediate_lower_bounds
    ]
    worst_bounds = [
        flip_maximized_objective_values(problem, numpy_array_to_objective_dict(problem, point))
        for point in intermediate_points
    ]

    corrected_intermediate_points = [
        flip_maximized_objective_values(problem, numpy_array_to_objective_dict(problem, point))
        for point in intermediate_points
    ]

    return ENautilusResult(
        current_iteration=current_iteration + 1,
        iterations_left=iterations_left - 1,
        intermediate_points=corrected_intermediate_points,
        reachable_best_bounds=best_bounds,
        reachable_worst_bounds=worst_bounds,
        closeness_measures=closeness_measures,
        reachable_point_indices=reachable_from_intermediate,
    )


def prune_by_average_linkage(non_dominated_points: np.ndarray, k: int) -> np.ndarray:
    """Prune a set of non-dominated points using average linkage clustering (Morse, 1980).

    This is used to calculate the representative solutions in E-NAUTILUS.

    Args:
        non_dominated_points (np.ndarray): an array of non-dominated points in objective space.
        k (int): Number of representative points to retain.

    Returns:
        np.ndarray: an array of representative points.
    """
    if len(non_dominated_points) <= k:
        # no need to prune
        return non_dominated_points

    # Compute pairwise distances
    distances = pdist(non_dominated_points, metric="euclidean")

    # Hierarchical clustering using average linkage
    z = linkage(distances, method="average")

    # Cut tree to form k clusters
    cluster_labels = fcluster(z, k, criterion="maxclust")

    # For each cluster, choose the point closest to the centroid
    representatives = []
    for cluster_id in range(1, k + 1):
        cluster_points = non_dominated_points[cluster_labels == cluster_id]
        centroid = cluster_points.mean(axis=0)
        closest_idx = np.argmin(np.linalg.norm(cluster_points - centroid, axis=1))
        representatives.append(cluster_points[closest_idx])

    return np.array(representatives)


def calculate_intermediate_points(
    z_previous: np.ndarray, zs_representatives: np.ndarray, iterations_left: int
) -> np.ndarray:
    """Calculates the intermediate points to be shown to the decision maker at each iteration.

    The number of returned points depends on how many `zs_representative points` are supplied.

    Args:
        z_previous (np.ndarray): the point selected by the decision maker in the previous iteration.
        zs_representatives (np.ndarray): the representative solutions at the current iteration.
        iterations_left (int): the number of iterations left (including the current one).

    Returns:
        np.ndarray: an array of intermediate points.
    """
    return ((iterations_left - 1) / iterations_left) * z_previous + (1 / iterations_left) * zs_representatives


def calculate_reachable_subset(
    non_dominated_points: np.ndarray, lower_bounds: np.ndarray, z_preferred: np.ndarray
) -> list[int]:
    """Calculates the reachable subset on a non-dominated set from a selected intermediate point.

    Args:
        non_dominated_points (np.ndarray): the original set of non-dominated points.
        lower_bounds (np.ndarray): the lower bounds of the reachable subset of non-dominates points.
        z_preferred (np.ndarray): the selected intermediate point subject to the reachable subset is calculated.

    Returns:
        list[int]: the indices of the reachable solutions
    """
    return [i for i, z in enumerate(non_dominated_points) if np.all(lower_bounds <= z) and np.all(z <= z_preferred)]


def calculate_lower_bounds(non_dominated_points: np.ndarray, z_intermediate: np.ndarray) -> np.ndarray:
    """Calculates the lower bounds of reachable solutions from an intermediate point.

    The lower bounds are calculated by solving an epsilon-constraint problem
    with the epsilon values taken from the intermediate point.

    Args:
        non_dominated_points (np.ndarray): a set of non-dominated points
            according to which the reachable values are computed.
        z_intermediate (np.ndarray): the intermediate point according to which
            the lower bounds are calculated.

    Returns:
        np.ndarray: the lower bounds of reachable solutions on the non-dominated
            set based from the intermediate point.
    """
    k = non_dominated_points.shape[1]
    bounds = []

    for r in range(k):
        # Indices of objectives other than r
        other = np.delete(np.arange(k), r)

        # Find points that are no worse than z_intermediate in all objectives except r
        mask = np.all(non_dominated_points[:, other] <= z_intermediate[other], axis=1)
        feasible = non_dominated_points[mask]

        if feasible.size > 0:
            bounds.append(np.min(feasible[:, r]))
        else:
            bounds.append(np.inf)  # No feasible point in this projection

    return np.array(bounds)


def calculate_closeness(z_intermediate: np.ndarray, z_nadir: np.ndarray, z_representative: np.ndarray) -> float:
    """Calculate the closeness of an intermediate point to the non-dominated set.

    The greater the closeness is, the close intermediate point is to the non-dominated set.

    Args:
        z_intermediate (np.ndarray): the intermediate point.
        z_nadir (np.ndarray): the nadir point of the non-dominated set.
        z_representative (np.ndarray): the representative solution of `z_intermediate`.

    Returns:
        float: the closeness measure.
    """
    return np.linalg.norm(z_intermediate - z_nadir) / np.linalg.norm(z_representative - z_nadir) * 100
