"""General utilities related to solvers."""

import numpy as np

from desdeo.problem import ObjectiveTypeEnum, Problem, VariableDomainTypeEnum, numpy_array_to_objective_dict

from .generics import BaseSolver
from .gurobipy_solver_interfaces import GurobipySolver
from .ng_solver_interfaces import NevergradGenericSolver
from .proximal_solver import ProximalSolver
from .pyomo_solver_interfaces import (
    PyomoBonminSolver,
    PyomoGurobiSolver,
    PyomoIpoptSolver,
)
from .scipy_solver_interfaces import ScipyDeSolver, ScipyMinimizeSolver

available_solvers = {
    "scipy_minimize": ScipyMinimizeSolver,
    "scipy_de": ScipyDeSolver,
    "proximal": ProximalSolver,
    "nevergrad": NevergradGenericSolver,
    "pyomo_bonmin": PyomoBonminSolver,
    "pyomo_ipopt": PyomoIpoptSolver,
    "pyomo_gurobi": PyomoGurobiSolver,
    "gurobipy": GurobipySolver,
}


def guess_best_solver(problem: Problem) -> BaseSolver:
    """Given a problem, tries to guess the best solver to handle it.

    Args:
        problem (Problem): the problem being solved.

    Note:
        Needs to be extended as new solvers are implemented.

    Returns:
        BaseSolver: a solver class that uses BaseSolver as a base class
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

    # check if the problem is differentiable and if it is mixed integer
    if problem.is_twice_differentiable and problem.variable_domain in [
        VariableDomainTypeEnum.integer,
        VariableDomainTypeEnum.mixed,
    ]:
        return available_solvers["pyomo_bonmin"]

    # check if the problem is differentiable and continuous
    if problem.is_twice_differentiable and problem.variable_domain in [VariableDomainTypeEnum.continuous]:
        return available_solvers["pyomo_ipopt"]

    # else, guess nevergrad heuristics to be the best
    return available_solvers["nevergrad"]

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

def payoff_table_method(
    problem: Problem,
    solver: BaseSolver = None
) -> tuple[dict[str, float], dict[str, float]]:
    """Solves a representation for the ideal and nadir points for a multiobjective optimization problem.

    Args:
        problem (Problem): The problem for which the ideal and nadir are solved.
        solver (BaseSolver): The solver to be used in solving the points. Defaults to None.

    Returns:
        tuple[dict[str, float], dict[str, float]]: The estimated ideal and nadir points.
    """
    solver = solver if solver is not None else guess_best_solver(problem)
    solver = solver(problem)

    k = len(problem.objectives)
    po_table = np.zeros((k, k))

    for i in range(k):
        res = solver.solve(f"f_{i+1}_min")
        for j in range(k):
            po_table[i][j] = res.optimal_objectives[f"f_{j+1}"]
    ideal = np.diag(po_table)
    nadir = []
    for i in range(k):
        if problem.objectives[i].maximize:
            nadir.append(np.min(po_table.T[i]))
        else:
            nadir.append(np.max(po_table.T[i]))
    return numpy_array_to_objective_dict(problem, ideal), numpy_array_to_objective_dict(problem, nadir)
