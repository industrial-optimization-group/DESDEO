"""Methods for the NAUTILI (a group decision making variant for NAUTILUS) method."""

import numpy as np
from pydantic import BaseModel, Field

from desdeo.mcdm.nautilus_navigator import (
    calculate_distance_to_front,
    calculate_navigation_point,
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
    add_asf_generic_nondiff,
    add_epsilon_constraints,
)
from desdeo.tools.utils import guess_best_solver


class NAUTILI_Response(BaseModel):
    """The response of the NAUTILI method."""

    step_number: int = Field(description="The step number associted with this response.")
    distance_to_front: float = Field(
        description=(
            "The distance travelled to the Pareto front. "
            "The distance is a ratio of the distances between the nadir and navigation point, and "
            "the nadir and the reachable objective vector. The distance is given in percentage."
        )
    )
    reference_points: dict | None = Field(description="The reference point used in the step.")
    improvement_directions: dict | None = Field(description="The improvement directions for each DM.")
    group_improvement_direction: dict | None = Field(description="The group improvement direction.")
    navigation_point: dict = Field(description="The navigation point used in the step.")
    reachable_solution: dict | None = Field(description="The reachable solution found in the step.")
    reachable_bounds: dict = Field(description="The reachable bounds found in the step.")


class NautiliError(Exception):
    """Exception raised for errors in the NAUTILI method."""


def solve_reachable_bounds(
    problem: Problem, navigation_point: dict[str, float], create_solver: CreateSolverType | None = None
) -> tuple[dict[str, float], dict[str, float]]:
    """Computes the current reachable (upper and lower) bounds of the solutions in the objective space.

    The reachable bound are computed based on the current navigation point. The bounds are computed by
    solving an epsilon constraint problem.

    Args:
        problem (Problem): the problem being solved.
        navigation_point (dict[str, float]): the navigation point limiting the
            reachable area. The key is the objective function's symbol and the value
            the navigation point.
        create_solver (CreateSolverType | None, optional): a function of type CreateSolverType that returns a solver.
            If None, then a solver is utilized bases on the problem's properties. Defaults to None.

    Raises:
        NautiliError: when optimization of an epsilon constraint problem is not successful.

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

    # if a solver creator was provided, use that, else, guess the best one
    _create_solver = guess_best_solver(problem) if create_solver is None else create_solver

    lower_bounds = {}
    upper_bounds = {}
    for objective in problem.objectives:
        eps_problem, target, _ = add_epsilon_constraints(
            problem,
            "target",
            {f"{obj.symbol}": f"{obj.symbol}_eps" for obj in problem.objectives},
            objective.symbol,
            const_bounds,
        )

        # solve
        solver = _create_solver(eps_problem)
        res = solver(target)

        if not res.success:
            # could not optimize eps problem
            msg = (
                f"Optimizing the epsilon constrait problem for the objective "
                f"{objective.symbol} was not successful. Reason: {res.message}"
            )
            raise NautiliError(msg)

        lower_bound = res.optimal_objectives[objective.symbol]

        if isinstance(lower_bound, list):
            lower_bound = lower_bound[0]

        # solver upper bounds
        # the lower bounds is set as in the NAUTILUS method, e.g., taken from
        # the current iteration/navigation point
        if isinstance(navigation_point[objective.symbol], list):
            # It should never be a list accordint to the type hints
            upper_bound = navigation_point[objective.symbol][0]
        else:
            upper_bound = navigation_point[objective.symbol]

        # add the lower and upper bounds logically depending whether an objective is to be maximized or minimized
        lower_bounds[objective.symbol] = lower_bound if not objective.maximize else upper_bound
        upper_bounds[objective.symbol] = upper_bound if not objective.maximize else lower_bound

    return lower_bounds, upper_bounds


def solve_reachable_solution(
    problem: Problem,
    group_improvement_direction: dict[str, float],
    previous_nav_point: dict[str, float],
    create_solver: CreateSolverType | None = None,
) -> SolverResults:
    """Calculates the reachable solution on the Pareto optimal front.

    For the calculation to make sense in the context of NAUTILI, the reference point
    should be bounded by the reachable bounds present at the navigation step the
    reference point has been given.

    In practice, the reachable solution is calculated by solving an achievement
    scalarizing function.

    Args:
        problem (Problem): the problem being solved.
        group_improvement_direction (dict[str, float]): the improvement direction for the group.
        previous_nav_point (dict[str, float]): the previous navigation point. The reachable solution found
            is always better than the previous navigation point.
        create_solver (CreateSolverType | None, optional): a function of type CreateSolverType that returns a solver.
            If None, then a solver is utilized bases on the problem's properties. Defaults to None.

    Returns:
        SolverResults: the results of the projection.
    """
    # check solver
    _create_solver = guess_best_solver(problem) if create_solver is None else create_solver

    # create and add scalarization function
    # previous_nav_point = objective_dict_to_numpy_array(problem, previous_nav_point).tolist()
    # weights = objective_dict_to_numpy_array(problem, group_improvement_direction).tolist()
    problem_w_asf, target = add_asf_generic_nondiff(
        problem,
        symbol="asf",
        reference_point=previous_nav_point,
        weights=group_improvement_direction,
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
    solver = _create_solver(problem_w_asf)
    return solver(target)


def nautili_init(problem: Problem, create_solver: CreateSolverType | None = None) -> NAUTILI_Response:
    """Initializes the NAUTILI method.

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
    return NAUTILI_Response(
        distance_to_front=0,
        navigation_point=nav_point,
        reachable_bounds={"lower_bounds": lower_bounds, "upper_bounds": upper_bounds},
        reachable_solution=None,
        reference_points=None,
        improvement_directions=None,
        group_improvement_direction=None,
        step_number=0,
    )


