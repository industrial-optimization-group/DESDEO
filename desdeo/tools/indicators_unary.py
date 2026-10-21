"""This module implements unary indicators that can be used to evaluate the quality of a single solution set.

It assumes that the solution set has been normalized just that _some_ ideal point (not necessarily the ideal point
of the set) is the origin and _some_ nadir point (not necessarily the nadir point of the set) is (1, 1, ..., 1).
The normalized solution set is assumed to be inside the bounding box [0, 1]^k where k is the number of objectives.
If these conditions are not met, the results of the indicators will not be meaningful.

Additionally, the set may be assumed to only contain mutually non-dominated solutions, depending on the indicator.

For now, we rely on pymoo for the implementation of some of the indicators.

Find more information about the indicators in:
Audet, Charles, et al. "Performance indicators in multiobjective optimization."
European journal of operational research 292.2 (2021): 397-422.
"""

from warnings import warn

import numpy as np
from moocore import Hypervolume
from pydantic import BaseModel, Field
from pymoo.indicators.rmetric import RMetric
from scipy.spatial.distance import cdist

from desdeo.tools.non_dominated_sorting import non_dominated


def hv(solution_set: np.ndarray, reference_point_component: float) -> float:
    """Calculate the hypervolume indicator for a set of solutions.

    Args:
        solution_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be non-dominated. The solutions are assumed to be normalized within the unit
            hypercube. The ideal and nadir of the set itself can lie within the hypercube, but not outside it.
        reference_point_component (float): The value of the reference point component. The reference point is assumed to
            be the same for all objectives. The reference point must be at least 1.

    Returns:
        float: The hypervolume indicator value.
    """
    hv = Hypervolume(reference_point_component)
    ind = hv(solution_set)

    if ind is None:
        raise ValueError("Hypervolume calculation failed.")

    return float(ind)


def hv_batch(
    solution_sets: dict[str, np.ndarray], reference_points_component: list[float]
) -> dict[str, list[float | None]]:
    """Calculate the hypervolume indicator for a set of solutions over a range of reference points.

    Args:
        solution_sets (dict[str, np.ndarray]): A dict of strings mapped to 2D numpy arrays where each array contains a
            set of solutions.
            Each row is a solution and each column is an objective value. The solutions are assumed to be non-dominated
            within their respective sets. The solutions are assumed to be normalized within the unit hypercube. The
            ideal and nadir of the set itself can lie within the hypercube, but not outside it. The sets must have the
            same number of objectives/columns but can have different number of solutions/rows.
            The keys of the dict are the names of the sets.
        reference_points_component (list[float]): A list of the value of the reference point component. The
            hypervolume is calculated for each set of solutions for each reference point component. The reference point
            is assumed to be the same for all objectives. The reference point must be at least 1.

    Returns:
        dict[str, list[float | None]]: A dict of strings mapped to lists of hypervolume indicator values. The keys of
            the dict are the names of the sets. The lists contain the hypervolume indicator values for each reference
            point component. If the calculation fails, the value is set to None, and should be handled by the user.
    """
    hvs = {key: [] for key in solution_sets}
    solution_sets[next(iter(solution_sets.keys()))].shape[1]

    for rp in reference_points_component:
        hv = Hypervolume(rp)
        for set_name, sols in solution_sets.items():
            ind = hv(sols)
            if ind is None:
                warn("Hypervolume calculation failed. Setting value to None", category=RuntimeWarning, stacklevel=2)
                hvs[set_name].append(None)
            else:
                hvs[set_name].append(float(ind))

    return hvs


class DistanceIndicators(BaseModel):
    """A container for closely related distance based indicators."""

    igd: float = Field(description="The inverted generational distance (IGD) indicator value.")
    "The inverted generational distance (IGD) indicator value."
    igd_p: float = Field(
        description=(
            "The IGD_p indicator, where instead of the arithmetic mean of the distances, the "
            "generalized (power) mean of order p is taken. Equals `igd` when p == 1."
        )
    )
    "The IGD_p indicator, where instead of the arithmetic mean of the distances, the generalized (power) mean"
    " of order p is taken. Equals `igd` when p == 1."
    gd: float = Field(description="The generational distance (GD) indicator value.")
    "The generational distance (GD) indicator value."
    gd_p: float = Field(
        description=(
            "The GD_p indicator, where instead of the arithmetic mean of the distances, the "
            "generalized (power) mean of order p is taken. Equals `gd` when p == 1."
        )
    )
    "The GD_p indicator, where instead of the arithmetic mean of the distances, the generalized (power) mean"
    " of order p is taken. Equals `gd` when p == 1."
    ahd: float = Field(description="The averaged Hausdorff distance (Delta_p) indicator value, max(igd_p, gd_p).")
    "The averaged Hausdorff distance (Delta_p) indicator value, max(igd_p, gd_p)."


