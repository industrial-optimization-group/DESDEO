"""Functions related to the NAUTILUS 1/2 method are defined here.

Reference of the method:

TODO: update
"""

import numpy as np
from pydantic import BaseModel, Field

from desdeo.mcdm.nautili import solve_reachable_bounds
from desdeo.mcdm.nautilus_navigator import (
    calculate_distance_to_front,
    calculate_navigation_point,
)
from desdeo.problem import (
    Problem,
    get_nadir_dict,
    get_ideal_dict,
)
from desdeo.tools.generics import BaseSolver, SolverResults
from desdeo.tools.scalarization import (  # create_asf, should be add_asf_nondiff probably
    add_lte_constraints,
    add_asf_generic_diff,
    add_asf_generic_nondiff,
)
from desdeo.tools.utils import guess_best_solver
from warnings import warn


# TODO: check if need all of these, eg. distance to front? and do I need to change some of them?
class NAUTILUS_Response(BaseModel):  # NOQA: N801
    """The response of the NAUTILUS method."""

    step_number: int = Field(description="The step number associted with this response.")
    distance_to_front: float = Field(
        description=(
            "The distance travelled to the Pareto front. "
            "The distance is a ratio of the distances between the nadir and navigation point, and "
            "the nadir and the reachable objective vector. The distance is given in percentage."
        )
    )
    preference: dict | None = Field(
        description="The preference used in the step. For now assumed that it is a reference point"
    )
    # preference_method: dict | None = Field(description="The preference method used in the step.")
    # improvement_direction: dict | None = Field(description="The improvement direction.")
    navigation_point: dict = Field(description="The navigation point used in the step.")
    reachable_solution: dict | None = Field(description="The reachable solution found in the step.")
    reachable_bounds: dict = Field(description="The reachable bounds found in the step.")


class NautilusError(Exception):
    """Raised when an exception is encountered with procedures related to NAUTILUS."""


def solve_reachable_solution(
    problem: Problem,
    weights: dict[str, float],
    # improvement_direction: dict[str, float],
    previous_nav_point: dict[str, float],
    solver: BaseSolver | None = None,
) -> SolverResults:
    """Calculates the reachable solution on the Pareto optimal front.

    For the calculation to make sense in the context of NAUTILUS, the reference point
    should be bounded by the reachable bounds present at the navigation step the
    reference point has been given.

    In practice, the reachable solution is calculated by solving an achievement
    scalarizing function.

    Args:
        problem (Problem): the problem being solved.
        preference (dict[str, float]): the weights defining the direction of improvement. Must be calculated
            from the preference provided by the DM (weights, ranks, or reference point).
        previous_nav_point (dict[str, float]): the previous navigation point. The reachable solution found
            is always better than the previous navigation point.
        solver (BaseSolver | None, optional): solver to solve the problem.
            If None, then a solver is utilized bases on the problem's properties. Defaults to None.
        bounds (dict[str, float] | None, optional): the bounds of the problem. Defaults to None.

    Returns:
        SolverResults: the results of the projection.
    """
    # check solver
    init_solver = guess_best_solver(problem) if solver is None else solver

    # need to convert the preferences to preferential factors?

    # create and add scalarization function
    if problem.is_twice_differentiable:
        # differentiable problem
        problem_w_asf, target = add_asf_generic_diff(
            problem,
            symbol="asf",
            reference_point=previous_nav_point,
            weights=weights,
            reference_in_aug=True,
        )
    else:
        # non-differentiable problem
        problem_w_asf, target = add_asf_generic_nondiff(
            problem,
            symbol="asf",
            reference_point=previous_nav_point,
            weights=weights,
            reference_in_aug=True,
        )

    # Note: We do not solve the global problem. Instead, we solve this constrained problem:
    const_exprs = [
        f"{obj.symbol}_min - {previous_nav_point[obj.symbol] * (-1 if obj.maximize else 1)}"
        for obj in problem.objectives
    ]
    problem_w_asf = add_lte_constraints(
        problem_w_asf, const_exprs, [f"const_{i}" for i in range(1, len(const_exprs) + 1)]
    )

    # solve the problem
    solver = init_solver(problem_w_asf)
    return solver.solve(target)


# NAUTILUS initializer and steppers


def nautilus_init(problem: Problem, solver: BaseSolver | None = None) -> NAUTILUS_Response:
    """Initializes the NAUTILUS method.

    Creates the initial response of the method, which sets the navigation point to the nadir point
    and the reachable bounds to the ideal and nadir points.

    Args:
        problem (Problem): The problem to be solved.
        solver (BaseSolver | None, optional): The solver to use. Defaults to None.

    Returns:
        NAUTILUS_Response: The initial response of the method.
    """
    nav_point = get_nadir_dict(problem)
    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point, solver=solver)
    return NAUTILUS_Response(
        distance_to_front=0,
        navigation_point=nav_point,
        reachable_bounds={"lower_bounds": lower_bounds, "upper_bounds": upper_bounds},
        reachable_solution=None,
        preference=None,
        step_number=0,
    )


