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
from pydantic import BaseModel, Field
from pymoo.indicators.hv import Hypervolume
from pymoo.indicators.rmetric import RMetric
from scipy.spatial.distance import cdist
from typing import Dict
from desdeo.tools.non_dominated_sorting import dominates, fast_non_dominated_sort_indices


def hv(solution_set: np.ndarray, reference_point_component: float | np.ndarray) -> float:
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
    rp = np.full(solution_set.shape[1], reference_point_component, dtype=np.float64)
    ideal = np.zeros(solution_set.shape[1], dtype=np.float64)
    nadir = np.ones(solution_set.shape[1], dtype=np.float64)

    # Sets the ideal and nadir to (0, 0, ..., 0) and (1, 1, ..., 1) respectively.
    # Turns of non-domination checks.
    # Turns of normalization of the reference point
    hv = Hypervolume(ref_point=rp, ideal=ideal, nadir=nadir, nds=False, norm_ref_point=False)

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
    num_objs = solution_sets[next(iter(solution_sets.keys()))].shape[1]

    for rp in reference_points_component:
        hv = Hypervolume(
            ref_point=np.full(num_objs, rp, dtype=np.float64),
            ideal=np.zeros(num_objs, dtype=np.float64),
            nadir=np.ones(num_objs, dtype=np.float64),
            nds=False,
            norm_ref_point=False,
        )
        for set_name in solution_sets:
            ind = hv(solution_sets[set_name])
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
    for set_name in solution_sets:
        inds[set_name] = distance_indicators(solution_sets[set_name], reference_set, p=p)
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
    r2_value: float

def tchebycheff_utility(fx: np.ndarray, lambd: np.ndarray, z_star: np.ndarray, rho: float = 0.05) -> float:
    """Calculates the augmented Tchebycheff utility of a solution."""
    diff = np.abs(z_star - fx)
    max_term = np.max(lambd * diff)
    sum_term = np.sum(diff)
    return - (max_term + rho * sum_term)

