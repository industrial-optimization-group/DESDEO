"""Solver interfaces to the optimization routines found in scipy.

These solvers can solve various scalarized problems of multiobjective optimization problems.
"""

from collections.abc import Callable
from enum import Enum

import numpy as np
from scipy.optimize import NonlinearConstraint
from scipy.optimize import OptimizeResult as _ScipyOptimizeResult
from scipy.optimize import differential_evolution as _scipy_de
from scipy.optimize import minimize as _scipy_minimize

from desdeo.problem import ConstraintTypeEnum, GenericEvaluator, Problem
from desdeo.tools.generics import SolverError, SolverResults


class EvalTargetEnum(str, Enum):
    """An enum that describe whether the evaluator target is an objective or a constraint."""

    objective = "objective"
    constraint = "constraint"


def get_variable_bounds_pairs(problem: Problem) -> list[tuple[float | int, float | int]]:
    """Returns the variable bounds defined in a Problem as a list of tuples.

    Args:
        problem (Problem): the problem with the variables of interest.

    Returns:
        list[tuple[float | int, float | int]]: a list of tuples, the first
            element of each tuple is the lower bound of a variable and the second
            its upper bound. Each tuple corresponds to a variable.
    """
    return [(variable.lowerbound, variable.upperbound) for variable in problem.variables]


def set_initial_guess(problem: Problem) -> list[float | int]:
    """Sets or gets the initial guess for each variable defined in a Problem.

    For variables without initial guess, the initial guess is set to be the middle point of said
    variable's lower and upper bound.

    Args:
        problem (Problem): the problem with the variables of which the initial values are of interest.

    Returns:
        list[float | int]: a list of numbers, each number represents the initial guess of each variable in the problem.
    """
    return [
        variable.initial_value
        if variable.initial_value is not None
        else ((variable.upperbound - variable.lowerbound) / 2 + variable.lowerbound)
        for variable in problem.variables
    ]


def create_scipy_dict_constraints(problem: Problem, evaluator: GenericEvaluator) -> dict:
    """Creates a dict with scipy compatible constraints.

    It is assumed that there are constraints defined in problem.

    Args:
        problem (Problem): the Problem with the constraints.
        evaluator (GenericEvaluator): the evaluator utilized to evaluate problem.

    Returns:
        dict: a dict with scipy compatible constraints.
    """
    return [
        {
            "type": "ineq" if constraint.cons_type == ConstraintTypeEnum.LTE else "eq",
            "fun": get_scipy_eval(problem, evaluator, constraint.symbol, eval_target=EvalTargetEnum.constraint),
        }
        for constraint in problem.constraints
    ]


def create_scipy_object_constraints(problem: Problem, evaluator: GenericEvaluator) -> list[NonlinearConstraint]:
    """Creates a list with scipy constraint object `NonLinearConstraints` used by some scipy routines.

    For more infor, see https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.NonlinearConstraint.html#scipy-optimize-nonlinearconstraint

    Args:
        problem (Problem): the problem with the original constraint to be utilized in creating the list of constraints.
        evaluator (GenericEvaluator): the evaluator corresponding to problem that can be used to evaluate
            the constraints.

    Returns:
        list[NonlinearConstraint]: a list of scipy's NonLinearConstraint objects.
    """
    return NonlinearConstraint(
        fun=get_scipy_eval(problem, evaluator, "", eval_target=EvalTargetEnum.constraint),
        lb=0,  # constraint value must be between 0 and inf, e.g., positive.
        ub=float("inf"),  # since in scipy, a constraint is respected when its value is positive. See scipy_eval.
    )


