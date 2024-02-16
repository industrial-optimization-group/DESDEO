"""Functions related to the NAUTILUS Navigator method are defined here.

Reference of the method:

Ruiz, Ana B., et al. "NAUTILUS Navigator: free search interactive multiobjective
optimization without trading-off." Journal of Global Optimization 74.2 (2019):
213-231.
"""
import numpy as np

from desdeo.problem import Problem
from desdeo.tools.generics import SolverResults


class NautilusNavigatorError(Exception):
    """Raised when an exception is encountered with procedures related to NAUTILUS Navigator."""


def calculate_navigation_point(
    previous_navigation_point: list[float], reachable_objective_vector: list[float], number_of_steps_remaining: int
) -> list[float]:
    """Calculates the navigation point.

    The navigation point based on the previous navigation
    point, number of navigation steps remaining, and the reachable objective
    vector from the new navigation point.

    Args:
        previous_navigation_point (list[float]): the previous navigation point.
        reachable_objective_vector (list[float]): the current reachable objective vector from the navigation point.
        number_of_steps_remaining (int): the number of steps remaining in the navigation. Must be greater than 0.

    Raises:
        NautilusNavigatorError: when the given number of steps remaining is less than 0.

    Returns:
        list[float]: the navigation point.
    """
    if number_of_steps_remaining <= 0:
        msg = f"The given number of steps remaining ({number_of_steps_remaining=}) must be greater than 0."
        raise NautilusNavigatorError(msg)

    z_prev = np.array(previous_navigation_point)
    f = np.array(reachable_objective_vector)
    rs = number_of_steps_remaining

    # return the new navigation point
    z = ((rs - 1) / (rs)) * z_prev + f / rs

    return z.tolist()


def calculate_reachable_bounds(problem: Problem, navigation_point: list[float]) -> tuple[list[float], list[float]]:
    """Computes the current reachable (upper and lower) bounds of the solutions in the objective space.

    The reachable bound are computed based on the current navigation point. The bounds are computed by
    solving an epsilon constraint problem.

    Args:
        problem (Problem): the problem being solved.
        navigation_point (list[float]): the navigation point limiting the reachable area.

    Returns:
        tuple[list[float], list[float]]: a tuple, where the first element are the lower bounds and the
            second element the upper bounds.
    """


def calculate_reachable_solution(problem: Problem, reference_point: list[float]) -> SolverResults:
    """Calculates the reachable solution on the Pareto optimal front.

    For the calculation to make sense in the context of NAUTILUS Navigator, the reference point
    should be bounded by the reachable bounds present at the navigation step the
    reference point has been given.

    In practice, the reachable solution is calculated by solving an achievement
    scalarizing function.

    Args:
        problem (Problem): the problem being solved.
        reference_point (list[float]): the reference point to project on the Pareto optimal front.

    Returns:
        SolverResults: the results of the projection.
    """


def calculate_distance_to_front(
    navigation_point: list[float], reachable_objective_vector: list[float], nadir_point: list[float]
) -> float:
    """Calculates the distance to the Pareto optimal front from a navigation point.

    Args:
        navigation_point (list[float]): the current navigation point.
        reachable_objective_vector (list[float]): the current reachable objective vector from the navigation point.
        nadir_point (list[float]): the nadir point of the front.

    Returns:
        float: the distance to the front.
    """
