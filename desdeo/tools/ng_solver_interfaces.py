"""Solver interfaces to the optimization routines found in nevergrad.

For more info, see https://facebookresearch.github.io/nevergrad/index.html
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import nevergrad as ng
from pydantic import BaseModel, Field

from desdeo.problem import Problem, SympyEvaluator
from desdeo.tools.generics import BaseSolver, SolverResults

available_nevergrad_optimizers = [
    "NGOpt",
    "TwoPointsDE",
    "PortfolioDiscreteOnePlusOne",
    "OnePlusOne",
    "CMA",
    "TBPSA",
    "PSO",
    "ScrHammersleySearchPlusMiddlePoint",
    "RandomSearch",
]


class NevergradGenericOptions(BaseModel):
    """Defines options to be passed to nevergrad's optimization routines."""

    budget: int = Field(description="The maximum number of allowed function evaluations.", default=100)
    """The maximum number of allowed function evaluations. Defaults to 100."""

    num_workers: int = Field(description="The maximum number of allowed parallel evaluations.", default=1)
    """The maximum number of allowed parallel evaluations. This is currently
    used to define the batch size when evaluating problems. Defaults to 1."""

    optimizer: Literal[*available_nevergrad_optimizers] = Field(
        description=(
            "The optimizer to be used. Must be one of `NGOpt`, `TwoPointDE`, `PortfolioDiscreteOnePlusOne`, "
            "`OnePlusOne`, `CMA`, `TBPSA`, `PSO`, `ScrHammersleySearchPlusMiddlePoint`, or `RandomSearch`. "
            "Defaults to `NGOpt`."
        ),
        default="NGOpt",
    )
    """The optimizer to be used. Must be one of `NGOpt`, `TwoPointsDE`, `PortfolioDiscreteOnePlusOne`,
    `OnePlusOne`, `CMA`, `TBPSA`, `PSO`, `ScrHammersleySearchPlusMiddlePoint`, or `RandomSearch`.
    Defaults to `NGOpt`."""


_default_nevergrad_generic_options = NevergradGenericOptions()
"""The set of default options for nevergrad's NgOpt optimizer."""


def parse_ng_results(results: dict, problem: Problem, evaluator: SympyEvaluator) -> SolverResults:
    """Parses the optimization results returned by nevergrad solvers.

    Args:
        results (dict): the results. A dict with at least the keys
            `recommendation`, which points to a parametrization returned by
            nevergrad solvers, `message` with information about the optimization,
            and `success` indicating whther a recommendation was found successfully
            or not.
        problem (Problem): the problem the results belong to.
        evaluator (GenericEvaluator): the evaluator used to evaluate the problem.

    Returns:
        SolverResults: a pydantic dataclass withthe relevant optimization results.
    """
    optimal_variables = results["recommendation"].value
    success = results["success"]
    msg = results["message"]

    results = evaluator.evaluate(optimal_variables)

    optimal_objectives = {obj.symbol: results[obj.symbol] for obj in problem.objectives}

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

    return SolverResults(
        optimal_variables=optimal_variables,
        optimal_objectives=optimal_objectives,
        constraint_values=constraint_values,
        extra_func_values=extra_func_values,
        scalarization_values=scalarization_values,
        success=success,
        message=msg,
    )


class NevergradGenericSolver(BaseSolver):
    """Creates a solver that utilizes optimizations routines found in the nevergrad library."""

    def __init__(self, problem: Problem, options: NevergradGenericOptions | None = _default_nevergrad_generic_options):
        """Creates a solver that utilizes optimizations routines found in the nevergrad library.

        These solvers are best utilized for black-box, gradient free optimization with
        computationally expensive function calls. Utilizing multiple workers is recommended
        (see `NevergradGenericOptions`) when function calls are heavily I/O bound.

        See https://facebookresearch.github.io/nevergrad/getting_started.html for further information
        on nevergrad and its solvers.

        References:
            Rapin, J., & Teytaud, O. (2018). Nevergrad - A gradient-free
                optimization platform. GitHub.
                https://GitHub.com/FacebookResearch/Nevergrad

        Args:
            problem (Problem): the problem to be solved.
            options (NgOptOptions | None): options to be passes to the solver.
                If none, `_default_ng_ngopt_options` are used. Defaults to None.

        """
        self.problem = problem
        self.options = options if options is not None else _default_nevergrad_generic_options
        self.evaluator = SympyEvaluator(problem)

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for the given target.

        Args:
            target (str): the symbol of the objective function to be optimized.

        Returns:
            SolverResults: the results of the optimization.
        """
        parametrization = ng.p.Dict(
            **{
                var.symbol: ng.p.Scalar(
                    # sets the initial value of the variables, if None, then the
                    # mid-point of the lower and upper bounds is chosen as the
                    # initial value.
                    init=var.initial_value if var.initial_value is not None else (var.lowerbound + var.upperbound) / 2
                ).set_bounds(var.lowerbound, var.upperbound)
                for var in self.problem.variables
            }
        )

        optimizer = ng.optimizers.registry[self.options.optimizer](
            parametrization=parametrization, **self.options.model_dump(exclude="optimizer")
        )

        constraint_symbols = (
            None if self.problem.constraints is None else [con.symbol for con in self.problem.constraints]
        )

        try:
            if optimizer.num_workers == 1:
                # single thread
                recommendation = optimizer.minimize(
                    lambda xs, t=target: self.evaluator.evaluate_target(xs, t),
                    constraint_violation=[
                        lambda xs, t=con_t: self.evaluator.evaluate_target(xs, t) for con_t in constraint_symbols
                    ]
                    if constraint_symbols is not None
                    else None,
                )

            elif optimizer.num_workers > 1:
                # multiple processors
                with ThreadPoolExecutor(max_workers=optimizer.num_workers) as executor:
                    recommendation = optimizer.minimize(
                        lambda xs, t=target: self.evaluator.evaluate_target(xs, t),
                        constraint_violation=[
                            lambda xs, t=con_t: self.evaluator.evaluate_target(xs, t) for con_t in constraint_symbols
                        ]
                        if constraint_symbols is not None
                        else None,
                        executor=executor,
                        batch_mode=False,
                    )

            msg = f"Recommendation found by {self.options.optimizer}."
            success = True

        except Exception as e:
            msg = f"{self.options.optimizer} failed. Possible reason: {e}"
            success = False

        result = {"recommendation": recommendation, "message": msg, "success": success}

        return parse_ng_results(result, self.problem, self.evaluator)