def get_scipy_eval(
    problem: Problem,
    evaluator: GenericEvaluator,
    target: str,
    eval_target: EvalTargetEnum,
) -> Callable[[list[float | int]], list[float | int]]:
    """Wraps the problem and evaluator into a callable function that can be used by scipy routines.

    The returned function expects an array-like argument, such as a numpy array or list.

    Args:
        problem (Problem): the problem being solved.
        evaluator (GenericEvaluator): the evaluator to evaluate the problem being solved.
        target (str): the symbol of the objective to of the optimization, defined in problem.
        eval_target (EvalTargetEnum): either objective or constraints. If objective,
            it is assumed that the evalution is about evaluating the objective function
            of the single-objective optimization problem being solved, e.g., a scalarization function
            defined in problem. If constraint, then the evalution is assumed to be about evaluating
            the constraints defined in problem.

    Returns:
      Callable[[list[float | int]], list[float | int]]: a function that takes as its argument
        an array like object.

    Note:
        Constraints in scipy are defined such that a positive number means the constraint
            is respected. In DESDEO, this is the opposite, e.g., a positive number means
            a constraint is breached. We take this into account when returning the
            constraint values, but this does not affect the constraint values computed
            for the true constraints.
    """

    def scipy_eval(x: list[float | int]) -> list[float | int]:
        """An evaluator to be used in scipy routines.

        Args:
            x (list[float  |  int]): an array like, such as a numpy array or list.append

        Raises:
            SolverError: when an invalid evaluator target is specified.

        Returns:
            list[float | int]: an array like.
        """
        # TODO: Consider caching the results of evaluator.evaluate
        evalutor_args = {problem.variables[i].symbol: x[i] for i in range(len(problem.variables))}

        if eval_target == EvalTargetEnum.objective:
            evaluator_res = evaluator.evaluate(evalutor_args)

            # evaluata objective (scalarized)
            return evaluator_res.to_dict(as_series=False)[target]

        if eval_target == EvalTargetEnum.constraint:
            evaluator_df = evaluator.evaluate(evalutor_args)
            # evaluate constraint
            # put the minus here because scipy expect positive constraints values when the constraint
            # is respected. But in DESDEO, we define constraints s.t., a negative value means the constraint
            # is recpected, therefore, it needs to be flipped here.
            con_symbols = [constraint.symbol for constraint in problem.constraints]
            res_dict = evaluator_df[con_symbols].to_dict(as_series=False)

            res = np.array([np.array(res_dict[symbol]) for symbol in con_symbols])

            # squeeze important for minimization routines
            return -np.squeeze(res, axis=-1) if res.shape[-1] == 1 else -res

        # non-existing eval_target
        msg = f"'eval_target' = '{eval_target} not supported. Must be one of {list(EvalTargetEnum)}."
        raise SolverError(msg)

    return scipy_eval


def parse_scipy_optimization_result(
    optimization_result: _ScipyOptimizeResult, problem: Problem, evaluator: GenericEvaluator
) -> SolverResults:
    """Parses the optimization results returned by various scipy methods.

    For documentation, see https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.OptimizeResult.html#scipy.optimize.OptimizeResult

    Args:
        optimization_result (_ScipyOptimizeResult): the optimization results.
        problem (Problem): the problem to which the optimization results correspond to.
        evaluator (GenericEvaluator): the evaluator that has been used in computing the optimization results.

    Returns:
        SolverResults: a pydantic dataclass with the relevant optimization results.
    """
    x_opt = optimization_result.x
    success_opt = optimization_result.success
    msg_opt = optimization_result.message

    eval_opt = evaluator.evaluate({problem.variables[i].symbol: x_opt[i] for i in range(len(problem.variables))})

    objective_symbols = [obj.symbol for obj in problem.objectives]
    f_res = eval_opt[objective_symbols]
    f_opt = {symbol: f_res[symbol][0] for symbol in objective_symbols}

    if problem.constraints is not None:
        const_symbols = [const.symbol for const in problem.constraints]
        const_res = eval_opt[const_symbols]
        const_opt = {symbol: const_res[symbol][0] for symbol in const_symbols}
    else:
        const_opt = None

    return SolverResults(
        optimal_variables={problem.variables[i].symbol: x_opt[i] for i in range(len(problem.variables))},
        optimal_objectives=f_opt,
        constraint_values=const_opt,
        success=success_opt,
        message=msg_opt,
    )


