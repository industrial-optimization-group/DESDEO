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
create_pyomo_gurobi_solver: CreateSolverType


@dataclass
class BonminOptions:
    """Defines a dataclass to store and pass options to the Bonmin solver.

    Because Bonmin utilizes many sub-solver, the options specific to Bonmin
    must be prefixed in their name with 'bonmin.{option_name}',
    e.g., `bonmin.integer_tolerance`. For a list of options, see
    https://www.coin-or.org/Bonmin/options_list.html

    Note:
        Please add options as they are needed and make a pull request.
    """

    tol: float = 1e-8
    """Sets the convergence tolerance of ipopt. Defaults to 1e-8."""

    bonmin_integer_tolerance: float = 1e-6
    """Numbers within this value of an integer are considered integers. Defaults to 1e-6."""

    bonmin_algorithm: str = "B-BB"
    """Presets some of the options in Bonmin based on the algorithm choice. Defaults to 'B-BB'.
    A good first option to try is 'B-Hyb'.
    """

    def asdict(self) -> dict[str, float]:
        """Converts the dataclass in a dict so that Bonmin specific options are in the correct format.

        This means that the attributes starting with `bonmin.optionname` will be
        converted to keys in the format `bonmin_optionname` in the returned dict.
        """
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

        # set solver options
        for key, value in options.asdict().items():
            opt.options[key] = value
        opt_res = opt.solve(evaluator.model)

        return parse_pyomo_optimizer_results(opt_res, problem, evaluator)

    return solver

def create_pyomo_gurobi_solver(
    problem: Problem, options: dict = dict()
) -> Callable[[str], SolverResults]:
    """Creates a pyomo solver that utilizes gurobi. You need to have gurobi
    installed on your system for this to work.

    Suitable for solving mixed-integer linear and quadratic optimization 
    problems.

    Args:
        problem (Problem): the problem to be solved.
        options (GurobiOptions): Dictionary of Gurobi parameters to set.
            This is passed to pyomo as is, so it works the same as options
            would for calling pyomo SolverFactory directly.

    Returns:
        Callable[[str], SolverResults]: returns a callable function that takes
            as its argument one of the symbols defined for a function expression in
            problem.
    """
    evaluator = PyomoEvaluator(problem)

    def solver(target: str) -> SolverResults:
        evaluator.set_optimization_target(target)

        opt = pyomo.SolverFactory('gurobi', solver_io='python', options=options)

        # set solver options
        #for key, value in options.asdict().items():
        #    opt.options[key] = value

        with pyomo.SolverFactory(
            'gurobi', solver_io='python'
        ) as opt:
            opt_res = opt.solve(evaluator.model)
            return parse_pyomo_optimizer_results(opt_res, problem, evaluator)

    return solver