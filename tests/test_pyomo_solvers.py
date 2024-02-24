"""Tests for the pyomo solver interfaces."""
import pytest

from desdeo.problem import binh_and_korn
from desdeo.tools.pyomo_solver_interfaces import create_pyomo_bonmin_solver


@pytest.mark.slow
@pytest.mark.pyomo
def test_bonmin_solver():
    """Tests the bonmin solver."""
    problem = binh_and_korn()
    solver = create_pyomo_bonmin_solver(problem)

    results = solver("f_2")
