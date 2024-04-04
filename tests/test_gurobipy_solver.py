"""Tests for the gurobipy solver."""

import numpy as np

import pytest

from desdeo.problem import (
    simple_linear_test_problem
)

from desdeo.tools import (
    create_gurobipy_solver
)

@pytest.mark.slow
@pytest.mark.gurobipy
def test_gurobi_solver():
    """Tests the bonmin solver."""
    problem = simple_linear_test_problem()
    solver = create_gurobipy_solver(problem)

    results = solver("f_1")

    assert results.success
    
    xs = results.optimal_variables
    assert np.isclose(xs["x_1"], 4.2, atol=1e-8)
    assert np.isclose(xs["x_2"], 2.1, atol=1e-8)