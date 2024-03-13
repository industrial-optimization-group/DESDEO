"""Functions related to the NAUTILUS 1/2 method are defined here.

Reference of the method:

TODO: update
"""

import numpy as np
from pydantic import BaseModel, Field

from desdeo.mcdm.nautilus_navigator import (
    calculate_distance_to_front,
    calculate_navigation_point,
)
from desdeo.mcdm.nautili import (
    solve_reachable_bounds
)
from desdeo.problem import (
    Problem,
    get_nadir_dict,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
)
from desdeo.tools.generics import CreateSolverType, SolverResults
from desdeo.tools.scalarization import (
    add_lte_constraints,
    add_scalarization_function,
    create_asf,
    create_asf_generic,
    create_epsilon_constraints_json,
)
from desdeo.tools.utils import guess_best_solver


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
    preference: dict | None = Field(description="The preference used in the step. For now assumed that it is a reference point")
    #preference_method: dict | None = Field(description="The preference method used in the step.")
    #improvement_direction: dict | None = Field(description="The improvement direction.")
    navigation_point: dict = Field(description="The navigation point used in the step.")
    reachable_solution: dict | None = Field(description="The reachable solution found in the step.")
    reachable_bounds: dict = Field(description="The reachable bounds found in the step.")


class NautilusError(Exception):
    """Raised when an exception is encountered with procedures related to NAUTILUS."""



def solve_reachable_solution(
    problem: Problem,
    preference: dict[str, float],
    #improvement_direction: dict[str, float],
    previous_nav_point: dict[str, float],
    create_solver: CreateSolverType | None = None,
) -> SolverResults:
    """Calculates the reachable solution on the Pareto optimal front.

    For the calculation to make sense in the context of NAUTILUS, the reference point
    should be bounded by the reachable bounds present at the navigation step the
    reference point has been given.

    In practice, the reachable solution is calculated by solving an achievement
    scalarizing function.

    Args:
        problem (Problem): the problem being solved.
        preference (dict[str, float]): the reference point to project on the Pareto optimal front.
        previous_nav_point (dict[str, float]): the previous navigation point. The reachable solution found
            is always better than the previous navigation point.
        create_solver (CreateSolverType | None, optional): a function of type CreateSolverType that returns a solver.
            If None, then a solver is utilized bases on the problem's properties. Defaults to None.
        bounds (dict[str, float] | None, optional): the bounds of the problem. Defaults to None.

    Returns:
        SolverResults: the results of the projection.
    """
    # check solver
    _create_solver = guess_best_solver(problem) if create_solver is None else create_solver

    # need to convert the preferences to preferential factors?

    # create and add scalarization function
    sf = create_asf(problem, preference, reference_in_aug=True)
    problem_w_asf, target = add_scalarization_function(problem, sf, "asf")

    # Note: We do not solve the global problem. Instead, we solve this constrained problem:
    const_exprs = [
        f"{obj.symbol}_min - {previous_nav_point[obj.symbol] * (-1 if obj.maximize else 1)}"
        for obj in problem.objectives
    ]
    problem_w_asf = add_lte_constraints(
        problem_w_asf, const_exprs, [f"const_{i}" for i in range(1, len(const_exprs) + 1)]
    )

    # solve the problem
    solver = _create_solver(problem_w_asf)
    return solver(target)


# NAUTILUS initializer and steppers

