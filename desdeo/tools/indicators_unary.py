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

    igd: float = Field(description="The inverted generational distance indicator value.")
    "The inverted generational distance indicator value."
    igd_p: float = Field(
        description=(
            "The inverted generational distance indicator, where instead of taking arithmetic "
            "mean of the distances, we take the geometric mean."
        )
    )
    "The inverted generational distance indicator, where instead of taking arithmetic mean of the distances,"
    " we take the geometric mean."
    gd: float = Field(description="The generational distance indicator value.")
    "The generational distance indicator value."
    gd_p: float = Field(
        description=(
            "The generational distance indicator, where instead of taking arithmetic mean of the "
            "distances, we take the geometric mean."
        )
    )
    "The generational distance indicator, where instead of taking arithmetic mean of the distances,"
    " we take the geometric mean."
    ahd: float = Field(description="The average Hausdorff distance indicator value.")
    "The average Hausdorff distance indicator value."


def distance_indicators(solution_set: np.ndarray, reference_set: np.ndarray, p: float = 2.0) -> DistanceIndicators:
    """Calculates various distance based indicators between a solution set and a reference set.

    Args:
        solution_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of the set itself
            can lie within the hypercube, but not outside it. The solutions are assumed to be non-dominated.
        reference_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of the reference
            set should probably be (0, 0, ..., 0) and (1, 1, ..., 1) respectively. The reference set is assumed to be
            non-dominated.
        p (float, optional): The power of the Minkowski metric. Set to 1 for Manhattan distance and 2 for Euclidean
            distance, and np.inf (or math.inf) for Chebyshev distance. Defaults to 2.0.

    Returns:
        DistanceIndicators: A Pydantic class containing the IGD, IGD+, GD, GD+, and AHD indicators values.
    """
    distance_matrix = cdist(solution_set, reference_set, metric="minkowski", p=p)
    _igd = np.min(distance_matrix, axis=0).mean()
    _gd = np.min(distance_matrix, axis=1).mean()
    ref_size = reference_set.shape[0]
    set_size = solution_set.shape[0]

    _igd_p = (_igd * ref_size) / (ref_size ** (1 / p))
    _gd_p = (_gd * set_size) / (set_size ** (1 / p))
    _ahd = max(_igd_p, _gd_p)
    return DistanceIndicators(igd=_igd, igd_p=_igd_p, gd=_gd, gd_p=_gd_p, ahd=_ahd)


def distance_indicators_batch(
    solution_sets: dict[str, np.ndarray], reference_set: np.ndarray, p: float = 2.0
) -> dict[str, DistanceIndicators]:
    """Calculate the IGD, GD, GD_P, IGD_P, and AHD for a sets of solutions.

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
        p (float, optional): The power of the Minkowski metric. Set to 1 for Manhattan distance and 2 for Euclidean
            distance, and np.inf (or math.inf) for Chebyshev distance. Defaults to 2.0.

    Returns:
        dict[str, DistanceIndicators]: A dict of strings mapped to DistanceIndicators objects. The keys of the dict are
            the names of the sets. The DistanceIndicators objects contain the IGD, IGD+, GD, GD+, and AHD indicators
            values. This data structure can be easily converted to a DataFrame or saved to disk as a JSON file.
    """
    inds = {}
    for set_name, sols in solution_sets.items():
        inds[set_name] = distance_indicators(sols, reference_set, p=p)
    return inds


class IGDPlusIndicators(BaseModel):
    """A container for the IGD+ distance-based indicator."""

    igd_plus: float = Field(description="The modified inverted generational distance (IGD+) indicator value.")


def igd_plus_indicator(solution_set: np.ndarray, reference_set: np.ndarray, p: float = 2.0) -> IGDPlusIndicators:
    """Computes the IGD+ indicator for a given solution set.

    Notes:
        The minimization of the objective function values is assumed.

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


def tchebycheff_utility(fx: np.ndarray, lambd: np.ndarray, z_star: np.ndarray, rho: float = 0.05) -> float:
    """Calculates the augmented Tchebycheff utility of a solution."""
    diff = np.abs(z_star - fx)
    max_term = np.max(lambd * diff)
    sum_term = np.sum(diff)
    return -(max_term + rho * sum_term)


def r2_indicator(
    solution_set: np.ndarray, lambda_set: np.ndarray, z_star: np.ndarray, rho: float = 0.05
) -> R2Indicator:
    """Computes the unary R2 indicator for a given solution set.

    Args:
        solution_set (np.ndarray): The Pareto front approximation.
        lambda_set (np.ndarray): The set of normalized weight vectors (λ).
        z_star (np.ndarray): The ideal point (must dominate or weakly dominate all solutions).
        rho (float, optional): Small positive number for augmented Tchebycheff. Default is 0.05.

    Returns:
        R2IndicatorResult: Pydantic class with R2 value.
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


