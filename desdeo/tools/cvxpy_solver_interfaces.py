"""Defines solver interfaces for cvxpy."""

import cvxpy as cp
from pydantic import BaseModel, Field

from desdeo.problem import (
    CVXPYEvaluator,
    Problem,
)
from desdeo.tools.generics import BaseSolver, SolverResults


class CVXPYSolverOptions(BaseModel):
    """Defines a pydantic model to store and pass options to the CVXPY solver."""

    solver: str | None = Field(
        description="The solver to use.",
        default=None,
    )
    solver_path: list[str | tuple[str, dict[str, object]]] | None = Field(
        description="The solvers to try with optional arguments, in order of preference.",
        default=None,
    )
    verbose: bool = Field(description="Overrides the default of hiding solver output.", default=False)
    gp: bool = Field(description="Parse the problem as a disciplined geometric program.", default=False)
    qcp: bool = Field(description="Parse the problem as a disciplined quasiconvex program.", default=False)
    requires_grad: bool = Field(
        description=(
            "Allow gradient computation with respect to Parameters by calling problem.backward() "
            "or problem.derivative() after solving."
        ),
        default=False,
    )
    enforce_dpp: bool = Field(
        description=(
            "Raise a DPPError for non-DPP problems when solving instead of only warning. "
            "Only relevant for problems involving Parameters."
        ),
        default=False,
    )
    ignore_dpp: bool = Field(
        description=("Treat DPP problems as non-DPP, which may speed up compilation."),
        default=False,
    )
    extra_options: dict[str, object] | None = Field(
        description="Additional keyword arguments forwarded directly to cvxpy Problem.solve().",
        default=None,
    )


_default_cvxpy_options = CVXPYSolverOptions()


def parse_cvxpy_optimizer_results(problem: Problem, evaluator: CVXPYEvaluator) -> SolverResults:
    """Parses results from CVXPYEvaluator's problem into DESDEO SolverResults.

    Args:
        problem (Problem): the problem being solved.
        evaluator (CVXPYEvaluator): the evaluator utilized to solve the problem.

    Returns:
        SolverResults: DESDEO solver results.
    """
    results = evaluator.get_values()

    variable_values = {var.symbol: results[var.symbol] for var in problem.variables}
    objective_values = {obj.symbol: results[obj.symbol] for obj in problem.objectives}
    constraint_values = (
        {con.symbol: results[con.symbol] for con in problem.constraints} if problem.constraints is not None else None
    )
    extra_func_values = (
        {extra.symbol: results[extra.symbol] for extra in problem.extra_funcs}
        if problem.extra_funcs is not None
        else None
    )
    scalarization_values = (
        {scal.symbol: results[scal.symbol] for scal in problem.scalarization_funcs}
        if problem.scalarization_funcs is not None
        else None
    )
    lagrange_multipliers = None

    success = evaluator.problem_model.status in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}
    if evaluator.problem_model.status == cp.OPTIMAL:
        status = "Optimal solution found."
    elif evaluator.problem_model.status == cp.OPTIMAL_INACCURATE:
        status = "Optimal solution found (inaccurate)."
    elif evaluator.problem_model.status == cp.INFEASIBLE:
        status = "Problem is infeasible."
    elif evaluator.problem_model.status == cp.UNBOUNDED:
        status = "Problem is unbounded."
    elif evaluator.problem_model.status == cp.INFEASIBLE_INACCURATE:
        status = "Problem is infeasible (inaccurate)."
    elif evaluator.problem_model.status == cp.UNBOUNDED_INACCURATE:
        status = "Problem is unbounded (inaccurate)."
    else:
        status = f"Optimization ended with status: {evaluator.problem_model.status}"
    msg = f"CVXPY solver status is: '{status}'"

    return SolverResults(
        optimal_variables=variable_values,
        optimal_objectives=objective_values,
        constraint_values=constraint_values,
        extra_func_values=extra_func_values,
        scalarization_values=scalarization_values,
        lagrange_multipliers=lagrange_multipliers,
        success=success,
        message=msg,
    )


class CVXPYSolver(BaseSolver):
    """Creates a CVXPY solver that utilizes CVXPY's optimization capabilities."""

    def __init__(self, problem: Problem, options: CVXPYSolverOptions = _default_cvxpy_options):
        """The solver is initialized by supplying a problem and options.

        CVXPY is a Python-embedded modeling language for convex optimization problems,
        supporting a broad range of problem types.

        Args:
            problem (Problem): the problem to be solved.
            options (CVXPYSolverOptions): Pydantic model containing solver options for CVXPY.
                For available options see https://www.cvxpy.org/api_reference/cvxpy.problems.html#solve
        """
        self.evaluator = CVXPYEvaluator(problem)
        self.problem = problem

        options_dict = {k: v for k, v in options.model_dump().items() if v is not None}
        extra_options = options_dict.pop("extra_options", None)
        if extra_options is not None:
            options_dict.update(extra_options)
        self.solve_options = options_dict

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for the given target.

        Args:
            target (str): the symbol of the function to be optimized, and which is
                defined in the problem given when initializing the solver.

        Returns:
            SolverResults: the results of the optimization.
        """
        self.evaluator.set_optimization_target(target)
        self.evaluator.solve(**self.solve_options)
        return parse_cvxpy_optimizer_results(self.problem, self.evaluator)


def check_cvxpy_suitability(problem: Problem) -> bool:
    """Checks whether a problem is suitable for being solved with CVXPY."""
    try:
        evaluator = CVXPYEvaluator(problem)
        for obj in problem.objectives:
            evaluator.set_optimization_target(obj.symbol)
            if not (evaluator.problem_model.is_dcp() or evaluator.problem_model.is_dgp()):
                return False
                break
        else:
            return True
    except Exception:
        return False
