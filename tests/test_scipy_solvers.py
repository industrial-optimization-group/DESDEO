"""Tests for the scipy solver interfaces."""

import pytest

from desdeo.problem import ScalarizationFunction
from desdeo.problem.testproblems import binh_and_korn
from desdeo.tools.scipy_solver_interfaces import ScipyDeSolver


@pytest.mark.scipy
def test_scipy_de_with_constraints():
    """Tests the scipy differential evolution solver with constraints."""
    problem = binh_and_korn((False, False))

    target = "first"
    problem = problem.add_scalarization(
        ScalarizationFunction(
            name=target,
            symbol=target,
            func="1*f_2",
            is_linear=problem.is_linear,
            is_convex=problem.is_convex,
            is_twice_differentiable=problem.is_twice_differentiable,
        )
    )

    solver = ScipyDeSolver(problem)

    solver.solve(target)