class ScipyMinimizeSolver:
    """Creates a scipy solver that utilizes the `minimization` routine."""

    def __init__(
        self,
        problem: Problem,
        initial_guess: dict[str, float | None] | None = None,
        method: str | None = None,
        method_kwargs: dict | None = None,
        tol: float | None = None,
        options: dict | None = None,
    ):
        """Initializes a solver that utilizes the `scipy.optimize.minimize` routine.

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
            method_kwargs (dict | None, optional): the keyword arguments passed to
                the scipy.optimize.minimize method. Defaults to None.
            tol (float | None, optional): the tolerance for termination. Defaults to None.
            subscriber (str | None, optional): not used right now. WIP. Defaults to None.

        """
        self.problem = problem
        self.method = method
        self.method_kwargs = method_kwargs
        self.tol = tol
        self.options = options

        # variables bounds as (min, max pairs)
        self.bounds = get_variable_bounds_pairs(problem)

        # the initial guess as a simple sequence. If no initial value is set for some variable,
        # then the initial value defaults to middle of the upper and lower bounds.
        if initial_guess is not None:
            self.initial_guess = [initial_guess[var.symbol] for var in self.problem.variables]
        else:
            self.initial_guess = set_initial_guess(problem)

        self.evaluator = GenericEvaluator(problem)

        self.constraints = (
            create_scipy_dict_constraints(self.problem, self.evaluator)
            if self.problem.constraints is not None
            else None
        )

    def solve(self, target: str) -> SolverResults:
        """Solves the problem for a given target.

        Args:
            target (str): the sumbol of the objective function to be optimized.

        Returns:
            SolverResults: results of the optimization.
        """
        # add constraints if there are any

        optimization_result: _ScipyOptimizeResult = _scipy_minimize(
            get_scipy_eval(self.problem, self.evaluator, target, EvalTargetEnum.objective),
            self.initial_guess,
            method=self.method,
            bounds=self.bounds,
            constraints=self.constraints,
            options=self.options,
            tol=self.tol,
        )

        # pare and return the results
        return parse_scipy_optimization_result(optimization_result, self.problem, self.evaluator)


class ScipyDeSolver:
    """Creates a scipy solver that utilizes differential evolution."""

    def __init__(
        self,
        problem: Problem,
        initial_guess: dict[str, float | None] | None = None,
        de_kwargs: dict | None = None,
    ):
        """Creates a solver that utilizes the `scipy.optimize.differential_evolution` routine.

        The `scipy.optimize.differential_evolution` routine is fully accessible through this function.
        For additional details and explanation of some of the argumetns, see
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html

        Args:
            problem (Problem): the multiobjective optimization problem to be solved.
            initial_guess (dict[str, float, None] | None, optional): The initial
                guess to be utilized in the solver. For variables with a None as their
                initial guess, the mid-point of the variable's lower and upper bound is
                utilzied as the initial guess. If None, it is assumed that there are
                no initial guesses for any of the variables. Defaults to None.
            de_kwargs (dict | None, optional): custom keyword arguments to be forwarded to
                `scipy.optimize.differential_evolution`. Defaults to None.
            subscriber (str | None, optional): not used right now. WIP. Defaults to None.
        """
        self.problem = problem
        if de_kwargs is None:
            de_kwargs = {
                "strategy": "best1bin",
                "maxiter": 1000,
                "popsize": 15,
                "tol": 0.01,
                "mutation": (0.5, 1),
                "recombination": 0.7,
                "seed": None,
                "callback": None,
                "disp": False,
                "polish": True,
                "init": "latinhypercube",
                "atol": 0,
                "updating": "deferred",
                "workers": 1,
                "integrality": None,
                "vectorized": True,  # the constraints for scipy_de need to be fixed first for this to work
            }
        self.de_kwargs = de_kwargs

        # variable bounds
        self.bounds = get_variable_bounds_pairs(problem)

        # initial guess. If no guess is present for a variable, said variable's mid point of its
        # lower abd upper bound is used instead
        if initial_guess is None:
            self.initial_guess = set_initial_guess(problem)
        else:
            self.initial_guess = initial_guess

        self.evaluator = GenericEvaluator(problem)
        self.constraints = (
            create_scipy_object_constraints(self.problem, self.evaluator)
            if self.problem.constraints is not None
            else ()
        )

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for a given target.

        Args:
            target (str): the symbol of the objective function to be optimized.

        Returns:
            SolverResults: results of the optimization.
        """
        # add constraints if there are any

        optimization_result: _ScipyOptimizeResult = _scipy_de(
            get_scipy_eval(self.problem, self.evaluator, target, EvalTargetEnum.objective),
            bounds=self.bounds,
            x0=self.initial_guess,
            constraints=self.constraints,
            **self.de_kwargs,
        )

        # parse the results
        return parse_scipy_optimization_result(optimization_result, self.problem, self.evaluator)