def nautilus_step(  # NOQA: PLR0913
    problem: Problem,
    steps_remaining: int,
    step_number: int,
    nav_point: dict,
    solver: BaseSolver | None = None,
    points: dict[str, float] | None = None,
    ranks: dict[str, int] | None = None,
) -> NAUTILUS_Response:
    """Performs a step of the NAUTILUS method.

    Args:
        problem (Problem): The problem to be solved.
        steps_remaining (int): The number of steps remaining.
        step_number (int): The current step number. Just used for the response.
        nav_point (dict): The current navigation point.
        solver (BaseSolver | None, optional): The solver to use. Defaults to None.
        points (dict[str, float] | None, optional): The points of the objectives. Defaults to None.
        ranks (dict[str, int] | None, optional): The ranks of the objectives. Defaults to None.

    Raises:
        NautilusError: If neither preference nor reachable_solution is provided.
        NautilusError: If both preference and reachable_solution are provided.

    Returns:
        NAUTILUS_Response: The response of the method after the step.
    """
    if points is None and ranks is None:
        raise NautilusError("Either points or ranks must be provided.")
    if points is not None and ranks is not None:
        raise NautilusError("Both points and ranks cannot be provided.")

    # get weights
    if points is not None:  # noqa: SIM108
        weights = points_to_weights(points, problem)
    else:
        weights = ranks_to_weights(ranks, problem)

    # calculate reachable solution (direction).
    # This is inefficient as it is recalculated even if preferences do not change.
    opt_result = solve_reachable_solution(problem, weights, nav_point, solver)

    if not opt_result.success:
        warn(message="The solver did not converge.", stacklevel=2)

    reachable_point = opt_result.optimal_objectives

    # update nav point
    new_nav_point = calculate_navigation_point(problem, nav_point, reachable_point, steps_remaining)

    # update_bounds
    lower_bounds, upper_bounds = solve_reachable_bounds(problem, new_nav_point, solver)

    distance = calculate_distance_to_front(problem, new_nav_point, reachable_point)

    return NAUTILUS_Response(
        step_number=step_number,
        distance_to_front=distance,
        navigation_point=new_nav_point,
        reachable_solution=reachable_point,
        preference=ranks if ranks is not None else points,
        reachable_bounds={"lower_bounds": lower_bounds, "upper_bounds": upper_bounds},
    )


def __nautilus_all_steps(
    problem: Problem,
    steps_remaining: int,
    preference: dict,
    previous_responses: list[NAUTILUS_Response],
    solver: BaseSolver | None = None,
):
    """Performs all steps of the NAUTILUS method.

    NAUTILUS needs to be initialized before calling this function. Once initialized, this function performs all
    steps of the method. However, this method need not start from the beginning. The method conducts "steps_remaining"
    number of steps from the last navigation point. The last navigation point is taken from the last response in
    "previous_responses" list. The first step in this algorithm always involves recalculating the reachable solution.
    All subsequest steps are precalculated without recalculating the reachable solution, with the assumption that the
    reference point has not changed. It is up to the user to only show the steps that the DM thinks they have taken.

    Args:
        problem (Problem): The problem to be solved.
        steps_remaining (int): The number of steps remaining.
        preference (dict): The reference point provided by the DM.
        bounds (dict): The bounds of the problem provided by the DM.
        previous_responses (list[NAUTILUS_Response]): The previous responses of the method.
        solver (BaseSolver | None, optional): The solver to use. Defaults to None, in which case the
            algorithm will guess the best solver for the problem.

    Returns:
        list[NAUTILUS_Response]: The new responses of the method after all steps. Note, as only new responses are
            returned, the length of the list is equal to "steps_remaining". The analyst should append these responses
            to the "previous_responses" list to keep track of the entire process.
    """
    responses: list[NAUTILUS_Response] = []
    nav_point = previous_responses[-1].navigation_point
    step_number = previous_responses[-1].step_number + 1
    first_iteration = True
    reachable_solution = dict
    while steps_remaining > 0:
        if first_iteration:
            response = nautilus_step(
                problem,
                steps_remaining=steps_remaining,
                step_number=step_number,
                nav_point=nav_point,
                preference=preference,
                solver=solver,
            )
            first_iteration = False
        else:
            response = nautilus_step(
                problem,
                steps_remaining=steps_remaining,
                step_number=step_number,
                nav_point=nav_point,
                reachable_solution=reachable_solution,
                solver=solver,
            )
        response.preference = preference
        responses.append(response)
        reachable_solution = response.reachable_solution
        nav_point = response.navigation_point
        steps_remaining -= 1
        step_number += 1
    return responses


# implement preferential factors for other preference types
def calculate_preferential_factors():
    """TODO: implement"""
    pass


def step_back_index(responses: list[NAUTILUS_Response], step_number: int) -> int:
    """Find the index of the response with the given step number.

    Note, multiple responses can have the same step
    number. This may happen if the DM takes a step back. In this case, the latest response with the given step number
    is returned. Note, as we precalculate all the responses, it is up to the analyst to show the steps that the DM
    thinks they have taken. Without this, the DM may be confused. In the worst case, the DM may take a step "back to
    the future".

    Args:
        responses (list[NAUTILUS_Response]): Responses returned by the NAUTILUS method.
        step_number (int): The step number to go back to.

    Returns:
        int : The index of the response with the given step number.
    """
    relevant_indices = [i for i, response in enumerate(responses) if response.step_number == step_number]
    # Choose latest index
    return relevant_indices[-1]


