"""This module implements unary indicators that can be used to compare two solution sets.

It assumes that the solution set has been normalized just that _some_ ideal point (not necessarily the ideal point
of the set) is the origin and _some_ nadir point (not necessarily the nadir point of the set) is (1, 1, ..., 1).
The normalized solution set is assumed to be inside the bounding box [0, 1]^k where k is the number of objectives.
If these conditions are not met, the results of the indicators will not be meaningful.

Additionally, the set may be assumed to only contain mutually non-dominated solutions, depending on the indicator.

For now, we rely on pymoo for the implementation of many of the indicators.
"""

from typing import Literal

import numpy as np
from moocore import epsilon_additive, epsilon_mult
from numba import njit
from desdeo.tools.non_dominated_sorting import dominates
from desdeo.tools.indicators_unary import hv

"""
Note that the moocore package includes a more complex implementation for calculating the epsilon_indicator for two
solution *sets*.
"""


@njit()
def epsilon_component(solution1: np.ndarray, solution2: np.ndarray) -> float:
    """Computes the additive epsilon-indicator between two solutions.

    Args:
        solution1 (np.ndarray): Should be an one-dimensional array, where each value is normalized between [0, 1]
        solution2 (np.ndarray): Should be an one-dimensional array, where each value is normalized between [0, 1]

    Returns:
        float: The maximum distance between the values in s1 and s2.
    """
    return max(0.0, max(solution1 - solution2))


@njit()
def self_epsilon(solution_set: np.ndarray) -> np.ndarray:
    """Computes the pairwise additive epsilon-indicator for a solution set.

    Args:
        solution_set (np.ndarray): Should be a two-dimensional array, where each row is a
            solution normalized between [0, 1].

    Returns:
        np.ndarray: A two-dimensional array where the entry at (i, j) is the
            additive epsilon-indicator between the i-th and j-th solution in the set.
    """
    n_solutions = solution_set.shape[0]
    eps_matrix = np.zeros((n_solutions, n_solutions), dtype=np.float64)
    for i in range(n_solutions):
        for j in range(n_solutions):
            eps_matrix[i, j] = epsilon_component(solution_set[i], solution_set[j])
    return eps_matrix


def epsilon_indicator(
    set1: np.ndarray, set2: np.ndarray, kind: Literal["additive", "multiplicative"] = "additive"
) -> float:
    """Computes the additive epsilon-indicator between two solution sets.

    Args:
        set1 (np.ndarray): Should be a two-dimensional array, where each row is a solution normalized between [0, 1]
        set2 (np.ndarray): Should be a two-dimensional array, where each row is a solution normalized between [0, 1]
        kind (Literal["additive", "multiplicative"]): The kind of epsilon-indicator to compute. Defaults to "additive".

    Returns:
        float: the  epsilon-indicator between the two sets.
    """
    if kind == "additive":
        return epsilon_additive(set1, ref=set2)
    if kind == "multiplicative":
        return epsilon_mult(set1, ref=set2)
    raise ValueError(f"Unknown kind: {kind}. Use 'additive' or 'multiplicative'.")


def hv_component(solution1: np.ndarray, solution2: np.ndarray, ref: float = 2.0) -> float:
    """Computes the hypervolume contribution of solution1 with respect to solution2.

    Args:
        solution1 (np.ndarray): Should be an one-dimensional array, where each value is normalized between [0, 1]
        solution2 (np.ndarray): Should be an one-dimensional array, where each value is normalized between [0, 1]
        ref (float): The reference point for the hypervolume calculation. Defaults to 2.0.

    Returns:
        float: The hypervolume contribution of solution1 with respect to solution2.
    """
    if dominates(solution1, solution2):
        return np.prod(ref - solution2) - np.prod(ref - solution1)
    return hv(solution_set=np.array([solution1, solution2]), reference_point_component=ref)


def self_hv(solution_set: np.ndarray, ref: float = 2.0) -> np.ndarray:
    """Computes the pairwise hypervolume contribution for a solution set.

    Args:
        solution_set (np.ndarray): Should be a two-dimensional array, where each row is a
            solution normalized between [0, 1].
        ref (float): The reference point for the hypervolume calculation. Defaults to 2.0.

    Returns:
        np.ndarray: A two-dimensional array where the entry at (i, j) is the
            hypervolume contribution of the i-th solution with respect to the j-th solution in the set.
    """
    n_solutions = solution_set.shape[0]
    hv_matrix = np.zeros((n_solutions, n_solutions), dtype=np.float64)
    for i in range(n_solutions):
        for j in range(n_solutions):
            hv_matrix[i, j] = hv_component(solution_set[i], solution_set[j], ref=ref)
    return hv_matrix
