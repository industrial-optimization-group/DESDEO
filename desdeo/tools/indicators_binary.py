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
from numba import njit
from moocore import epsilon_additive, epsilon_mult

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
    eps = 0.0
    for i in range(solution1.size):
        value = solution1[i] - solution2[i]
        if value > eps:
            eps = value
    return eps


def epsilon_indicator(
    set1: np.ndarray, set2: np.ndarray, kind: Literal["additive", "multiplicative"] = "additive"
) -> float:
    """Computes the additive epsilon-indicator between two solution sets.

    Args:
        set1 (np.ndarray): Should be a two-dimensional array, where each row is a solution normalized between [0, 1]
        set2 (np.ndarray): Should be a two-dimensional array, where each row is a solution normalized between [0, 1]

    Returns:
        float: the  epsilon-indicator between the two sets.
    """
    if kind == "additive":
        return epsilon_additive(set1, ref=set2)
    if kind == "multiplicative":
        return epsilon_mult(set1, ref=set2)
    raise ValueError(f"Unknown kind: {kind}. Use 'additive' or 'multiplicative'.")