def _power_mean(distances: np.ndarray, p: float) -> float:
    """Computes the generalized (power) mean of order p of a 1D array of non-negative distances.

    Args:
        distances (np.ndarray): A 1D array of non-negative distances.
        p (float): The order of the mean. Must be positive. np.inf (or math.inf) yields the maximum.

    Returns:
        float: The generalized mean of order p.
    """
    if np.isinf(p):
        return float(distances.max())
    return float(np.mean(distances**p) ** (1 / p))


def distance_indicators(
    solution_set: np.ndarray, reference_set: np.ndarray, p: float = 2.0, distance_p: float = 2.0
) -> DistanceIndicators:
    """Calculates various distance based indicators between a solution set and a reference set.

    Given the point-to-set distances `d_i`, the indicators are

        IGD   = mean over the reference set of the distance to the closest solution,
        GD    = mean over the solution set of the distance to the closest reference point,
        IGD_p = (mean(d_i**p))**(1/p) over the reference set,
        GD_p  = (mean(d_i**p))**(1/p) over the solution set,
        AHD   = max(IGD_p, GD_p), the averaged Hausdorff distance Delta_p.

    Note that `p` only controls the averaging; the point-to-point distance is controlled separately by
    `distance_p` and defaults to the Euclidean distance, matching the definitions used by `moocore` and by
    Schuetze et al. Consequently, IGD_p and GD_p coincide with IGD and GD when `p == 1`.

    Args:
        solution_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of the set itself
            can lie within the hypercube, but not outside it. The solutions are assumed to be non-dominated.
        reference_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of the reference
            set should probably be (0, 0, ..., 0) and (1, 1, ..., 1) respectively. The reference set is assumed to be
            non-dominated.
        p (float, optional): The order of the generalized mean used to aggregate the distances into IGD_p, GD_p, and
            AHD. Must be positive; np.inf (or math.inf) aggregates by taking the maximum distance, giving the
            (non-averaged) Hausdorff distance. Defaults to 2.0.
        distance_p (float, optional): The power of the Minkowski metric used for the point-to-point distances. Set to 1
            for Manhattan distance, 2 for Euclidean distance, and np.inf (or math.inf) for Chebyshev distance. Defaults
            to 2.0, i.e., the Euclidean distance used by the standard definitions of these indicators.

    Returns:
        DistanceIndicators: A Pydantic class containing the IGD, IGD_p, GD, GD_p, and AHD indicator values.

    Raises:
        ValueError: If `p` or `distance_p` is not positive.
    """
    if p <= 0:
        raise ValueError(f"'p' must be positive, got {p}.")
    if distance_p <= 0:
        raise ValueError(f"'distance_p' must be positive, got {distance_p}.")

    distance_matrix = cdist(solution_set, reference_set, metric="minkowski", p=distance_p)
    # For each reference point, the distance to the closest solution, and vice versa.
    igd_distances = np.min(distance_matrix, axis=0)
    gd_distances = np.min(distance_matrix, axis=1)

    _igd = float(igd_distances.mean())
    _gd = float(gd_distances.mean())
    _igd_p = _power_mean(igd_distances, p)
    _gd_p = _power_mean(gd_distances, p)
    _ahd = max(_igd_p, _gd_p)
    return DistanceIndicators(igd=_igd, igd_p=_igd_p, gd=_gd, gd_p=_gd_p, ahd=_ahd)


def distance_indicators_batch(
    solution_sets: dict[str, np.ndarray], reference_set: np.ndarray, p: float = 2.0, distance_p: float = 2.0
) -> dict[str, DistanceIndicators]:
    """Calculate the IGD, GD, GD_p, IGD_p, and AHD for a sets of solutions.

    Args:
        solution_sets (dict[str, np.ndarray]): A dict of strings mapped to 2D numpy arrays where each array contains a
            set of solutions. Each row is a solution and each column is an
            objective value. The solutions are assumed to be normalized within
            the unit hypercube. The ideal and nadir of the set itself can lie
            within the hypercube, but not outside it. The solutions are assumed
            to be non-dominated within their respective sets. The sets must have
            the same number of objectives/columns but can have different number
            of solutions/rows. The keys of the dict are the names of the sets.
        reference_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of the reference
            set should probably be (0, 0, ..., 0) and (1, 1, ..., 1) respectively. The reference set is assumed to be
            non-dominated.
        p (float, optional): The order of the generalized mean used to aggregate the distances into IGD_p, GD_p, and
            AHD. Must be positive; np.inf (or math.inf) aggregates by taking the maximum distance. Defaults to 2.0.
        distance_p (float, optional): The power of the Minkowski metric used for the point-to-point distances. Set to 1
            for Manhattan distance, 2 for Euclidean distance, and np.inf (or math.inf) for Chebyshev distance. Defaults
            to 2.0, i.e., the Euclidean distance used by the standard definitions of these indicators.

    Returns:
        dict[str, DistanceIndicators]: A dict of strings mapped to DistanceIndicators objects. The keys of the dict are
            the names of the sets. The DistanceIndicators objects contain the IGD, IGD_p, GD, GD_p, and AHD indicator
            values. This data structure can be easily converted to a DataFrame or saved to disk as a JSON file.
    """
    inds = {}
    for set_name, sols in solution_sets.items():
        inds[set_name] = distance_indicators(sols, reference_set, p=p, distance_p=distance_p)
    return inds


