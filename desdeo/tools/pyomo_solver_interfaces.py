"""Defines solver interfaces for pyomo."""

from collections.abc import Callable
from dataclasses import fields, dataclass

import pyomo.environ as pyomo
from pyomo.opt import SolverResults as _pyomo_SolverResults
from pyomo.opt import SolverStatus as _pyomo_SolverStatus
from pyomo.opt import TerminationCondition as _pyomo_TerminationCondition

from desdeo.problem import Problem, PyomoEvaluator
from desdeo.tools.generics import SolverResults, CreateSolverType


# forward typehints
create_pyomo_bonmin_solver: CreateSolverType


@dataclass
class BonminOptions:
    """Defines a dataclass to store and pass options to the Bonmin solver.

    Because Bonmin utilizes many sub-solver, the options specific to Bonmin
    must be prefixed in their name with 'bonmin.{option_name}',
    e.g., `bonmin.integer_tolerance`. For a list of options, see
    https://www.coin-or.org/Bonmin/options_list.html

    Note:
        Add options as they are needed.
    """

    tol: float = 1e-8
    """Sets the convergence tolerance of ipopt. Defaults to 1e-8."""

    bonmin_integer_tolerance: float = 1e-6
    """Numbers within this value of an integer are considered integers. Defaults to 1e-6."""

    def asdict(self) -> dict[str, float]:
        """Converts the dataclass in a dict so that Bonmin specific options are in the correct format."""
        output = {}
        for field in fields(self):
            if (rest := field.name.split(sep="_"))[0] == "bonmin":
                output[f"bonmin.{'_'.join(rest[1:])}"] = getattr(self, field.name)
            else:
                output[f"{field.name}"] = getattr(self, field.name)

        return output


_default_bonmin_options = BonminOptions()
"""Defines Bonmin options with the default values."""


def parse_pyomo_optimizer_results(
    opt_res: _pyomo_SolverResults, problem: Problem, evaluator: PyomoEvaluator
) -> SolverResults:
    """Parses pyomo SolverResults into DESDEO SolverResutls.

    Args:
        opt_res (_pyomo_SolverResults): the pyomo solver results.
        problem (Problem): the problem being solved.
        evaluator (PyomoEvaluator): the evalutor utilized to get the pyomo solver results.

    Returns:
        SolverResults: DESDEO solver results.
    """
    results = evaluator.get_values()

    variable_values = {var.symbol: results[var.symbol] for var in problem.variables}
    objective_values = {obj.symbol: results[obj.symbol] for obj in problem.objectives}
    constraint_values = {con.symbol: results[con.symbol] for con in problem.constraints}
    success = (
        opt_res.solver.status == _pyomo_SolverStatus.ok
        and opt_res.solver.termination_condition == _pyomo_TerminationCondition.optimal
    )
    msg = (
        f"Pyomo solver status is: '{opt_res.solver.status}', with termination condition: "
        f"'{opt_res.solver.termination_condition}'."
    )

    return SolverResults(
        optimal_variables=variable_values,
        optimal_objectives=objective_values,
        constraint_values=constraint_values,
        success=success,
        message=msg,
    )


def create_pyomo_bonmin_solver(
    problem: Problem, options: BonminOptions = _default_bonmin_options
) -> Callable[[str], SolverResults]:
    """Creates a pyomo solver that utilizes bonmin.

    Suitable for mixed-integer problems. The objective function being minimized
    (target) and the constraint functions must be twice continuously
    differentiable. When the objective functions and constraints are convex, the
    solution is exact. When the objective or any of the constraints, or both,
    are non-convex, then the solution is based on heuristics.

    Bonmin must be installed on the system running DESDEO, and its executable
    must be defined in the PATH.

    For more info about bonmin, see: https://www.coin-or.org/Bonmin/

    Args:
        problem (Problem): the problem to be solved.
        options (BonminOptions): options to be passed to the Bonmin solver.
            Defaults to `default_bonmin_options` defined in this source
            file.

    Returns:
        Callable[[str], SolverResults]: returns a callable function that takes
            as its argument one of the symbols defined for a function expression in
            problem.
    """
    evaluator = PyomoEvaluator(problem)

    def solver(target: str) -> SolverResults:
        evaluator.set_optimization_target(target)

        opt = pyomo.SolverFactory("bonmin", tee=True)
        # OBS! 'tol' is passes to ipopt, while bonmin options must be
        # prefixed with bonmin. see for a list of options: https://www.coin-or.org/Bonmin/options_list.html
        # opt.set_options("bonmin.integer_tolerance=1e-4")
        # TODO: create a dataclass to pass options to bonmin
        # set solver options
        for key, value in options.asdict().items():
            opt.options[key] = value
        opt_res = opt.solve(evaluator.model)

        return parse_pyomo_optimizer_results(opt_res, problem, evaluator)

    return solver
