"""Defines solvers meant to be utilized with Problems with discrete representations."""

import polars as pl

from desdeo.problem import (
    ObjectiveTypeEnum,
    PolarsEvaluator,
    PolarsEvaluatorModesEnum,
    Problem,
)
from desdeo.tools.generics import BaseSolver, SolverError, SolverResults


class ProximalSolver(BaseSolver):
    """Creates a solver that finds the closest solution given a fully discrete problem.

    Note:
        This solver is extremely naive. It will optimize the problem and the result will
            be a point defined for a discrete problem that is closest (Euclidean
            distance) to the optimum. The result may be wildly inaccurate depending on how
            representative the discrete points are of the original problem.
    """

    def __init__(self, problem: Problem, kwargs: dict | None = None):
        """Creates a solver that assumes the problem being a fully discrete one.

        Assumes that problem has only data-based objectives and a discrete definition
        that fully defines all the objectives.

        Args:
            problem (Problem): the problem being solved.
            kwargs (Optional[dict]): optional keyword arguments. Not used right now, but kept
                here for compatibility reasons. Defaults to None.

        """
        for obj in problem.objectives:
            if obj.objective_type is not ObjectiveTypeEnum.data_based:
                raise SolverError(f"All objectives must be data-based {obj.symbol}.")
        if problem.discrete_representation is None:
            raise SolverError("Problem must have a discrete representation defined.")
        self.problem = problem
        self.evaluator = PolarsEvaluator(problem, evaluator_mode=PolarsEvaluatorModesEnum.discrete)

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for the given target.

        Args:
            target (str): the symbol of the objective function to be optimized.

        Returns:
            SolverResults: the results fo the optimization.
        """
        results_df = self.evaluator.evaluate()

        # check constraint values if problem has constraints
        if self.problem.constraints is not None:
            cons_condition = pl.lit(True)  # noqa: FBT003
            for constraint in self.problem.constraints:
                cons_condition = cons_condition & (results_df[constraint.symbol] <= 0)

            results_df = results_df.filter(cons_condition)

        # find the row with the minimum value in the 'target' column
        closest = results_df.sort(target).head(1)

        # extract relevant results, extract them as dict for easier jsonification
        variable_values = {variable.symbol: closest[variable.symbol][0] for variable in self.problem.variables}
        objective_values = {objective.symbol: closest[objective.symbol][0] for objective in self.problem.objectives}
        constraint_values = (
            {constraint.symbol: closest[constraint.symbol][0] for constraint in self.problem.constraints}
            if self.problem.constraints is not None
            else None
        )
        extra_func_values = (
            {extra.symbol: closest[extra.symbol][0] for extra in self.problem.extra_funcs}
            if self.problem.extra_funcs is not None
            else None
        )
        scalarization_values = (
            {scal.symbol: closest[scal.symbol][0] for scal in self.problem.scalarization_funcs}
            if self.problem.scalarization_funcs is not None
            else None
        )
        message = f"Optimal value found from tabular data minimizing the column '{target}'."
        success = True

        # wrap results and return them
        return SolverResults(
            optimal_variables=variable_values,
            optimal_objectives=objective_values,
            constraint_values=constraint_values,
            extra_func_values=extra_func_values,
            scalarization_values=scalarization_values,
            success=success,
            message=message,
        )
