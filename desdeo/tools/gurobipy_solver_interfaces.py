"""Defines solver interfaces for gurobipy."""

from collections.abc import Callable
from dataclasses import dataclass, fields

import gurobipy as gp

from desdeo.problem import Problem, GurobipyEvaluator
from desdeo.tools.generics import CreateSolverType, SolverResults

# forward typehints
create_gurobipy_solver: CreateSolverType

def parse_gurobipy_optimizer_results(
    problem: Problem, evaluator: GurobipyEvaluator
) -> SolverResults:
    """Parses results from GurobipyEvaluator's model into DESDEO SolverResutls.

    Args:
        problem (Problem): the problem being solved.
        evaluator (GurobipyEvaluator): the evalutor utilized to solve the problem.

    Returns:
        SolverResults: DESDEO solver results.
    """
    results = evaluator.get_values()

    variable_values = {var.symbol: results[var.symbol] for var in problem.variables}
    objective_values = {obj.symbol: results[obj.symbol] for obj in problem.objectives}
    constraint_values = {con.symbol: results[con.symbol] for con in problem.constraints}
    success = ( evaluator.model.status == gp.GRB.OPTIMAL )
    if evaluator.model.status == gp.GRB.OPTIMAL:
        status = "Optimal solution found."
    elif evaluator.model.status == gp.GRB.INFEASIBLE:
        status = "Model is infeasible."
    elif evaluator.model.status == gp.GRB.UNBOUNDED:
        status = "Model is unbounded."
    elif evaluator.model.status == gp.GRB.INF_OR_UNBD:
        status = "Model is either infeasible or unbounded."
    else:
        status = f"Optimization ended with status: {evaluator.model.status}"
    msg = (
        f"Gurobipy solver status is: '{status}'"
    )

    return SolverResults(
        optimal_variables=variable_values,
        optimal_objectives=objective_values,
        constraint_values=constraint_values,
        success=success,
        message=msg,
    )

def create_gurobipy_solver(
    problem: Problem, options: dict[str,any] = dict()
) -> Callable[[str], SolverResults]:
    """Creates a gurobipy solver that utilizes gurobi's own python implementation. 
    Unlike with Pyomo you do not need to have gurobi installed on your system 
    for this to work.

    Suitable for solving mixed-integer linear and quadratic optimization 
    problems.

    Args:
        problem (Problem): the problem to be solved.
        options (dict[str,any]): Dictionary of Gurobi parameters to set.
            You probably don't need to set any of these and can just use the defaults.
            For available parameters see https://www.gurobi.com/documentation/current/refman/parameters.html

    Returns:
        Callable[[str], SolverResults]: returns a callable function that takes
            as its argument one of the symbols defined for a function expression in
            problem.
    """
    evaluator = GurobipyEvaluator(problem)
    for key, value in options.items():
        evaluator.model.setParam(key,value)

    def solver(target: str) -> SolverResults:
        evaluator.set_optimization_target(target)
        evaluator.model.optimize()
        return parse_gurobipy_optimizer_results(problem, evaluator)

    return solver