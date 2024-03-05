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
        if not fronts[i].any():
            break
    return fronts[:i]


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
