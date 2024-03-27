"""Solver interfaces to the optimization routines found in nevergrad."""

from collections.abc import Callable

import nevergrad as ng
import polars as pl
from pydantic import BaseModel, Field

from desdeo.problem import GenericEvaluator, Problem
from desdeo.tools.generics import CreateSolverType, SolverResults

# forward typehints
create_ng_ngopt_solver: CreateSolverType


class NgOptOptions(BaseModel):
    """Defines options to be passed to nevergrad's NgOpt optimization routine."""

    budget: int | None = Field(description="The maximum number of allowed function evaluations.", default=100)
    """"The maximum number of allowed function evaluations. Defaults to 100."""

    num_workers: int | None = Field(description="The maximum number of allowed parallel evaluations.", default=1)
    """The maximum number of allowed parallel evaluations. Defaults to 1."""


_default_ng_ngopt_options = NgOptOptions()
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


def create_ng_ngopt_solver(
    problem: Problem, options: NgOptOptions = _default_ng_ngopt_options
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

        optimizer = ng.optimizers.NGOpt(parametrization=parametrization, **options.model_dump())

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
                evaluations = evaluator.evaluate(xs).with_columns(pl.arange(0, batch_size).alias("index"))

                # Find the row with the minimum target value
                min_row = evaluations.sort(target).head(1)

                # Retrieve the original index of the best candidate
                best_index = min_row["index"][0]

                # Constraints values
                if constraint_symbols is not None:
                    best_constraints = list(evaluations[constraint_symbols][best_index].rows()[0])
                else:
                    best_constraints = None
                best_candidate = candidates[best_index]

                optimizer.tell(best_candidate, evaluations[target][best_index], constraint_violation=best_constraints)

            # Done, it is what it is
            msg = "Recommendation found by NgOpt."
            success = True

        except Exception as e:
            msg = str(f"NgOpt failed. Possible reason: {e}")
            success = False

        result = {"recommendation": optimizer.provide_recommendation(), "message": msg, "success": success}

        return parse_ng_results(result, problem, evaluator)

    return solver
