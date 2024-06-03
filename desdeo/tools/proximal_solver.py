"""Defines solvers meant to be utilized with Problems with discrete representations."""

import polars as pl

from desdeo.problem import EvaluatorModesEnum, GenericEvaluator, Problem
from desdeo.tools.generics import SolverResults


class ProximalSolver:
    """Creates a solver that finds the closest solution given a fully discrete problem.

    Note:
        This solver is extremely naive. It will optimize the problem and the result will
            be a point defined for a discrete problem that is closest (Euclidean
            distance) to the optimum. The result may be wildly inaccurate depending on how
            representative the discrete points are of the original problem.
    """

    def __init__(self, problem: Problem):
        """Creates a solver that assumes the problem being a fully discrete one.

        Assumes that problem has only data-based objectives and a discrete definition
        that fully defines all the objectives.

        Args:
            problem (Problem): the problem being solved.

        Returns:
            Callable[[str], SolverResults]: a solver that can be called with a target to be optimized.
                This function then returns the results of the optimization as in a `SolverResults` dataclass.
        """
        self.problem = problem
        self.evaluator = GenericEvaluator(problem, evaluator_mode=EvaluatorModesEnum.discrete)

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
            cons_condition = pl.lit(True)
            for constraint in self.problem.constraints:
                cons_condition = cons_condition & (results_df[constraint.symbol] <= 0)

            results_df = results_df.filter(cons_condition)

        # find the row with the minimum value in the 'target' column
        closest = results_df.sort(target).head(1)

        # extract relevant results, extract them as disc for easier jsonification
        variable_values = {variable.symbol: closest[variable.symbol][0] for variable in self.problem.variables}
        objective_values = {objective.symbol: closest[objective.symbol][0] for objective in self.problem.objectives}
        constraint_values = (
            {constraint.symbol: closest[constraint.symbol][0] for constraint in self.problem.constraints}
            if self.problem.constraints is not None
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