def get_current_path(all_responses: list[NAUTILUS_Response]) -> list[int]:
    """Get the path of the current responses.

    All responses may contain steps that the DM has gone back on. This function returns the path of the current active
    path being followed by the DM. The path is a list of indices of the responses in the "all_responses" list. Note that
    the path includes all steps until reaching the Pareto front (or whatever the last response is). It is up to the
    analyst/GUI to only show the steps that the DM has taken.

    Args:
        all_responses (list[NAUTILUS_Response]): All responses returned by the NAUTILUS method.

    Returns:
        list[int]: The path of the current active responses.
    """
    total_steps = all_responses[-1].step_number
    current_index = len(all_responses) - 1
    path: list[int] = [current_index]
    total_steps -= 1

    while total_steps >= 0:
        found_step = False
        while not found_step:
            current_index -= 1
            if all_responses[current_index].step_number == total_steps:
                path.append(current_index)
                found_step = True
        total_steps -= 1
    return list(reversed(path))


def ranks_to_weights(ranks: dict[str, int], problem: Problem) -> dict[str, float]:
    """Convert ranks to weights.

    The ranks are converted to weights using the following formula:
    weight = rank * (nadir - utopian). Note that this means that a lower rank is worse.

    Args:
        ranks (dict[str, int]): The ranks of the objectives.
        problem (Problem): The problem being solved.

    Returns:
        dict[str, float]: The weights calculated from the ranks.
    """
    nadir = get_nadir_dict(problem)
    ideal = get_ideal_dict(problem)
    tol = 1e-10
    weights = {}
    for key, rank in ranks.items():
        max_mult = [obj.maximize for obj in problem.objectives if obj.symbol == key][0]
        max_mult = -1 if max_mult else 1
        weights[key] = rank * (nadir[key] * max_mult - ideal[key] * max_mult + tol)
    return weights


def points_to_weights(points: dict[str, float], problem: Problem) -> dict[str, float]:
    """Convert points to weights.

    The points are converted to weights using the following formula:
    weight = point * (nadir - utopian).

    Args:
        points (dict[str, float]): The points of the objectives.
        problem (Problem): The problem being solved.

    Returns:
        dict[str, float]: The weights calculated from the points.
    """
    nadir = get_nadir_dict(problem)
    ideal = get_ideal_dict(problem)
    tol = 1e-6
    weights = {}
    check_sum = 0
    for key, point in points.items():
        max_mult = [obj.maximize for obj in problem.objectives if obj.symbol == key][0]
        max_mult = -1 if max_mult else 1
        weights[key] = point / 100 * (nadir[key] * max_mult - ideal[key] * max_mult + tol)
        check_sum += point
    if check_sum != 100:
        raise ValueError(f"The sum of the points must be 100. The sum is {check_sum}.")
    return weights


if __name__ == "__main__":
    from desdeo.problem import binh_and_korn

    problem = binh_and_korn()

    # initialization
    nav_point = get_nadir_dict(problem)
    lower_bounds = get_ideal_dict(problem)
    upper_bounds = get_nadir_dict(problem)

    step = 1
    steps_remaining = 100

    # get reference point
    ranks = {"f_1": 1, "f_2": 2}
    weights = ranks_to_weights(ranks, problem)

    # get ranking
    #  "preference_method": 1,
    # "preference_info": np.array([2, 2, 1, 1]),
    # preference = {"f_1": 100.0, "f_2": 8.0}

    # calculate reachable solution (direction)
    opt_result = solve_reachable_solution(problem, weights, nav_point)

    assert opt_result.success

    reachable_point = opt_result.optimal_objectives

    # update nav point
    nav_point = calculate_navigation_point(problem, nav_point, reachable_point, steps_remaining)
    print(f"{nav_point=}")

    # update_bounds
    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    distance = calculate_distance_to_front(problem, nav_point, reachable_point)

    step += 1
    steps_remaining -= 1

    # no new preference, reachable point (direction) stays the same
    # update nav point
    nav_point = calculate_navigation_point(problem, nav_point, reachable_point, steps_remaining)
    print(f"{nav_point=}")

    # update bounds
    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    distance = calculate_distance_to_front(problem, nav_point, reachable_point)

    step += 1
    steps_remaining -= 1

    # new reference point
    points = {"f_1": 80, "f_2": 20}  # Now f_1 is more important
    weights = points_to_weights(points, problem)

    # calculate reachable solution (direction)
    opt_result = solve_reachable_solution(problem, weights, nav_point)

    assert opt_result.success

    reachable_point = opt_result.optimal_objectives

    # update nav point
    nav_point = calculate_navigation_point(problem, nav_point, reachable_point, steps_remaining)
    print(f"{nav_point=}")

    # update_bounds
    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    distance = calculate_distance_to_front(problem, nav_point, reachable_point)

    step += 1
    steps_remaining -= 1

    # etc...
