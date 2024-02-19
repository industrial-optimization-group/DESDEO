"""Solver interfaces to the optimization routines found in nevergrad."""
from collections.abc import Callable

import nevergrad as ng

from desdeo.problem import Problem
from desdeo.tools.generics import CreateSolverType, SolverError, SolverResults

# forward typehints
create_ng_ngopt_solver: CreateSolverType


def create_ng_ngopt_solver(problem: Problem) -> Callable[[str], SolverResults]:
    """Creates a solver that utilizes the `ng.optimizers.NGOpt` routine.

    Args:
        problem (Problem): _description_

    Returns:
        _type_: _description_
    """


if __name__ == "__main__":

    def square(x, y=12):
        return sum((x - 0.5) ** 2) + abs(y)

    optimizer = ng.optimizers.NGOpt(parametrization=2, budget=100)
    recommendation = optimizer.minimize(square)
    print(recommendation.value)
