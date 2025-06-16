"""This module implements unary indicators that can be used to compare two solution sets.

It assumes that the solution set has been normalized just that _some_ ideal point (not necessarily the ideal point
of the set) is the origin and _some_ nadir point (not necessarily the nadir point of the set) is (1, 1, ..., 1).
The normalized solution set is assumed to be inside the bounding box [0, 1]^k where k is the number of objectives.
If these conditions are not met, the results of the indicators will not be meaningful.

Additionally, the set may be assumed to only contain mutually non-dominated solutions, depending on the indicator.

For now, we rely on pymoo for the implementation of many of the indicators.
"""

import numpy as np
from numba import njit

"""
Note that the moocore package includes a more complex implementation for calculating the epsilon_indicator for two
solution *sets*.
"""

@njit()
def epsilon_indicator(s1: np.ndarray, s2: np.ndarray) -> float:
    """Computes the additive epsilon-indicator between two solutions.

    Args:
        s1 (np.ndarray): Solution 1. Should be an one-dimensional array, where each value is normalized between [0, 1]
        s2 (np.ndarray): Solution 2. Should be an one-dimensional array, where each value is normalized between [0, 1]

    Returns:
        float: The maximum distance between the values in s1 and s2.
    """
    eps = 0.0
    for i in range(s1.size):
        value = s2[i] - s1[i]
        if value > eps:
            eps = value
    return eps
