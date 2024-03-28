"""Solver interfaces to the optimization routines found in nevergrad.

For more info, see https://facebookresearch.github.io/nevergrad/index.html
"""

from collections.abc import Callable

import nevergrad as ng
from pydantic import BaseModel, Field

from desdeo.problem import GenericEvaluator, Problem
from desdeo.tools.generics import CreateSolverType, SolverResults

# forward typehints
create_ng_generic_solver: CreateSolverType


class NevergradGenericOptions(BaseModel):
    """Defines options to be passed to nevergrad's NgOpt optimization routine."""

    budget: int = Field(description="The maximum number of allowed function evaluations.", default=100)
    """"The maximum number of allowed function evaluations. Defaults to 100."""

    num_workers: int = Field(description="The maximum number of allowed parallel evaluations.", default=1)
    """The maximum number of allowed parallel evaluations. This is currently
    used to define the batch size when evaluating problems. Defaults to 1."""

    optimizer: str = Field(
        descriptions=(
            "The optimizer to be used. Must be one of `NGOpt`, `TwoPointDE`, `PortfolioDiscreteOnePlusOne`, "
            "`OnePlusOne`, `CMA`, `TBPSA`, `PSO`, `ScrHammersleySearchPlusMiddlePoint`, or `RandomSearch`. "
            "Defaults to `NGOpt`."
        ),
        default="NGOpt",
    )
    """The optimizer to be used. Must be one of `NGOpt`, `TwoPointsDE`, `PortfolioDiscreteOnePlusOne`, "
    "`OnePlusOne`, `CMA`, `TBPSA`, `PSO`, `ScrHammersleySearchPlusMiddlePoint`, or `RandomSearch`. "
    "Defaults to `NGOpt`."""


_default_nevergrad_generic_options = NevergradGenericOptions()
"""The set of default options for nevergrad's NgOpt optimizer."""


def parse_ng_results(results: dict, problem: Problem, evaluator: GenericEvaluator) -> SolverResults:
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

    f_opt = {obj.symbol: eval_opt[obj.symbol][0] for obj in problem.objectives}

    if problem.constraints is not None:
        # has constraints
        const_opt = {con.symbol: eval_opt[con.symbol][0] for con in problem.constraints}
    else:
        const_opt = None

    return SolverResults(
        optimal_variables=x_opt, optimal_objectives=f_opt, constraint_values=const_opt, success=success, message=msg_opt
    )


def create_ng_generic_solver(
    problem: Problem, options: NevergradGenericOptions = _default_nevergrad_generic_options
) -> Callable[[str], SolverResults]:
    """Creates a solver that utilizes the `ng.optimizers.NGOpt` routine.

    Args:
        problem (Problem): the problem to be solved.
        options (NgOptOptions): options to be passes to the solver. Defaults to `_default_ng_ngopt_options`.

    Returns:
        Callable[[str], SolverResults]: returns a callable function that takes
            as its argument one of the symbols defined for a function expression in
            problem.
    """
    evaluator = GenericEvaluator(problem)

    def solver(target: str) -> SolverResults:
        parametrization = ng.p.Dict(
            **{
                var.symbol: ng.p.Array(
                    # sets the initial value of the variables, if None, then the
                    # mid-point of the lower and upper bounds is chosen as the
                    # initial value.
                    init=[var.initial_value if var.initial_value is not None else (var.lowerbound + var.upperbound) / 2]
                ).set_bounds(var.lowerbound, var.upperbound)
                for var in problem.variables
            }
        )

        # ng.optimizers.registry["NGOpt"]
        optimizer = ng.optimizers.registry[options.optimizer](
            parametrization=parametrization, **options.model_dump(exclude="optimizer")
        )

        # optimize in batches
        batch_size = optimizer.num_workers
        constraint_symbols = None if problem.constraints is None else [con.symbol for con in problem.constraints]

        try:
            for _ in range(optimizer.budget // batch_size):
                # Generate a batch of candidates
                candidates = [optimizer.ask() for _ in range(batch_size)]

                # Extract arguments from candidates for evaluation
                xs = {key: [candidate.args[0][key][0] for candidate in candidates] for key in candidates[0].args[0]}

                # Evaluate the batch and find the best candidate
                eval_df = evaluator.evaluate(xs)
                target_values = eval_df[target].to_list()

                # Constraints values
                constraint_values = (
                    [list(t) for t in eval_df[constraint_symbols].rows()] if constraint_symbols is not None else None
                )

                if constraint_values is not None:
                    for candidate, loss_value, constraint_violations in zip(
                        candidates, target_values, constraint_values, strict=True
                    ):
                        optimizer.tell(candidate, loss_value, constraint_violations)
                else:
                    for candidate, loss_value in zip(candidates, target_values, strict=True):
                        optimizer.tell(candidate, loss_value)

            # Done, it is what it is
            msg = f"Recommendation found by {options.optimizer}."
            success = True

        except Exception as e:
            msg = str(f"{options.optimizer} failed. Possible reason: {e}")
            success = False

        result = {"recommendation": optimizer.provide_recommendation(), "message": msg, "success": success}

        return parse_ng_results(result, problem, evaluator)

    return solver