class IGDPlusIndicators(BaseModel):
    """A container for the IGD+ distance-based indicator."""

    igd_plus: float = Field(description="The modified inverted generational distance (IGD+) indicator value.")


def igd_plus_indicator(solution_set: np.ndarray, reference_set: np.ndarray, p: float = 2.0) -> IGDPlusIndicators:
    """Computes the IGD+ indicator for a given solution set.

    Notes:
        The minimization of the objective function values is assumed.

        IGD+ is defined by Ishibuchi et al. (2015) in terms of the Euclidean distance, i.e., p == 2, which is the
        default here. Other values of `p` give a non-standard generalization that will not match the IGD+ values
        reported by, e.g., `moocore` or `pymoo`.

    Args:
        solution_set (np.ndarray): The solution set being evaluated.
        reference_set (np.ndarray): The reference Pareto front.
        p (float, optional): The power of the Minkowski metric. Defaults to 2.0 (Euclidean distance).

    Returns:
        IGDPlusIndicators: A Pydantic class containing the IGD+ indicator value.
    """
    num_ref_points = reference_set.shape[0]
    total_distance = 0.0

    for y_p in reference_set:
        min_distance = float("inf")

        for y_n in solution_set:
            # Compute IGD+ distance (only positive differences)
            distance = np.sum(np.maximum(0, y_n - y_p) ** p)  # Sum over objectives
            min_distance = min(min_distance, distance)  # Store the closest one

        total_distance += min_distance ** (1 / p)  # Apply the root AFTER summing over objectives

    igd_plus_value = total_distance / num_ref_points
    return IGDPlusIndicators(igd_plus=igd_plus_value)


def igd_plus_batch(
    solution_sets: dict[str, np.ndarray], reference_set: np.ndarray, p: float = 2.0
) -> dict[str, IGDPlusIndicators]:
    """Computes the IGD+ indicator for multiple solution sets.

    Notes:
        The minimization of the objective function values is assumed.

    Args:
        solution_sets (dict[str, np.ndarray]): A dictionary of solution sets.
        reference_set (np.ndarray): The reference Pareto front.
        p (float, optional): The power of the Minkowski metric. Defaults to 2.0 (Euclidean distance).

    Returns:
        dict[str, IGDPlusIndicators]: A dictionary of IGDPlusIndicators.
    """
    results = {}
    for set_name, solution_set in solution_sets.items():
        results[set_name] = igd_plus_indicator(solution_set, reference_set, p)
    return results


class R2Indicator(BaseModel):
    """Container for the R2 indicator value of a solution set."""

    r2_value: float
    """The R2 indicator value. **Higher is better, and the value is always negative.**

    This is the utility form of R2, and it is the opposite orientation to every other indicator in
    this module. See `r2_indicator` for why, and do not put it on a chart beside IGD+ or GD without
    flipping its sign first."""


def tchebycheff_utility(fx: np.ndarray, lambd: np.ndarray, z_star: np.ndarray, rho: float = 0.05) -> float:
    """Calculates the augmented Tchebycheff utility of a solution.

    A *utility*, so it is the negated achievement scalarising value and **higher is better**. It is
    always negative, reaching zero only for a solution sitting on the ideal point.
    """
    diff = np.abs(z_star - fx)
    max_term = np.max(lambd * diff)
    sum_term = np.sum(diff)
    return -(max_term + rho * sum_term)


def r2_indicator(
    solution_set: np.ndarray, lambda_set: np.ndarray, z_star: np.ndarray, rho: float = 0.05
) -> R2Indicator:
    """Computes the unary R2 indicator for a given solution set.

    **Higher is better, and the value is always negative** -- the opposite of every other indicator
    in this module, and the single most likely thing to be got wrong about it.

    Two conventions for unary R2 are in use and they differ by a sign. This is the *utility* form of
    Brockhoff, Wagner and Trautmann: the mean over weight vectors of the best utility any solution
    achieves, where the utility is a negated Tchebycheff distance. PlatEMO and jMetal report the
    *distance* form instead -- the mean over weight vectors of the smallest Tchebycheff distance --
    which is non-negative and minimised. The two are exact negations of each other, so
    `-r2_value` converts this to the value those frameworks print.

    Args:
        solution_set (np.ndarray): The Pareto front approximation.
        lambda_set (np.ndarray): The set of normalized weight vectors (λ).
        z_star (np.ndarray): The ideal point (must dominate or weakly dominate all solutions).
        rho (float, optional): Small positive number for augmented Tchebycheff. Default is 0.05.

    Returns:
        R2IndicatorResult: Pydantic class with R2 value. Higher is better; see above.

    References:
        Brockhoff, D., Wagner, T., & Trautmann, H. (2012). On the properties of the R2 indicator.
            In Proceedings of the 14th Annual Conference on Genetic and Evolutionary Computation
            (pp. 465-472). https://doi.org/10.1145/2330163.2330230

        Hansen, M. P., & Jaszkiewicz, A. (1998). Evaluating the quality of approximations to the
            non-dominated set. IMM Technical Report IMM-REP-1998-7, Technical University of Denmark.
    """
    total_score = 0.0
    for lambd in lambda_set:
        best_score = max(tchebycheff_utility(fx, lambd, z_star, rho) for fx in solution_set)
        total_score += best_score

    r2_value = total_score / len(lambda_set)
    return R2Indicator(r2_value=r2_value)