# CHANGE 1: missing helper -- returns the non-dominated INDICES instead of
# the values (the existing get_pareto_front returns values). Used by the
# phi / phi_decision classes to index the original solutions + RP array.
def get_pareto_front_indices(solutions: np.ndarray) -> np.ndarray:
    """Extract the indices of the non-dominated (Pareto front) solutions."""
    nd = []
    for i, solution in enumerate(solutions):
        remaining_solutions = np.delete(solutions, i, axis=0)
        if not is_dominated(solution, remaining_solutions):
            nd.append(i)
    return np.array(nd, dtype=int)


# CHANGE 2: Pydantic model to type the result of phi.get_phi().
# get_phi used to return a plain tuple; this documents the 4 fields in the
# exact order expected by run_adm_phi_pipeline.py (pos, total, neg, rp_hv).
class PHIResult(BaseModel):
    """A container for the PHI indicator (positive/negative/total hypervolume)."""

    positive_hypervolume: float = Field(description="Positive PHV normalized by max PHV.")
    total_hypervolume: float = Field(description="Total PHV normalized by max PHV.")
    negative_hypervolume: float = Field(description="Negative PHV normalized by max PHV.")
    reference_point_hypervolume: float = Field(description="Reference point HV normalized by max PHV.")


# CHANGE 3: Pydantic model for the aggregated decision-phase result
# (phi_decision.assess_decision_phase). Completes the ported API from the
# legacy desdeo-tools/utilities/quality_indicator.py.
class PHIDecisionResult(BaseModel):
    """A container for the aggregated PHI value across a full decision phase."""

    phi: float = Field(description="Decision phase PHI value.")
    weights: list[float] = Field(description="Weights used for each reference point.")


# CHANGE 4: `phi` class -- this is the class imported directly by
# run_adm_phi_pipeline.py (`from desdeo.tools.indicators_unary import phi`).
# It did NOT exist in this file before; this is what caused the ImportError.
# Ported from the legacy desdeo-tools/utilities/quality_indicator.py implementation.
class phi:
    """Preference-based hypervolume (PHI) indicator for a single iteration."""

    def __init__(self, ideal: np.ndarray):
        self.name = "phi"
        self.ideal = np.asarray(ideal, dtype=float)

    # CHANGE 4a: determines whether the reference point (RP) is dominated by
    # any solution in the front. Decides which calculation branch to use next.
    def check_rp_dominated(self, set_of_s: np.ndarray, RP: np.ndarray):
        r = False
        doms = []
        for s in set_of_s:
            if np.all(s <= RP) and np.any(s < RP):
                doms.append(True)
                r = True
            else:
                doms.append(False)
        return r, doms

    # CHANGE 4b: "RP dominated" case -- computes positive/negative/total HV
    # normalized by the maximum HV with respect to the ideal point.
    def RP_dom_cal(self, set_of_s, RP, doms, nadir):
        ind = np.where(np.asarray(doms) == 0)[0]
        stacked = np.vstack([set_of_s, RP])
        nondoms = stacked[get_pareto_front_indices(stacked)]
        max_phv = hv(np.asarray(self.ideal).reshape(1, -1), nadir)
        all_phv = hv(nondoms, nadir)
        rp_phv = hv(np.asarray(RP).reshape(1, -1), nadir)
        pos_phv = hv(np.asarray(set_of_s)[ind], nadir) - rp_phv
        neg_phv = all_phv - pos_phv - rp_phv
        if all_phv == 0:
            return 0.0, 0.0, 0.0, 0.0
        return pos_phv / max_phv, all_phv / max_phv, neg_phv / max_phv, rp_phv / max_phv

    # CHANGE 4c: "RP not dominated" case -- same idea but normalizing
    # against the RP's own HV instead of the ideal point.
    # CHANGE 6: guard against rp_phv == 0. If the reference point sits on
    # (or beyond) the nadir boundary for at least one objective, its own
    # hypervolume w.r.t. nadir is exactly zero, which previously caused a
    # ZeroDivisionError at `pos_phv / rp_phv`. In that degenerate case there
    # is no meaningful "positive" region relative to the RP, so we report
    # pos=0.0 for the two RP-normalized ratios while still reporting the
    # (still valid) neg_phv / all_phv ratio, unless all_phv is also zero.
    def RP_nondom_cal(self, set_of_s, RP, nadir):
        stacked = np.vstack([set_of_s, RP])
        nondoms = stacked[get_pareto_front_indices(stacked)]
        all_phv = hv(nondoms, nadir)
        rp_phv = hv(np.asarray(RP).reshape(1, -1), nadir)
        s_phv = hv(np.asarray(set_of_s), nadir)
        nondom_area = all_phv - s_phv
        pos_phv = rp_phv - nondom_area
        neg_phv = all_phv - rp_phv
        if all_phv == 0:
            return 0.0, 0.0, 0.0, 0.0
        if rp_phv == 0:
            return 0.0, 0.0, neg_phv / all_phv, rp_phv
        return pos_phv / rp_phv, pos_phv / all_phv, neg_phv / all_phv, rp_phv

    # CHANGE 4d: public method called by run_adm_phi_pipeline.py
    # (`self.phi_calculator.get_phi(front, pref_array, self.nadir)`).
    # Automatically decides which branch (dominated / non-dominated) to use.
    def get_phi(self, set_of_s: np.ndarray, RP: np.ndarray, nadir: np.ndarray):
        set_of_s = np.asarray(set_of_s, dtype=float)
        RP = np.asarray(RP, dtype=float)
        nadir = np.asarray(nadir, dtype=float)
        is_rp_dominated, doms = self.check_rp_dominated(set_of_s, RP)
        if is_rp_dominated:
            return self.RP_dom_cal(set_of_s, RP, doms, nadir)
        return self.RP_nondom_cal(set_of_s, RP, nadir)


