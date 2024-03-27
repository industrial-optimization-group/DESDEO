"""Solver interfaces to the optimization routines found in nevergrad."""

from collections.abc import Callable
from concurrent import futures

import nevergrad as ng
import numpy as np
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
        def ng_evaluator(xs: np.array, target: str) -> float:
            return evaluator.evaluate(xs).to_dict(as_series=False)[target][0]

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

        try:
            if optimizer.num_workers > 1:
                # use several workers
                with futures.ThreadPoolExecutor(max_workers=optimizer.num_workers) as executor:
                    recommendation = optimizer.minimize(
                        lambda xs: ng_evaluator(xs, target=target), executor=executor, batch_mode=False, verbosity=2
                    )
            else:
                # just a single worker
                recommendation = optimizer.minimize(
                    lambda xs: ng_evaluator(xs, target=target),
                    constraint_violation=[
                        lambda xs, const=const: ng_evaluator(xs, target=const.symbol) for const in problem.constraints
                    ]
                    if problem.constraints is not None
                    else None,
                )

            msg = "Recommendation found by NgOpt."
            success = True
        except Exception as e:
            msg = str(f"NgOpt failed. Possible reason: {e}")
            success = False
        finally:
            if not success:
                recommendation = parametrization

        result = {"recommendation": recommendation, "message": msg, "success": success}

        return parse_ng_results(result, problem, evaluator)

    return solver