def r2_batch(
    solution_sets: dict[str, np.ndarray], lambda_set: np.ndarray, z_star: np.ndarray, rho: float = 0.05
) -> dict[str, R2Indicator]:
    """Computes the R2 indicator for multiple solution sets.

    Args:
        solution_sets (dict[str, np.ndarray]): Dictionary of solution sets.
        lambda_set (np.ndarray): Set of weight vectors.
        z_star (np.ndarray): Ideal point.
        rho (float, optional): Augmented Tchebycheff parameter.

    Returns:
        dict[str, R2IndicatorResult]: Dictionary of results.
    """
    return {name: r2_indicator(solution_set, lambda_set, z_star, rho) for name, solution_set in solution_sets.items()}


class RMetricIndicators(BaseModel):
    """A container for R-metric indicators: R-HV and R-IGD."""

    r_hv: float = Field(description="The R-HV indicator value, based on hypervolume.")
    "The R-HV indicator value, based on hypervolume."
    r_igd: float = Field(description="The R-IGD indicator value, based on inverted generational distance.")
    "The R-IGD indicator value, based on inverted generational distance."


def r_metric_indicator(
    solution_set: np.ndarray, ref_points: np.ndarray, w: np.ndarray = None, delta: float = 0.2
) -> RMetricIndicators:
    """Calculate the R-metric (either R-HV or R-IGD) for a given solution set.

    Parameters:
    solution_set : np.ndarray
        The set of solutions.

    ref_points : np.ndarray
        A set of reference points..

    w : np.ndarray, optional
        Weights for each objective.

    delta : float, optional
        Region of interest for the metric calculation.

    Returns:
    RMetricIndicators
        An object containing the computed R-HV and R-IGD values.
    """
    # Calculate the Pareto front
    pareto_front = get_pareto_front(solution_set)

    rmetric = RMetric(problem=None, ref_points=ref_points, w=w, delta=delta, pf=pareto_front)
    r_igd, r_hv = rmetric.do(solution_set)
    return RMetricIndicators(r_hv=r_hv, r_igd=r_igd)


def r_metric_indicators_batch(
    solution_set: dict[str, np.ndarray], ref_points: np.ndarray, w: np.ndarray = None, delta: float = 0.2
) -> dict[str, RMetricIndicators]:
    """Calculate the R-metrics (R-HV and R-IGD) for a batch of solution sets."""
    inds = {}
    for set_name, sols in solution_set.items():
        inds[set_name] = r_metric_indicator(sols, ref_points, w, delta)
    return inds


def is_dominated(solution, other_solutions):
    """Check if a solution is dominated by any other solution."""
    return any(np.all(other <= solution) and np.any(other < solution) for other in other_solutions)


def get_pareto_front(solutions):
    """Extract the Pareto front from a set of solutions."""
    pareto_front = []
    for i, solution in enumerate(solutions):
        remaining_solutions = np.delete(solutions, i, axis=0)
        if not is_dominated(solution, remaining_solutions):
            pareto_front.append(solution)
    return np.array(pareto_front)


class DPhiIndicators(BaseModel):
    """A container for the desirability based hypervolume indicator D-PHI and its complementary indicator."""

    d_phi: float = Field(description="The D-PHI indicator value. Higher is better.")
    "The D-PHI indicator value. Higher is better."

    ci: float = Field(
        description=(
            "The complementary indicator (CI) value, the negated achievement scalarizing function value of the "
            "best solution in the set with respect to the aspiration and reservation points. Higher is better, "
            "and the value is non-negative if and only if at least one solution reaches all aspiration levels."
        )
    )
    "The complementary indicator (CI) value. Higher is better."


