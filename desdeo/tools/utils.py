"""General utilities related to solvers."""
from desdeo.problem import Problem, ObjectiveTypeEnum
from desdeo.tools.generics import CreateSolverType
from desdeo.tools.scipy_solver_interfaces import create_scipy_de_solver, create_scipy_minimize_solver
from desdeo.tools.proximal_solver import create_proximal_solver


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

    Returns:
        tuple[list[float], list[float]]: a list with the corrected ideal point
            and a list with the corrected nadir point. Will return None for missing
            elements.
    """
    ideal_point = {
        objective.symbol: objective.ideal if not objective.maximize else -objective.ideal
        for objective in problem.objectives
    }
    nadir_point = {
        objective.symbol: objective.nadir if not objective.maximize else -objective.nadir
        for objective in problem.objectives
    }

    return ideal_point, nadir_point
