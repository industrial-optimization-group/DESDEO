"""Tests for the pyomo solver interfaces."""
import pytest

from desdeo.problem import binh_and_korn, momip_ti2
from desdeo.tools.pyomo_solver_interfaces import create_pyomo_bonmin_solver


@pytest.mark.slow
@pytest.mark.pyomo
def test_bonmin_solver():
    """Tests the bonmin solver."""
    problem = binh_and_korn()
    solver = create_pyomo_bonmin_solver(problem)

    results = solver("f_2")

    assert results.success


@pytest.mark.slow
@pytest.mark.pyomo
def test_bonmin_w_momip_ti2():
    """Test the bonmin solver with a known problem."""
    problem = momip_ti2()

    solver = create_pyomo_bonmin_solver(problem)

    results = solver("f_2")