def _as_objective_vector(value: float | np.ndarray, num_objectives: int, name: str) -> np.ndarray:
    """Broadcasts a scalar or a 1-D array into a 1-D array with one entry per objective.

    Args:
        value (float | np.ndarray): A scalar shared by all objectives, or one value per objective.
        num_objectives (int): The number of objectives, i.e., the length of the returned array.
        name (str): The name of the argument, used in the error message.

    Returns:
        np.ndarray: A 1-D array of length `num_objectives`.

    Raises:
        ValueError: If `value` is neither a scalar nor of length `num_objectives`.
    """
    array = np.atleast_1d(np.asarray(value, dtype=float)).flatten()

    if array.size == 1:
        return np.full(num_objectives, array[0])

    if array.size != num_objectives:
        raise ValueError(
            f"'{name}' must be a scalar or have one value per objective ({num_objectives}), got {array.size}."
        )

    return array


def desirability_values(
    solution_set: np.ndarray,
    aspiration_point: float | np.ndarray,
    reservation_point: float | np.ndarray,
    *,
    c1: float | np.ndarray = 1.0,
    c2: float | np.ndarray = 0.0,
    epsilon_a: float | np.ndarray = 0.2,
    epsilon_r: float | np.ndarray = 0.2,
    delta: float = 1e-2,
) -> np.ndarray:
    """Maps objective vectors to desirability values using the desirability function of D-PHI.

    The desirability function is defined objective-wise and is piecewise: it is linear between the aspiration
    level `a` and the reservation level `r`, mapping `a` to `c1` and `r` to `c2`, and it is hyperbolic outside
    that interval. The hyperbolic pieces approach the limits `c1 + epsilon_a` (for values better than the
    aspiration level) and `c2 - epsilon_r` (for values worse than the reservation level) without ever reaching
    them, so the desirability values are always in the open interval `(c2 - epsilon_r, c1 + epsilon_a)`.

    Note:
        The minimization of the objective function values is assumed, and desirability values are maximized.

    Args:
        solution_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective
            value.
        aspiration_point (float | np.ndarray): The aspiration point, containing one aspiration level per objective.
            A scalar is broadcast to all objectives.
        reservation_point (float | np.ndarray): The reservation point, consisting of the reservation level of each
            objective. A scalar is broadcast to all objectives. Each reservation level must be at least as large
            as the corresponding aspiration level.
        c1 (float | np.ndarray, optional): The desirability of the aspiration levels. Defaults to 1.0.
        c2 (float | np.ndarray, optional): The desirability of the reservation levels. Must be smaller than `c1`.
            Defaults to 0.0.
        epsilon_a (float | np.ndarray, optional): A positive number defining the upper limit `c1 + epsilon_a` of
            the desirability function, controlling how much solutions better than the aspiration levels are
            rewarded. Defaults to 0.2.
        epsilon_r (float | np.ndarray, optional): A positive number defining the lower limit `c2 - epsilon_r` of
            the desirability function, controlling how much solutions worse than the reservation levels are
            penalized. Defaults to 0.2.
        delta (float, optional): A small positive number used in place of `a - r` for objectives where the
            aspiration and reservation levels coincide, keeping the desirability function well defined.
            Defaults to 1e-2.

    Returns:
        np.ndarray: A 2D numpy array of the same shape as `solution_set` containing the desirability values.

    Raises:
        ValueError: If the arguments are of incompatible lengths, if any aspiration level is larger than the
            corresponding reservation level, if `c1` is not larger than `c2`, or if `delta`, `epsilon_a`, or
            `epsilon_r` is not positive.
    """
    solutions = np.atleast_2d(np.asarray(solution_set, dtype=float))
    num_objectives = solutions.shape[1]

    a = _as_objective_vector(aspiration_point, num_objectives, "aspiration_point")
    r = _as_objective_vector(reservation_point, num_objectives, "reservation_point")
    c1 = _as_objective_vector(c1, num_objectives, "c1")
    c2 = _as_objective_vector(c2, num_objectives, "c2")
    epsilon_a = _as_objective_vector(epsilon_a, num_objectives, "epsilon_a")
    epsilon_r = _as_objective_vector(epsilon_r, num_objectives, "epsilon_r")

    if delta <= 0:
        raise ValueError(f"'delta' must be positive, got {delta}.")
    if np.any(a > r):
        raise ValueError("Each aspiration level must be at most as large as the corresponding reservation level.")
    if np.any(c1 <= c2):
        raise ValueError("Each component of 'c1' must be larger than the corresponding component of 'c2'.")
    if np.any(epsilon_a <= 0) or np.any(epsilon_r <= 0):
        raise ValueError("'epsilon_a' and 'epsilon_r' must be positive.")

    # 'a - r' must be strictly negative. Objectives with a == r are handled by substituting -delta.
    a_minus_r = np.where(a < r, a - r, -delta)
    # The inverse slope of the linear piece, always negative.
    inverse_slope = a_minus_r / (c1 - c2)

    desirabilities = np.empty_like(solutions)

    better_than_a = solutions <= a
    worse_than_r = solutions > r
    between = ~better_than_a & ~worse_than_r

    # Broadcast the objective-wise parameters over the solutions.
    a_full, c1_full = np.broadcast_to(a, solutions.shape), np.broadcast_to(c1, solutions.shape)
    r_full, c2_full = np.broadcast_to(r, solutions.shape), np.broadcast_to(c2, solutions.shape)
    eps_a_full, eps_r_full = np.broadcast_to(epsilon_a, solutions.shape), np.broadcast_to(epsilon_r, solutions.shape)
    a_minus_r_full = np.broadcast_to(a_minus_r, solutions.shape)
    inverse_slope_full = np.broadcast_to(inverse_slope, solutions.shape)

    # Better than the aspiration levels: a hyperbola approaching c1 + epsilon_a from below.
    mask = better_than_a
    desirabilities[mask] = -(eps_a_full[mask] ** 2) * inverse_slope_full[mask] / (
        solutions[mask] - a_full[mask] + eps_a_full[mask] * inverse_slope_full[mask]
    ) + (c1_full[mask] + eps_a_full[mask])

    # Between the aspiration and reservation levels: linear from c1 to c2.
    mask = between
    desirabilities[mask] = (
        (c1_full[mask] - c2_full[mask]) * solutions[mask] - c1_full[mask] * r_full[mask] + c2_full[mask] * a_full[mask]
    ) / a_minus_r_full[mask]

    # Worse than the reservation levels: a hyperbola approaching c2 - epsilon_r from above.
    mask = worse_than_r
    desirabilities[mask] = -(eps_r_full[mask] ** 2) * inverse_slope_full[mask] / (
        solutions[mask] - r_full[mask] - eps_r_full[mask] * inverse_slope_full[mask]
    ) + (c2_full[mask] - eps_r_full[mask])

    return desirabilities


