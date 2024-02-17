"""Functions related to the NAUTILUS Navigator method are defined here.

Reference of the method:

Ruiz, Ana B., et al. "NAUTILUS Navigator: free search interactive multiobjective
optimization without trading-off." Journal of Global Optimization 74.2 (2019):
213-231.
"""
import numpy as np

from desdeo.problem import Problem
from desdeo.tools.generics import SolverResults
from desdeo.tools.scalarization import (
    create_asf,
    create_epsilon_constraints,
    add_scalarization_function,
    add_lte_constraints,
)
from desdeo.tools.scipy_solver_interfaces import create_scipy_de_solver
from desdeo.problem import objective_dict_to_numpy_array, numpy_array_to_objective_dict


class NautilusNavigatorError(Exception):
    """Raised when an exception is encountered with procedures related to NAUTILUS Navigator."""


def calculate_navigation_point(
    problem: Problem,
    previous_navigation_point: dict[str, float],
    reachable_objective_vector: dict[str, float],
    number_of_steps_remaining: int,
) -> dict[str, float]:
    """Calculates the navigation point.

    The navigation point based on the previous navigation
    point, number of navigation steps remaining, and the reachable objective
    vector from the new navigation point.

    Args:
        problem (Problem): the problem being solved.
        previous_navigation_point (dict[str, float]): the previous navigation point.
        reachable_objective_vector (dict[str, float]): the current reachable objective vector from the navigation point.
        number_of_steps_remaining (int): the number of steps remaining in the navigation. Must be greater than 0.

    Raises:
        NautilusNavigatorError: when the given number of steps remaining is less than 0.

    Returns:
        list[float]: the navigation point.
    """
    if number_of_steps_remaining <= 0:
        msg = f"The given number of steps remaining ({number_of_steps_remaining=}) must be greater than 0."
        raise NautilusNavigatorError(msg)

    z_prev = objective_dict_to_numpy_array(problem, previous_navigation_point)
    f = objective_dict_to_numpy_array(problem, reachable_objective_vector)
    rs = number_of_steps_remaining

    # return the new navigation point
    z = ((rs - 1) / (rs)) * z_prev + f / rs

    return numpy_array_to_objective_dict(problem, z)


def calculate_reachable_bounds(
    problem: Problem, navigation_point: dict[str, float]
) -> tuple[dict[str, float], dict[str, float]]:
    """Computes the current reachable (upper and lower) bounds of the solutions in the objective space.

    The reachable bound are computed based on the current navigation point. The bounds are computed by
    solving an epsilon constraint problem.

    Args:
        problem (Problem): the problem being solved.
        navigation_point (dict[str, float]): the navigation point limiting the
            reachable area. The key is the objective function's symbol and the value
            the navigation point.

    Raises:
        NautilusNavigationError: when optimization of an epsilon constraint problem is not successful.

    Returns:
        tuple[dict[str, float], dict[str, float]]: a tuple of dicts, where the first dict are the lower bounds and the
            second element the upper bounds, the key is the symbol of each objective.
    """
    # If an objective is to be maximized, then the navigation point component of that objective should be
    # multiplied by -1.
    const_bounds = {
        objective.symbol: -1 * navigation_point[objective.symbol]
        if objective.maximize
        else navigation_point[objective.symbol]
        for objective in problem.objectives
    }

    lower_bounds = {}
    upper_bounds = {}
    for objective in problem.objectives:
        # symbols to identify the objectives to be constrained
        target_expr, const_exprs = create_epsilon_constraints(
            problem, objective_symbol=objective.symbol, epsilons=const_bounds
        )

        # solve lower bounds
        # add scalarization
        eps_problem, target = add_scalarization_function(problem, target_expr, "target")

        # add constraints
        eps_problem = add_lte_constraints(
            eps_problem, const_exprs, [f"eps_{i}" for i in range(1, len(const_exprs) + 1)]
        )

        # solve
        solver = create_scipy_de_solver(eps_problem)
        res = solver(target)

        if not res.success:
            # could not optimize eps problem
            msg = (
                f"Optimizing the epsilon constrait problem for the objective "
                f"{objective.symbol} was not successful. Reason: {res.message}"
            )
            raise NautilusNavigatorError(msg)

        lower_bound = res.optimal_objectives[objective.symbol][0]

        # solver upper bounds
        # the lower bounds is set as in the NAUTILUS method, e.g., taken from
        # the current itration/navigation point
        upper_bound = navigation_point[objective.symbol]

        # add the lower and upper bounds logically depending whether an objective is to be maximized or minimized
        lower_bounds[objective.symbol] = lower_bound if not objective.maximize else upper_bound
        upper_bounds[objective.symbol] = upper_bound if not objective.maximize else lower_bound

    return lower_bounds, upper_bounds


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
    # create and add scalarization function
    sf = create_asf(problem, reference_point, reference_in_aug=True)
    problem_w_asf, target = add_scalarization_function(problem, sf, "asf")

    # solve the problem
    solver = create_scipy_de_solver(problem_w_asf)
    return solver(target)


def calculate_distance_to_front(
    problem: Problem, navigation_point: dict[str, float], reachable_objective_vector: dict[str, float]
) -> float:
    """Calculates the distance to the Pareto optimal front from a navigation point.

    It is assumed that a nadir point is defined for the problem.

    Args:
        problem (Problem): the problem being solved.
        navigation_point (dict[str, float]): the current navigation point.
        reachable_objective_vector (dict[str, float]): the current reachable objective vector from the navigation point.

    Raises:
        NautilusNavigatorError: all or some of the components of the problem's nadir point
            are not defined.

    Returns:
        float: the distance to the front.
    """
    nadir_point = objective_dict_to_numpy_array(
        problem, {objective.symbol: objective.nadir for objective in problem.objectives}
    )
    if None in nadir_point:
        msg = (
            f"Some or all the nadir values for the given problem are 'None': {nadir_point}. "
            "The nadir point must be fully defined."
        )
        raise NautilusNavigatorError(msg)

    z_nav = objective_dict_to_numpy_array(problem, navigation_point)
    f = objective_dict_to_numpy_array(problem, reachable_objective_vector)

    return (np.linalg.norm(z_nav - nadir_point) / np.linalg.norm(f - nadir_point)) * 100
