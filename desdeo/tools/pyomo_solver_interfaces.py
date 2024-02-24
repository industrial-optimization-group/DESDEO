"""Defines solver interfaces for pyomo."""
from collections.abc import Callable

import pyomo.environ as pyomo
from pyomo.opt.results.results_ import SolverResults as _pyomo_SolverResults

from desdeo.problem import Problem, PyomoEvaluator
from desdeo.tools.generics import SolverResults, CreateSolverType


# forward typehints
create_pyomo_bonmin_solver: CreateSolverType


def parse_pyomo_optimizer_results(opt_res: _pyomo_SolverResults) -> SolverResults:
    """Parses pyomo SolverResults into DESDEO SolverResutls.

    Args:
        opt_res (_pyomo_SolverResults): the pyomo sovler results.

    Returns:
        SolverResults: desdeo solver results.
    """


def create_pyomo_bonmin_solver(problem: Problem) -> Callable[[str], SolverResults]:
    evaluator = PyomoEvaluator(problem)

    def solver(target: str) -> SolverResults:
        evaluator.set_optimization_target(target)

        opt = pyomo.SolverFactory("bonmin")
        opt_res = opt.solve(evaluator.model)

        opt_status = str(opt_res["Solver"][0]["Status"])
        opt_msg = str(opt_res["Solver"][0]["Message"])
        opt_term_condition = str(opt_res["Solver"][0]["Termination condition"])

        results = evaluator.get_values()

        return results

    return solver