def d_phi_indicator(
    solution_set: np.ndarray,
    aspiration_point: float | np.ndarray,
    reservation_point: float | np.ndarray,
    *,
    c1: float | np.ndarray = 1.0,
    c2: float | np.ndarray = 0.0,
    epsilon_a: float | np.ndarray = 0.2,
    epsilon_r: float | np.ndarray = 0.2,
    delta: float = 1e-2,
) -> DPhiIndicators:
    """Computes the D-PHI indicator and its complementary indicator (CI) for a given solution set.

    D-PHI measures the quality of a solution set with respect to preferences expressed as an aspiration point
    and a reservation point. The solutions are first mapped to desirability values, see `desirability_values`,
    and D-PHI is the hypervolume of the mapped set, maximized, with the vector of lower limits
    `c2 - epsilon_r` as the reference point. Because the desirability function is bounded, D-PHI is bounded as
    well, and it is at most `prod(c1 + epsilon_a - c2 + epsilon_r)` over the objectives.

    D-PHI is insensitive to how close the set gets to the aspiration levels once the region between the
    aspiration and reservation points has been covered. The complementary indicator CI is reported alongside it
    for that reason: it is the negated achievement scalarizing function value of the best solution in the set,
    computed with the aspiration point as the reference point and `1 / (r - a)` as the weights. CI is non-negative
    if and only if some solution reaches every aspiration level.

    Note:
        The minimization of the objective function values is assumed.

    Args:
        solution_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective
            value. D-PHI itself does not perform normalization. The set need not be
            mutually non-dominated, since dominated solutions do not affect the
            hypervolume.
        aspiration_point (float | np.ndarray): The aspiration point, containing one aspiration level per objective.
            A scalar is broadcast to all objectives.
        reservation_point (float | np.ndarray): The reservation point, consisting of the reservation level of each
            objective. A scalar is broadcast to all objectives.
        c1 (float | np.ndarray, optional): The desirability of the aspiration levels. Defaults to 1.0.
        c2 (float | np.ndarray, optional): The desirability of the reservation levels. Defaults to 0.0.
        epsilon_a (float | np.ndarray, optional): A positive number defining the upper limit of the desirability
            function. Defaults to 0.2.
        epsilon_r (float | np.ndarray, optional): A positive number defining the lower limit of the desirability
            function, which is also used as the reference point of the hypervolume computation. Defaults to 0.2.
        delta (float, optional): A small positive number used in place of `a - r` for objectives where the
            aspiration and reservation levels coincide. Defaults to 1e-2.

    Returns:
        DPhiIndicators: A Pydantic class containing the D-PHI and CI indicator values.

    Raises:
        ValueError: If `solution_set` is empty, or if the preference information is invalid, see
            `desirability_values`.

    References:
        Liang, M., Shavazipour, B., Saini, B., & Emmerich, M. (2026). D-PHI: Desirability-based hypervolume
            indicator for interactive multiobjective optimization using aspiration and reservation levels as
            preferences. ACM Transactions on Evolutionary Learning and Optimization.
            https://doi.org/10.1145/3794854
    """
    solutions = np.atleast_2d(np.asarray(solution_set, dtype=float))

    if solutions.size == 0:
        raise ValueError("'solution_set' must contain at least one solution.")

    num_objectives = solutions.shape[1]
    a = _as_objective_vector(aspiration_point, num_objectives, "aspiration_point")
    r = _as_objective_vector(reservation_point, num_objectives, "reservation_point")

    desirabilities = desirability_values(
        solutions, a, r, c1=c1, c2=c2, epsilon_a=epsilon_a, epsilon_r=epsilon_r, delta=delta
    )

    # The lower limits of the desirability function are the reference point. No solution can reach them, so the
    # reference point is always dominated, and dominated solutions can be passed to the hypervolume as they are.
    reference_point = _as_objective_vector(c2, num_objectives, "c2") - _as_objective_vector(
        epsilon_r, num_objectives, "epsilon_r"
    )

    hypervolume = Hypervolume(ref=reference_point, maximise=True)
    d_phi_value = hypervolume(desirabilities)

    if d_phi_value is None:
        raise ValueError("D-PHI calculation failed.")

    # CI: the negated ASF value of the best solution, with the aspiration point as the reference point.
    weights = 1 / np.where(a < r, r - a, delta)
    ci_value = -np.min(np.max(weights * (solutions - a), axis=1))

    return DPhiIndicators(d_phi=float(d_phi_value), ci=float(ci_value))


