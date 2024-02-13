"""Here various solved interfaces to Python-based solvers are defined."""

from enum import Enum
from typing import Callable

from scipy.optimize import minimize as _scipy_minimize
from scipy.optimize import OptimizeResult as _ScipyOptimizeResult
from pydantic import BaseModel, Field

from desdeo.problem import ConstraintTypeEnum, EvaluatorResult, GenericEvaluator, Problem
from desdeo.tools.scalarization import create_from_objective, add_scalarization_function


class SolverError(Exception):
    """Raised when an error with a solver is encountered."""


class SolverResults(BaseModel):
    """Defines a schema for a dataclass to store the results of a sovler."""

    optimal_variables: dict[str, list[float]] = Field(description="The optimal decision variables found.")
    optimal_objectives: dict[str, list[float]] = Field(
        description="The objective function values corresponding to the optimal decision variables found."
    )
    constraint_values: dict[str, list[float]] | None = Field(
        description=(
            "The constraint values of the problem. A negative value means the constraint is respected, "
            "a positive one means it has been breached."
        ),
        default=None,
    )
    success: bool = Field(description="A boolean flag indicating whether the optimization was successful or not.")
    message: str = Field(description="Description of the cause of termination.")


class EvalTargetEnum(str, Enum):
    """An enum that describe whether the evaluator target is an objective or a constraint."""

    objective = "objective"
    constraint = "constraint"


def create_scipy_minimize_solver(
    problem: Problem,
    initial_guess: dict[str, float | None] | None = None,
    method: str | None = None,
    method_kwargs: dict | None = None,
    tol: float | None = None,
    options: dict | None = None,
    subscriber: str | None = None,
) -> Callable[[str], SolverResults]:
    """Creates a solver that utilizes the `scipy.optimize.minimize` routine.

    The `scipy.optimize.minimze` routine is fully accessible through this function.
    For additional details and explanation of some of the argumetns, see
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html#scipy.optimize.minimize

    Args:
        problem (Problem): the multiobjective optimization problem to be solved.
        initial_guess (dict[str, float, None] | None, optional): The initial
            guess to be utilized in the solver. For variables with a None as their
            initial guess, the mid-point of the variable's lower and upper bound is
            utilzied as the initial guess. If None, it is assumed that there are
            no initial guesses for any of the variables. Defaults to None.
        method (str | None, optional): the scipy.optimize.minimize method to be
            used. If None, a method is selected automatically based on the
            properties of the objective (does it have constraints?). Defaults to
            None.
        method_options (dict | None, optional): the keyword arguments passed to
            the scipy.optimize.minimize mehtod. Defaults to None.
        tol (float | None, optional): the tolerance for termination. Defaults to None.
        subscriber (str | None, optional): not used right now. WIP. Defaults to None.

    Raises:
        SolverError: if an evaluation target is not found.

    Returns:
        Callable[[str], SolverResults]: results a callable function that can be
            called with a target specifying the scalarization function to be used as
            the objective of the single-objective optimization.
    """
    # variables bounds as (min, max pairs)
    bounds = [(variable.lowerbound, variable.upperbound) for variable in problem.variables]

    # the initial guess as a simple sequence. If no initial value is set for some variable,
    # then the initial value defaults to middle of the upper and lower bounds.
    x0 = [
        variable.initial_value
        if variable.initial_value is not None
        else ((variable.upperbound - variable.lowerbound) / 2 + variable.lowerbound)
        for variable in problem.variables
    ]

    evaluator = GenericEvaluator(problem)

    def solver(target: str) -> SolverResults:
        def scipy_eval(
            x: list[float],
            problem=problem,
            evaluator=evaluator,
            target: str = target,
            eval_target: EvalTargetEnum = EvalTargetEnum.objective,
        ) -> list[float | int]:
            evalutor_args = {problem.variables[i].symbol: x[i] for i in range(len(problem.variables))}

            evaluator_res: EvaluatorResult = evaluator.evaluate(evalutor_args)

            if eval_target == EvalTargetEnum.objective:
                return evaluator_res.scalarization_values[target]

            if eval_target == EvalTargetEnum.constraint:
                # put the minus here because scipy expect positive constraints values when the constraint
                # is respected. But in DESDEO, we define constraints s.t., a negative value means the constraint
                # is recpected, therefore, it needs to be flipped here.
                return [-num for num in evaluator_res.constraint_values[target]]

            msg = f"'eval_target' = '{eval_target} not supported. Must be one of {list(EvalTargetEnum)}."
            raise SolverError(msg)

        if problem.constraints is not None:
            # add constraints
            constraints = [
                {
                    "type": "ineq" if constraint.cons_type == ConstraintTypeEnum.LTE else "eq",
                    "fun": lambda x, target=constraint.symbol, eval_target=EvalTargetEnum.constraint: scipy_eval(
                        x, target=target, eval_target=eval_target
                    ),
                }
                for constraint in problem.constraints
            ]

        else:
            # no constraints
            constraints = None

        optimization_result: _ScipyOptimizeResult = _scipy_minimize(
            lambda x, target=target: scipy_eval(x, target=target),
            x0,
            method=method,
            bounds=bounds,
            constraints=constraints,
            options=options,
            tol=tol,
        )

        # grab the results
        x_opt = optimization_result.x
        success_opt = optimization_result.success
        msg_opt = optimization_result.message

        eval_opt = evaluator.evaluate({problem.variables[i].symbol: x_opt[i] for i in range(len(problem.variables))})

        f_opt = eval_opt.objective_values

        if constraints is not None:
            const_opt = eval_opt.constraint_values

        return SolverResults(
            optimal_variables={problem.variables[i].symbol: [x_opt[i]] for i in range(len(problem.variables))},
            optimal_objectives=f_opt,
            constraint_values=const_opt,
            success=success_opt,
            message=msg_opt,
        )

    return solver


if __name__ == "__main__":
    from desdeo.problem import binh_and_korn

    problem = binh_and_korn()

    sf = create_from_objective(problem, "f_1")

    problem, target = add_scalarization_function(problem, sf, "target")

    solver = create_scipy_minimize_solver(problem)

    res = solver(target)
    print(res)
