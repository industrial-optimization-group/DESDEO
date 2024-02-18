"""Defines solvers meant to be utilized with Problems with pre-defined solutions."""
from collections.abc import Callable

import polars as pl

from desdeo.problem import GenericEvaluator, EvaluatorModesEnum, Problem
from desdeo.tools.generics import CreateSolverType, SolverResults

# forward typehints
create_proximal_solver: CreateSolverType


def create_proximal_solver(problem: Problem) -> Callable[[str], SolverResults]:
    """Creates a solver that assumes the problem being a fully discrete one.

    Assumes that problem has only data-based objectives and a discrete definition
    that fully defines all the objectives.

    Args:
        problem (Problem): the problem being solved.

    Returns:
        Callable[[str], SolverResults]: a solver that can be called with a target to be optimized.
            This function then returns the results of the optimization as in a `SolverResults` dataclass.
    """
    evaluator = GenericEvaluator(problem, evaluator_mode=EvaluatorModesEnum.discrete)

    def solver(target: str) -> SolverResults:
        results_df = evaluator.evaluate()

        # check constraint values if problem has constraints
        if problem.constraints is not None:
            cons_condition = pl.lit(True)
            for constraint in problem.constraints:
                cons_condition = cons_condition & (results_df[constraint.symbol] <= 0)

            results_df = results_df.filter(cons_condition)

        # find the row with the minimum value in the 'target' column
        closest = results_df.sort(target).head(1)

        # extract relevant results, extract them as disc for easier jsonification
        variable_values = {variable.symbol: closest[variable.symbol][0] for variable in problem.variables}
        objective_values = {objective.symbol: closest[objective.symbol][0] for objective in problem.objectives}
        constraint_values = (
            {constraint.symbol: closest[constraint.symbol][0] for constraint in problem.constraints}
            if problem.constraints is not None
            else None
        )
        message = f"Optimal value found from tabular data minimizing the column '{target}'."
        success = True

        # wrap results and return them
        return SolverResults(
            optimal_variables=variable_values,
            optimal_objectives=objective_values,
            constraint_values=constraint_values,
            success=success,
            message=message,
        )

    return solver