def d_phi_batch(
    solution_sets: dict[str, np.ndarray],
    aspiration_point: float | np.ndarray,
    reservation_point: float | np.ndarray,
    *,
    c1: float | np.ndarray = 1.0,
    c2: float | np.ndarray = 0.0,
    epsilon_a: float | np.ndarray = 0.2,
    epsilon_r: float | np.ndarray = 0.2,
    delta: float = 1e-2,
) -> dict[str, DPhiIndicators]:
    """Computes the D-PHI and CI indicators for multiple solution sets.

    Note:
        The minimization of the objective function values is assumed.

    Args:
        solution_sets (dict[str, np.ndarray]): A dict of strings mapped to 2D numpy arrays where each array
            contains a set of solutions. The keys of the dict are the names of the sets. The sets must have the
            same number of objectives/columns but can have a different number of solutions/rows.
        aspiration_point (float | np.ndarray): The aspiration point, shared by all the sets.
        reservation_point (float | np.ndarray): The reservation point, shared by all the sets.
        c1 (float | np.ndarray, optional): The desirability of the aspiration levels. Defaults to 1.0.
        c2 (float | np.ndarray, optional): The desirability of the reservation levels. Defaults to 0.0.
        epsilon_a (float | np.ndarray, optional): The upper limit parameter. Defaults to 0.2.
        epsilon_r (float | np.ndarray, optional): The lower limit parameter. Defaults to 0.2.
        delta (float, optional): A small positive number, see `d_phi_indicator`. Defaults to 1e-2.

    Returns:
        dict[str, DPhiIndicators]: A dict of strings mapped to DPhiIndicators objects. The keys of the dict are
            the names of the sets.
    """
    return {
        set_name: d_phi_indicator(
            sols,
            aspiration_point,
            reservation_point,
            c1=c1,
            c2=c2,
            epsilon_a=epsilon_a,
            epsilon_r=epsilon_r,
            delta=delta,
        )
        for set_name, sols in solution_sets.items()
    }


class PhiPlusIndicator(BaseModel):
    """A container for the PHI+ indicator."""

    phi_plus: float = Field(
        description=(
            "The PHI+ indicator value, the share of the region of interest covered by the solution set. Higher is "
            "better. The value is zero if no solution falls in the region of interest, and it exceeds one when "
            "the set contains solutions better than the reference point."
        )
    )
    "The PHI+ indicator value. Higher is better."


