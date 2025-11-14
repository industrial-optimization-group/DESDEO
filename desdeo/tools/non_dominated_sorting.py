"""This module contains functions for non-dominated sorting of solutions."""

import numpy as np
from numba import njit  # type: ignore


@njit()
def dominates(x: np.ndarray, y: np.ndarray) -> bool:
    """Returns true if x dominates y.

    Args:
        x (np.ndarray): First solution. Should be a 1-D array of numerics.
        y (np.ndarray): Second solution. Should be the same shape as x.

    Returns:
        bool: True if x dominates y, false otherwise.
    """
    dom = False
    for i in range(len(x)):
        if x[i] > y[i]:
            return False
        elif x[i] < y[i]:
            dom = True
    return dom


@njit()
def non_dominated(data: np.ndarray) -> np.ndarray:
    """Finds the non-dominated front from a population of solutions.

    Args:
        data (np.ndarray): 2-D array of solutions, with each row being a single solution.

    Returns:
        np.ndarray: Boolean array of same length as number of solutions (rows). The value is
            true if corresponding solution is non-dominated. False otherwise
    """
    num_solutions = len(data)
    index = np.zeros(num_solutions, dtype=np.bool_)
    index[0] = True
    for i in range(1, num_solutions):
        index[i] = True
        for j in range(i):
            if not index[j]:
                continue
            if dominates(data[i], data[j]):
                index[j] = False
            elif dominates(data[j], data[i]):
                index[i] = False
                break
    return index


@njit()
def fast_non_dominated_sort(data: np.ndarray) -> np.ndarray:
    """Conduct fast non-dominated sorting on a population of solutions.

    Args:
        data (np.ndarray): 2-D array of solutions, with each row being a single solution.

    Returns:
        np.ndarray: n x f boolean array. n is the number of solutions, f is the number of fronts.
            The value of an array element is true if the corresponding solution id (column) belongs in
            the corresponding front (row).
    """
    num_solutions = len(data)
    indices = np.arange(num_solutions)
    taken = np.zeros(num_solutions, dtype=np.bool_)
    fronts = np.zeros((num_solutions, num_solutions), dtype=np.bool_)

    for i in indices:
        current_front = non_dominated(data[~taken])

        current_front_all = np.zeros(num_solutions, dtype=np.bool_)
        current_front_all[~taken] = current_front
        fronts[i] = current_front_all

        taken = taken + fronts[i]
        if taken.all():
            # if all the solutions have been sorted, stop
            break

    return fronts[: i + 1]


def fast_non_dominated_sort_indices(data: np.ndarray) -> list[np.ndarray]:
    """Conduct fast non-dominated sorting on a population of solutions.

    This function returns identical results as `fast_non_dominated_sort`, but in a different format.
    This function returns an array of solution indices for each front, packed in a list.

    Args:
        data (np.ndarray): 2-D array of solutions, with each row being a single solution.

    Returns:
        list[np.ndarray]: A list with f elements where f is the number of fronts in the data,
            arranged in ascending order. Each element is a numpy array of the indices of solutions
            belonging to the corresponding front.
    """
    fronts = fast_non_dominated_sort(data)
    return [np.where(fronts[i])[0] for i in range(len(fronts))]


@njit()
def non_dominated_merge(set1: np.ndarray, set2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Merge two sets of non-dominated solutions.

    This is a slightly more efficient way to merge two sets of solutions such that the resulting
    set only contains non-dominated solutions from the two sets. This function assumes that the
    two sets already only contain non-dominated solutions. I.e., each solution in each set is non-dominated
    with respect to all other solutions in the same set. However, the solutions in the two sets may not be
    non-dominated with respect to each other.

    Args:
        set1 (np.ndarray): 2-D array of solutions, with each row being a single solution.
        set2 (np.ndarray): 2-D array of solutions, with each row being a single solution.

    Returns:
        tuple[np.ndarray, np.ndarray]: A tuple of two mask arrays. The first mask array is for set1 and the
            second mask array is for set2. The value of an element in the mask array is True if the corresponding
            solution is non-dominated in the merged set. False otherwise.
    """
    # Masks to keep track of which solutions are non-dominated. Default is all True.
    set1_mask = np.ones(len(set1), dtype=np.bool_)
    set2_mask = np.ones(len(set2), dtype=np.bool_)

    for i in range(len(set1)):
        for j in range(len(set2)):
            if dominates(set1[i], set2[j]):
                set2_mask[j] = False
            elif dominates(set2[j], set1[i]):
                set1_mask[i] = False

    return set1_mask, set2_mask
