"""Tests for the scipy solver interfaces."""

from desdeo.problem import binh_and_korn
from desdeo.tools.scalarization import add_scalarization_function
from desdeo.tools.scipy_solver_interfaces import ScipyDeSolver


def test_scipy_de_with_constraints():
    """Tests the scipy differential evolution solver with constraints."""
    problem = binh_and_korn((False, False))

    problem, target = add_scalarization_function(problem, "1*f_2", "first")

    solver = ScipyDeSolver(problem)

    res = solver.solve(target)
