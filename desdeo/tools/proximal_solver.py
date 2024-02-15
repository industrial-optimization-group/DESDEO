"""Defines solvers meant to be utilized with Problems with pre-defined solutions."""
from typing import Callable

from desdeo.problem import GenericEvaluator, EvaluatorModesEnum, Problem
from desdeo.tools.generics import SolverError, SolverResults


def create_proximal_solver(problem: Problem) -> Callable[[str], SolverResults]:
    """_summary_

    Args:
        problem (Problem): _description_

    Returns:
        Callable[[str], SolverResults]: _description_
    """
    evaluator = GenericEvaluator(problem, evaluator_mode=EvaluatorModesEnum.discrete)

    def solver(target: str) -> SolverResults:
        results_df = evaluator.evaluate()

        # find the row with the minimum value in the 'target' column
        # closest = combined_df.sort("distance").head(1)

        closest = results_df.sort(target).head(1)

        # extract relevant results, extract them as disc for easier jsonification
        variable_values = closest[[var.symbol for var in problem.variables]].to_dict(as_series=False)
        objective_values = closest[[obj.symbol for obj in problem.objectives]].to_dict(as_series=False)
        constraint_values = closest[[con.symbol for con in problem.constraints]].to_dict(as_series=False)
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
