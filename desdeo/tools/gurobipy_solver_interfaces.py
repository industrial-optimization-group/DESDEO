"""Defines solver interfaces for gurobipy."""

from collections.abc import Callable
from dataclasses import dataclass, fields

import gurobipy as gp

from desdeo.problem import Problem, PyomoEvaluator
from desdeo.tools.generics import CreateSolverType, SolverResults

# forward typehints
create_gurobipy_solver: CreateSolverType

def parse_pyomo_optimizer_results(
    opt_res: _pyomo_SolverResults, problem: Problem, evaluator: PyomoEvaluator
) -> SolverResults:
    """Parses pyomo SolverResults into DESDEO SolverResutls.

    Args:
        opt_res (_pyomo_SolverResults): the pyomo solver results.
        problem (Problem): the problem being solved.
        evaluator (PyomoEvaluator): the evalutor utilized to get the pyomo solver results.

    Returns:
        SolverResults: DESDEO solver results.
    """
    results = evaluator.get_values()

    variable_values = {var.symbol: results[var.symbol] for var in problem.variables}
    objective_values = {obj.symbol: results[obj.symbol] for obj in problem.objectives}
    constraint_values = {con.symbol: results[con.symbol] for con in problem.constraints}
    success = (
        opt_res.solver.status == _pyomo_SolverStatus.ok
        and opt_res.solver.termination_condition == _pyomo_TerminationCondition.optimal
    )
    msg = (
        f"Pyomo solver status is: '{opt_res.solver.status}', with termination condition: "
        f"'{opt_res.solver.termination_condition}'."
    )

    return SolverResults(
        optimal_variables=variable_values,
        optimal_objectives=objective_values,
        constraint_values=constraint_values,
        success=success,
        message=msg,
    )

def create_gurobipy_solver(
    problem: Problem, options: dict = dict()
) -> Callable[[str], SolverResults]:
    """Creates a gurobipy solver that utilizes gurobi's own python implementation. 
    Unlike with Pyomo you do not need to have gurobi installed on your system 
    for this to work.

    Suitable for solving mixed-integer linear and quadratic optimization 
    problems.

    Args:
        problem (Problem): the problem to be solved.
        options (GurobiOptions): Dictionary of Gurobi parameters to set.
            This is passed to pyomo as is, so it works the same as options
            would for calling pyomo SolverFactory directly.

    Returns:
        Callable[[str], SolverResults]: returns a callable function that takes
            as its argument one of the symbols defined for a function expression in
            problem.
    """
    evaluator = PyomoEvaluator(problem)

    def solver(target: str) -> SolverResults:
        evaluator.set_optimization_target(target)

        opt = pyomo.SolverFactory('gurobi', solver_io='python', options=options)

        with pyomo.SolverFactory(
            'gurobi', solver_io='python'
        ) as opt:
            opt_res = opt.solve(evaluator.model)
            return parse_pyomo_optimizer_results(opt_res, problem, evaluator)

    return solver