# CHANGE 5: `phi_decision` class -- aggregates the PHI indicator at the
# level of a full phase (several RPs across several iterations), not just
# per iteration. Not yet used by run_adm_phi_pipeline.py, but available in
# case phi_summary should later be weighted by phase instead of summed/averaged.
class phi_decision:
    """Aggregated PHI indicator across a full interaction phase (learning/decision)."""

    def __init__(self, n_interactions: int, indicator_values, nadir: np.ndarray):
        self.name = "phi_decision"
        self.n_interactions = n_interactions
        self.indicator_values = indicator_values
        self.nadir = np.asarray(nadir, dtype=float)

    # CHANGE 5a: computes the shared HV area between two reference points.
    def get_areas(self, rp1: np.ndarray, rp2: np.ndarray) -> float:
        if rp1.ndim == 1:
            rp1 = rp1.reshape(1, -1)
        if rp2.ndim == 1:
            rp2 = rp2.reshape(1, -1)
        dom21 = is_dominated(rp2.flatten(), rp1)
        dom12 = is_dominated(rp1.flatten(), rp2)
        hv_rp1 = hv(rp1, self.nadir)
        hv_rp2 = hv(rp2, self.nadir)
        hv_rp12 = hv(np.vstack([rp1, rp2]), self.nadir)
        self.hv_rp12 = hv_rp12
        if dom21:
            return hv_rp1
        elif dom12:
            return hv_rp2
        else:
            extra_area_in_rp1 = abs(hv_rp12 - hv_rp2)
            return hv_rp1 - extra_area_in_rp1

    # CHANGE 5b: repeats get_areas against a "main" RP for each intermediate RP.
    def interactions_areas(self, set_of_RPs, main_RP, n_interactions):
        areas = []
        if n_interactions >= 2:
            for s in set_of_RPs:
                areas.append(self.get_areas(s, main_RP))
        else:
            areas = self.get_areas(set_of_RPs, main_RP)
        return areas

    # CHANGE 5c: normalizes the shared areas into weights.
    def get_weights(self, w, main_w):
        return w / self.hv_rp12

    # CHANGE 5d: final weighted average -- the aggregated "phase PHI".
    def assess(self, w, assessment_values):
        return np.mean(w * assessment_values)

    # CHANGE 5e: orchestrates 5a-5d to produce the PHI for the whole decision phase.
    def assess_decision_phase(self, set_of_RPs, main_RP):
        if main_RP.ndim == 1:
            main_RP = main_RP.reshape(1, -1)
        main_area = hv(main_RP, self.nadir)
        shared_areas = self.interactions_areas(set_of_RPs, main_RP, self.n_interactions)
        weights = self.get_weights(np.asarray(shared_areas), main_area)
        results = self.assess(np.asarray(weights), np.asarray(self.indicator_values))
        return results, weights


# Additional unary indicators can be added here.
# E.g. The IGD+ indicator, R2 indicator, averaged Hausdorff distance, etc.
# The function signature should be similar the already implemented functions, if reasonable.
# Optionally, a batch version of the indicator can be added as well.
# The methods should make similar assumptions about the input data as the already implemented functions.