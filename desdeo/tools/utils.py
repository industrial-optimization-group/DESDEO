"""General utilities related to solvers."""

from desdeo.problem import ObjectiveTypeEnum, Problem
from desdeo.tools.generics import CreateSolverType
from desdeo.tools.proximal_solver import create_proximal_solver
from desdeo.tools.scipy_solver_interfaces import (
    create_scipy_de_solver,
    create_scipy_minimize_solver,
)

available_solvers = {
    "scipy_minimize": create_scipy_minimize_solver,
    "scipy_de": create_scipy_de_solver,
    "proximal": create_proximal_solver,
}


def guess_best_solver(problem: Problem) -> CreateSolverType:
    """Given a problem, tries to guess the best solver to handle it.

    Args:
        problem (Problem): the problem being solved.

    Note:
        Needs to be extended as new solvers are implemented.

    Returns:
        Callable[[Problem, Kwargs], Callable[[str], SolverResults]]: a callable function that returns a function
            that can be called with a target to optimize and then returns the optimization results in a
            `SolverResults` dataclass.
    """
    # needs to be extended as new solver are implemented

    # check if problem has only data-based objectives
    all_data_based = all(objective.objective_type == ObjectiveTypeEnum.data_based for objective in problem.objectives)

    # check if problem has a discrete definition
    has_discrete = problem.discrete_representation is not None

    if all_data_based and has_discrete:
        # problem has only data-based objectives and a discrete definition is available
        # guess proximal solver is best
        return available_solvers["proximal"]

    # else, guess scipy differential evolution is best
    return available_solvers["scipy_de"]

    # thigs to check: variable types, does the problem have constraint, constraint types, etc...


def get_corrected_ideal_and_nadir(problem: Problem) -> tuple[dict[str, float | None], dict[str, float | None] | None]:
    """Compute the corrected ideal and nadir points depending if an objective function is to be maximized or not.

    I.e., the ideal and nadir point element for objectives to be maximized will be multiplied by -1.

    Args:
        problem (Problem): the problem with the ideal and nadir points.

    Raises:
        ValueError: some of the ideal or nadir point components have not been defined
            for some of the objectives.

    Returns:
        tuple[list[float], list[float]]: a list with the corrected ideal point
            and a list with the corrected nadir point. Will return None for missing
            elements.
    """
    # check that ideal and nadir points are actually defined
    if any(obj.ideal is None for obj in problem.objectives) or any(obj.nadir is None for obj in problem.objectives):
        msg = "Some of the objectives have not a defined ideal or nadir value."
        raise ValueError(msg)

    ideal_point = {
        objective.symbol: objective.ideal if not objective.maximize else -objective.ideal
        for objective in problem.objectives
    }
    nadir_point = {
        objective.symbol: objective.nadir if not objective.maximize else -objective.nadir
        for objective in problem.objectives
    }

    return ideal_point, nadir_point


def get_corrected_reference_point(problem: Problem, reference_point: dict[str, float]) -> dict[str, float]:
    """Correct the components of a reference point.

    Correct the components of a reference point by multiplying the components
    related to maximized objective functions by -1.

    Args:
        problem (Problem): the problem the reference point is related to.
        reference_point (dict[str, float]): the reference point to be corrected.

    Returns:
        dict[str, float]: the corrected reference point.
    """
    return {
        obj.symbol: reference_point[obj.symbol] * -1 if obj.maximize else reference_point[obj.symbol]
        for obj in problem.objectives
    }