def phi_plus_indicator(
    solution_set: np.ndarray,
    reference_point: float | np.ndarray,
    deviations_lower: float | np.ndarray,
    deviations_upper: float | np.ndarray,
) -> PhiPlusIndicator:
    """Computes the PHI+ indicator for a given solution set.

    PHI+ measures how well a solution set covers a region of interest around a reference point given by a
    decision maker. The region of interest is the box spanned by the lower point `reference_point -
    deviations_lower` and the upper point `reference_point + deviations_upper`. Solutions inside that box, as
    well as any solution dominating the reference point, are taken into account; everything else is discarded.

    The indicator is the hypervolume of the retained solutions, computed with the upper point as the reference
    point, divided by the largest hypervolume that solutions in the region of interest could attain. The
    normalizing quantity depends on whether the reference point is attainable: if some solution dominates the
    reference point, the hypervolume of the reference point itself is used; otherwise the hypervolume of the
    lower point minus the volume of the box between the lower point and the reference point is used, since no
    solution can occupy that box. The indicator is 0 when the region of interest contains no solutions, and it
    exceeds 1 when the set contains solutions better than the reference point.

    Note:
        The minimization of the objective function values is assumed. Following the assumptions of this module,
        the solution set, the reference point, and the deviations are all expected to be given in the same
        normalized objective space, and no further normalization is applied here.

    Args:
        solution_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective
            value. The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of
            the set itself can lie within the hypercube, but not outside it. Dominated solutions are filtered out
            before the indicator is computed.
        reference_point (float | np.ndarray): The reference point of the decision maker, given in the same normalized
            objective space as the solutions.
        deviations_lower (float | np.ndarray): The distance from the reference point to the lower (better)
            boundary of the region of interest, per objective. Must be non-negative; zero means that the region
            of interest is not extended past the reference point in that direction. A scalar is broadcast to all
            objectives.
        deviations_upper (float | np.ndarray): The distance from the reference point to the upper (worse)
            boundary of the region of interest, per objective. Must be positive so that the hypervolume between
            the reference point and the upper point is strictly positive. A scalar is broadcast to all objectives.

    Returns:
        PhiPlusIndicator: A Pydantic class containing the PHI+ indicator value.

    Raises:
        ValueError: If the deviations are of an incompatible length, if any lower deviation is negative, or if
            any upper deviation is not positive.

    References:
        Liang, M., Shavazipour, B., Saini, B., Emmerich, M., & Miettinen, K. (2024). A modified preference-based
            hypervolume indicator for interactive evolutionary multiobjective optimization methods. In Proceedings
            of the 16th International Joint Conference on Computational Intelligence (pp. 214-221). SCITEPRESS.
    """
    solutions = np.atleast_2d(np.asarray(solution_set, dtype=float))

    if solutions.size == 0:
        return PhiPlusIndicator(phi_plus=0.0)

    num_objectives = solutions.shape[1]
    rp = _as_objective_vector(reference_point, num_objectives, "reference_point")
    dev_lower = _as_objective_vector(deviations_lower, num_objectives, "deviations_lower")
    dev_upper = _as_objective_vector(deviations_upper, num_objectives, "deviations_upper")

    if np.any(dev_lower < 0):
        raise ValueError("'deviations_lower' must be non-negative.")
    if np.any(dev_upper <= 0):
        raise ValueError("'deviations_upper' must be positive to keep the PHI+ normalization denominator well defined.")

    lower_point = rp - dev_lower
    upper_point = rp + dev_upper

    non_dominated_solutions = solutions[non_dominated(solutions)]

    # Solutions inside the box spanned by the lower and the upper point, plus any solution dominating the
    # reference point, form the (modified) region of interest.
    in_box = np.all((non_dominated_solutions >= lower_point) & (non_dominated_solutions <= upper_point), axis=1)
    dominates_rp = np.all(non_dominated_solutions < rp, axis=1)
    in_region = in_box | dominates_rp
    solutions_in_region = non_dominated_solutions[in_region]

    if solutions_in_region.size == 0:
        return PhiPlusIndicator(phi_plus=0.0)

    # Positive upper deviations guarantee that the reference point dominates the upper point, so both of the
    # normalizing quantities below are strictly positive.
    hypervolume = Hypervolume(ref=upper_point)

    if np.any(dominates_rp):
        # The reference point is attainable, so the whole of its hypervolume can be covered.
        best_possible = hypervolume(rp.reshape(1, -1))
    else:
        # No solution dominates the reference point, so the box between the lower point and the reference point
        # is unreachable and is subtracted from the hypervolume of the lower point.
        best_possible = hypervolume(lower_point.reshape(1, -1)) - np.prod(dev_lower)

    return PhiPlusIndicator(phi_plus=float(hypervolume(solutions_in_region) / best_possible))


def phi_plus_batch(
    solution_sets: dict[str, np.ndarray],
    reference_point: float | np.ndarray,
    deviations_lower: float | np.ndarray,
    deviations_upper: float | np.ndarray,
) -> dict[str, PhiPlusIndicator]:
    """Computes the PHI+ indicator for multiple solution sets.

    Note:
        The minimization of the objective function values is assumed.

    Args:
        solution_sets (dict[str, np.ndarray]): A dict of strings mapped to 2D numpy arrays where each array
            contains a set of solutions. The keys of the dict are the names of the sets. The sets must have the
            same number of objectives/columns but can have a different number of solutions/rows.
        reference_point (float | np.ndarray): The reference point of the decision maker, shared by all the sets.
        deviations_lower (float | np.ndarray): The distances to the lower boundary of the region of interest.
        deviations_upper (float | np.ndarray): The distances to the upper boundary of the region of interest.

    Returns:
        dict[str, PhiPlusIndicator]: A dict of strings mapped to PhiPlusIndicator objects. The keys of the dict
            are the names of the sets.
    """
    return {
        set_name: phi_plus_indicator(sols, reference_point, deviations_lower, deviations_upper)
        for set_name, sols in solution_sets.items()
    }


# Additional unary indicators can be added here.
# E.g. The IGD+ indicator, R2 indicator, averaged Hausdorff distance, etc.
# The function signature should be similar the already implemented functions, if reasonable.
# Optionally, a batch version of the indicator can be added as well.
# The methods should make similar assumptions about the input data as the already implemented functions.
