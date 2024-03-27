"""Tests for the scipy solver interfaces."""
import pytest

from desdeo.problem import binh_and_korn
from desdeo.tools.scalarization import add_scalarization_function
from desdeo.tools.scipy_solver_interfaces import create_scipy_de_solver


def test_scipy_de_with_constraints():
    problem = binh_and_korn((False, False))

    problem, target = add_scalarization_function(problem, "1*f_2", "first")

    solver = create_scipy_de_solver(problem)

    res = solver(target)