def nautili_step(  # NOQA: PLR0913
    problem: Problem,
    steps_remaining: int,
    step_number: int,
    nav_point: dict,
    create_solver: CreateSolverType | None = None,
    group_improvement_direction: dict | None = None,
    reachable_solution: dict | None = None,
) -> NAUTILI_Response:
    if group_improvement_direction is None and reachable_solution is None:
        raise NautiliError("Either group_improvement_direction or reachable_solution must be provided.")

    if group_improvement_direction is not None and reachable_solution is not None:
        raise NautiliError("Only one of group_improvement_direction or reachable_solution should be provided.")

    if group_improvement_direction is not None:
        opt_result = solve_reachable_solution(problem, group_improvement_direction, nav_point, create_solver)
        reachable_solution = opt_result.optimal_objectives

    # update nav point
    new_nav_point = calculate_navigation_point(problem, nav_point, reachable_solution, steps_remaining)

    # update_bounds

    lower_bounds, upper_bounds = solve_reachable_bounds(problem, new_nav_point, create_solver=create_solver)

    distance = calculate_distance_to_front(problem, new_nav_point, reachable_solution)

    return NAUTILI_Response(
        step_number=step_number,
        distance_to_front=distance,
        reference_points=None,
        improvement_directions=None,
        group_improvement_direction=group_improvement_direction,
        navigation_point=new_nav_point,
        reachable_solution=reachable_solution,
        reachable_bounds={"lower_bounds": lower_bounds, "upper_bounds": upper_bounds},
    )


def nautili_all_steps(
    problem: Problem,
    steps_remaining: int,
    reference_points: dict[str, dict[str, float]],
    previous_responses: list[NAUTILI_Response],
    create_solver: CreateSolverType | None = None,
):
    responses = []
    nav_point = previous_responses[-1].navigation_point
    step_number = previous_responses[-1].step_number + 1
    first_iteration = True
    reachable_solution = dict

    # Calculate the improvement directions for each DM

    improvement_directions = {}
    for dm in reference_points:
        if reference_points[dm] is None:
            # If no reference point is provided, use the previous improvement direction
            if previous_responses[-1].reference_points is None:
                raise NautiliError("A reference point must be provided for the first iteration.")
            if previous_responses[-1].improvement_directions is None:
                raise NautiliError("An improvement direction must be provided for the first iteration.")
            reference_points[dm] = previous_responses[-1].reference_points[dm]
            improvement_directions[dm] = previous_responses[-1].improvement_directions[dm]
        else:
            # If a reference point is provided, calculate the improvement direction
            # First, check if the reference point is better than the navigation point
            max_multiplier = [-1 if obj.maximize else 1 for obj in problem.objectives]
            reference_point = (
                np.array([reference_points[dm][obj.symbol] for obj in problem.objectives]) * max_multiplier
            )
            nav_point_arr = np.array([nav_point[obj.symbol] for obj in problem.objectives]) * max_multiplier
            improvement = nav_point_arr - reference_point
            if np.any(improvement < 0):
                msg = (
                    f"If a reference point is provided, it must be better than the navigation point.\n"
                    f" The reference point for {dm} is not better than the navigation point.\n"
                    f" Reference point: {reference_point}, Navigation point: {nav_point}\n"
                    f"Check objectives {np.where(improvement < 0)}"
                )
                raise NautiliError(msg)
            # The improvement direction is in the true objective space
            improvement_directions[dm] = improvement * max_multiplier
    mean_improvement_direction = np.mean(list(improvement_directions.values()), axis=0)
    group_improvement_direction = {
        obj.symbol: mean_improvement_direction[i] for i, obj in enumerate(problem.objectives)
    }

    while steps_remaining > 0:
        if first_iteration:
            response = nautili_step(
                problem,
                steps_remaining=steps_remaining,
                step_number=step_number,
                nav_point=nav_point,
                group_improvement_direction=group_improvement_direction,
                create_solver=create_solver,
            )
            first_iteration = False
        else:
            response = nautili_step(
                problem,
                steps_remaining=steps_remaining,
                step_number=step_number,
                nav_point=nav_point,
                reachable_solution=reachable_solution,
                create_solver=create_solver,
            )
        response.reference_points = reference_points
        response.improvement_directions = improvement_directions
        responses.append(response)
        reachable_solution = response.reachable_solution
        nav_point = response.navigation_point
        steps_remaining -= 1
        step_number += 1
    return responses