def r2_indicator(
    solution_set: np.ndarray,
    lambda_set: np.ndarray,
    z_star: np.ndarray,
    rho: float = 0.05
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
        best_score = max(
            tchebycheff_utility(fx, lambd, z_star, rho)
            for fx in solution_set
        )
        total_score += best_score

    r2_value = total_score / len(lambda_set)
    return R2Indicator(r2_value=r2_value)

def r2_batch(
    solution_sets: Dict[str, np.ndarray],
    lambda_set: np.ndarray,
    z_star: np.ndarray,
    rho: float = 0.05
) -> Dict[str, R2Indicator]:
    """Computes the R2 indicator for multiple solution sets.

    Args:
        solution_sets (dict[str, np.ndarray]): Dictionary of solution sets.
        lambda_set (np.ndarray): Set of weight vectors.
        z_star (np.ndarray): Ideal point.
        rho (float, optional): Augmented Tchebycheff parameter.

    Returns:
        dict[str, R2IndicatorResult]: Dictionary of results.
    """
    return {
        name: r2_indicator(solution_set, lambda_set, z_star, rho)
        for name, solution_set in solution_sets.items()
    }

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
    for set_name in solution_set:
        inds[set_name] = r_metric_indicator(solution_set[set_name], ref_points, w, delta)
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

class PHI(object):

    def __init__(self,
                 solution_set: np.ndarray,
                 reference_point: np.ndarray,
                 nadir: np.ndarray,
                 ideal: np.ndarray = None):
        """
        Calculates multiple PHI metrics for solution set and reference point.

        Args:
            solution_set (np.ndarray): 2D numpy arrays where each array contains a set of solutions.
                Each row is a solution and each column is an objective value.
            reference_point (np.ndarray): Numpy array containing a reference point values
            nadir (np.ndarray): Numpy array containing a nadir point values
            ideal (np.ndarray): Numpy array containing a ideal point values. 
                Could be None if we are sure that solution set is non dominated???
        """

        self.solution_set = solution_set
        self.reference_point = reference_point
        self.nadir = nadir
        self.ideal = ideal

        self.is_rp_dominated, self.dom_indices = self.check_rp_dominated(self.solution_set,
                                                                         self.reference_point)

        non_dom_indices = fast_non_dominated_sort_indices(
            np.vstack((self.solution_set, self.reference_point)))[0][0]
        self.non_dom_sols = np.vstack((self.solution_set, self.reference_point))[non_dom_indices]

    def check_rp_dominated(self, set_of_solutions, reference_point) -> tuple[bool, list]:
        """Check if the reference point (RP) is dominated by any solution in set_of_s."""
        dominated = False
        dom_indices = []
        for idx, sol in enumerate(set_of_solutions):
            if dominates(sol, reference_point):
                dom_indices.append(idx)
                dominated = True
        return dominated, dom_indices

    def RP_dom_cal(self, dom_indices):
        """Calculate hypervolume metrics when RP is dominated."""

        if self.ideal is None:
            warn("Cannot calculate phi for dominated without ideal point.",
                 category=RuntimeWarning, stacklevel=2)
            return None

        max_phv = hv(self.ideal.reshape(1, -1), self.nadir)
        all_phv = hv(self.non_dom_sols.reshape(1, -1), self.nadir)
        rp_phv = hv(self.reference_point.reshape(1, -1), self.nadir)
        pos_phv = hv(self.solution_set[dom_indices], self.nadir) - rp_phv
        neg_phv = all_phv - pos_phv - rp_phv

        if all_phv == 0:
            return 0, 0, 0, 0
        else:
            return (1 + (pos_phv / all_phv),
                    (pos_phv + rp_phv) / max_phv,
                    neg_phv / max_phv,
                    rp_phv / max_phv)

    def RP_nondom_cal(self):
        """Calculate hypervolume metrics when RP is non dominated."""

        all_phv = hv(self.non_dom_sols, self.nadir)
        rp_phv = hv(self.reference_point.reshape(1, -1), self.nadir)
        s_phv = hv(self.solution_set, self.nadir)
        nondom_area = all_phv - s_phv
        pos_phv = rp_phv - nondom_area
        neg_phv = all_phv - rp_phv

        if all_phv == 0:
            return 0, 0, 0, 0
        else:
            return (pos_phv / rp_phv,
                    pos_phv / all_phv,
                    neg_phv / all_phv,
                    rp_phv)

    def get_phi(self) -> tuple[bool, tuple] | tuple[None, None]:
        if self.is_rp_dominated:
            if len(self.dom_indices) == len(self.solution_set):
                warn("Warning: No non-dominated solutions found.", category=RuntimeWarning, stacklevel=2)
                return None, None

            results = self.RP_dom_cal(self.dom_indices)
            return True, results
        else:
            results = self.RP_nondom_cal()
            return False, results


class PhiDecision(object):
    def __init__(self, indicator_values: tuple, nadir: np.ndarray):
        """Initialize with the PHI indicator values, and nadir for hypervolume calculations."""
        self.indicator_values = indicator_values
        self.nadir = nadir

        self.combined_hv = None
        self.nadir_1d = None

    def get_areas(self, ref_point1: np.ndarray, ref_point2: np.ndarray) -> float:
        """Calculate the shared hypervolume area between two reference points."""
        # Ensure rp1 and rp2 are 2D arrays
        if ref_point1.ndim == 1:
            ref_point1 = ref_point1.reshape(1, -1)
        if ref_point2.ndim == 1:
            ref_point2 = ref_point2.reshape(1, -1)

        dom21 = dominates(ref_point2.flatten(), ref_point1.flatten())
        dom12 = dominates(ref_point1.flatten(), ref_point2.flatten())
        ref_point1_hv = hv(ref_point1, self.nadir_1d)
        ref_point2_hv = hv(ref_point2, self.nadir_1d)
        combined_hv = hv(np.vstack((ref_point1, ref_point2)), self.nadir_1d)
        self.combined_hv = combined_hv

        if dom21:
            shared_area = ref_point1_hv
        elif dom12:
            shared_area = ref_point2_hv
        else:
            extra_area_in_rp1 = abs(combined_hv - ref_point2_hv)
            shared_area = ref_point1_hv - extra_area_in_rp1
        return shared_area

    def interactions_areas(self, ref_point_set: np.ndarray, main_ref_point: np.ndarray) -> np.ndarray:
        """Calculate interaction areas for a set of reference points and a main reference point."""
        areas = [self.get_areas(ref_point, main_ref_point) for ref_point in ref_point_set]
        return np.asarray(areas)

    def get_weights(self, shared_areas: np.ndarray, main_w) -> np.ndarray:
        """Calculate the weights for the hypervolume shared areas."""
        return shared_areas / self.combined_hv

    def assess(self, weights: np.ndarray, assessment_values: np.ndarray):
        """Assess the decision phase using weighted mean of assessment values."""
        assessment = np.mean(weights * assessment_values)
        return assessment

    def assess_decision_phase(self, set_of_RPs: np.ndarray, main_RP: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Assess the decision phase for a set of reference points and a main reference point."""
        # Reshape main_RP to 2D array if it is 1D
        if main_RP.ndim == 1:
            main_RP = main_RP.reshape(1, -1)

        # Ensure self.nadir is a 1D array
        self.nadir_1d = self.nadir.flatten()

        main_area = hv(main_RP, self.nadir_1d)
        shared_areas = self.interactions_areas(set_of_RPs, main_RP)
        weights = self.get_weights(shared_areas, main_area)
        assessment = self.assess(weights, np.asarray(self.indicator_values))
        return assessment, weights

# Additional unary indicators can be added here.
# E.g. The IGD+ indicator, R2 indicator, averaged Hausdorff distance, etc.
# The function signature should be similar the already implemented functions, if reasonable.
# Optionally, a batch version of the indicator can be added as well.
# The methods should make similar assumptions about the input data as the already implemented functions.