def nautilus_init(problem: Problem, create_solver: CreateSolverType | None = None) -> NAUTILUS_Response:
    """Initializes the NAUTILUS method.

    Creates the initial response of the method, which sets the navigation point to the nadir point
    and the reachable bounds to the ideal and nadir points.

    Args:
        problem (Problem): The problem to be solved.
        create_solver (CreateSolverType | None, optional): The solver to use. Defaults to ???.

    Returns:
        NAUTILUS_Response: The initial response of the method.
    """
    nav_point = get_nadir_dict(problem)
    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point, create_solver=create_solver)
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
    create_solver: CreateSolverType | None = None,
    preference: dict | None = None,
    reachable_solution: dict | None = None,
) -> NAUTILUS_Response:
    """Performs a step of the NAUTILUS method.

    Args:
        problem (Problem): The problem to be solved.
        steps_remaining (int): The number of steps remaining.
        step_number (int): The current step number. Just used for the response.
        nav_point (dict): The current navigation point.
        create_solver (CreateSolverType | None, optional): The solver to use. Defaults to None.
        preference (dict | None, optional): The reference point provided by the DM. Defaults to None, in which
        case it is assumed that the DM has not changed their preference. The algorithm uses the last reachable solution,
        which must be provided in this case.
        bounds (dict | None, optional): The bounds of the problem provided by the DM. Defaults to None.
        reachable_solution (dict | None, optional): The previous reachable solution. Must only be provided if the DM
        has not changed their preference. Defaults to None.

    Raises:
        NautilusError: If neither preference nor reachable_solution is provided.
        NautilusError: If both preference and reachable_solution are provided.

    Returns:
        NAUTILUS_Response: The response of the method after the step.
    """
    if preference is None and reachable_solution is None:
        raise NautilusError("Either preference or reachable_solution must be provided.")

    if preference is not None and reachable_solution is not None:
        raise NautilusError("Only one of preference or reachable_solution should be provided.")

    if preference is not None:
        opt_result = solve_reachable_solution(problem, preference, nav_point, create_solver)
        reachable_point = opt_result.optimal_objectives
    else:
        reachable_point = reachable_solution

    # update nav point
    new_nav_point = calculate_navigation_point(problem, nav_point, reachable_point, steps_remaining)

    # update_bounds
    lower_bounds, upper_bounds = solve_reachable_bounds(
        problem, new_nav_point, create_solver=create_solver,
    )

    distance = calculate_distance_to_front(problem, new_nav_point, reachable_point)

    return NAUTILUS_Response(
        step_number=step_number,
        distance_to_front=distance,
        navigation_point=new_nav_point,
        reachable_solution=reachable_point,
        preference=preference,
        reachable_bounds={"lower_bounds": lower_bounds, "upper_bounds": upper_bounds},
    )


def nautilus_all_steps(
    problem: Problem,
    steps_remaining: int,
    preference: dict,
    previous_responses: list[NAUTILUS_Response],
    create_solver: CreateSolverType | None = None,
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
        create_solver (CreateSolverType | None, optional): The solver to use. Defaults to None, in which case the
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
                create_solver=create_solver,
            )
            first_iteration = False
        else:
            response = nautilus_step(
                problem,
                steps_remaining=steps_remaining,
                step_number=step_number,
                nav_point=nav_point,
                reachable_solution=reachable_solution,
                create_solver=create_solver,
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
    """ TODO: implement """
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


if __name__ == "__main__":
    from desdeo.problem import binh_and_korn, get_ideal_dict

    problem = binh_and_korn()

    # initialization
    nav_point = get_nadir_dict(problem)
    lower_bounds = get_ideal_dict(problem)
    upper_bounds = get_nadir_dict(problem)

    step = 1
    steps_remaining = 100

    # get reference point
    preference = {"f_1": 100.0, "f_2": 8.0}

    # get ranking       
    #  "preference_method": 1,
    # "preference_info": np.array([2, 2, 1, 1]),
    #preference = {"f_1": 100.0, "f_2": 8.0}

    # calculate reachable solution (direction)
    opt_result = solve_reachable_solution(problem, preference, nav_point)

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

    # no new reference point, reachable point (direction) stays the same
    # update nav point
    nav_point = calculate_navigation_point(problem, nav_point, reachable_point, steps_remaining)
    print(f"{nav_point=}")

    # update bounds
    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    distance = calculate_distance_to_front(problem, nav_point, reachable_point)

    step += 1
    steps_remaining -= 1

    # new reference point
    preference = {"f_1": 80.0, "f_2": 9.0}

    # calculate reachable solution (direction)
    opt_result = solve_reachable_solution(problem, preference, nav_point)

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
