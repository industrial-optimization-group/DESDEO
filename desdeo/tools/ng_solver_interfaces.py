"""Solver interfaces to the optimization routines found in nevergrad.

For more info, see https://facebookresearch.github.io/nevergrad/index.html
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import nevergrad as ng
from pydantic import BaseModel, Field

from desdeo.problem import Problem, SympyEvaluator
from desdeo.tools.generics import CreateSolverType, SolverResults

# forward typehints
create_ng_generic_solver: CreateSolverType

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
        descriptions=(
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
    x_opt = results["recommendation"].value
    success = results["success"]
    msg_opt = results["message"]

    eval_opt = evaluator.evaluate(x_opt)

    f_opt = {obj.symbol: eval_opt[obj.symbol] for obj in problem.objectives}

    if problem.constraints is not None:
        # has constraints
        const_opt = {con.symbol: eval_opt[con.symbol] for con in problem.constraints}
    else:
        const_opt = None

    return SolverResults(
        optimal_variables=x_opt, optimal_objectives=f_opt, constraint_values=const_opt, success=success, message=msg_opt
    )


def create_ng_generic_solver(
    problem: Problem, options: NevergradGenericOptions = _default_nevergrad_generic_options
) -> Callable[[str], SolverResults]:
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
        options (NgOptOptions): options to be passes to the solver. Defaults to `_default_ng_ngopt_options`.

    Returns:
        Callable[[str], SolverResults]: returns a callable function that takes
            as its argument one of the symbols defined for a function expression in
            problem.
    """
    evaluator = SympyEvaluator(problem)

    def solver(target: str) -> SolverResults:
        parametrization = ng.p.Dict(
            **{
                var.symbol: ng.p.Scalar(
                    # sets the initial value of the variables, if None, then the
                    # mid-point of the lower and upper bounds is chosen as the
                    # initial value.
                    init=var.initial_value if var.initial_value is not None else (var.lowerbound + var.upperbound) / 2
                ).set_bounds(var.lowerbound, var.upperbound)
                for var in problem.variables
            }
        )

        optimizer = ng.optimizers.registry[options.optimizer](
            parametrization=parametrization, **options.model_dump(exclude="optimizer")
        )

        constraint_symbols = None if problem.constraints is None else [con.symbol for con in problem.constraints]

        try:
            if optimizer.num_workers == 1:
                # single thread
                recommendation = optimizer.minimize(
                    lambda xs, t=target: evaluator.evaluate_target(xs, t),
                    constraint_violation=[
                        lambda xs, t=con_t: evaluator.evaluate_target(xs, t) for con_t in constraint_symbols
                    ]
                    if constraint_symbols is not None
                    else None,
                )

            elif optimizer.num_workers > 1:
                # multiple processors
                with ThreadPoolExecutor(max_workers=optimizer.num_workers) as executor:
                    recommendation = optimizer.minimize(
                        lambda xs, t=target: evaluator.evaluate_target(xs, t),
                        constraint_violation=[
                            lambda xs, t=con_t: evaluator.evaluate_target(xs, t) for con_t in constraint_symbols
                        ]
                        if constraint_symbols is not None
                        else None,
                        executor=executor,
                        batch_mode=False,
                    )

            msg = f"Recommendation found by {options.optimizer}."
            success = True

        except Exception as e:
            msg = f"{options.optimizer} failed. Possible reason: {e}"
            success = False

        result = {"recommendation": recommendation, "message": msg, "success": success}

        return parse_ng_results(result, problem, evaluator)

    return solver
