"""Tests for the pyomo solver interfaces."""

import numpy as np
import numpy.testing as npt
import pytest

from desdeo.problem import (
    dtlz2,
    binh_and_korn,
    momip_ti2,
    momip_ti7,
    simple_linear_test_problem,
    simple_knapsack_vectors,
)
from desdeo.tools import (
    BonminOptions,
    PyomoBonminSolver,
    PyomoCBCSolver,
    PyomoIpoptSolver,
    PyomoGurobiSolver,
)
from desdeo.tools.scalarization import add_scalarization_function, add_asf_diff


@pytest.mark.slow
@pytest.mark.pyomo
def test_bonmin_solver():
    """Tests the bonmin solver."""
    problem = binh_and_korn()
    solver = PyomoBonminSolver(problem)

    results = solver.solve("f_2")

    assert results.success


@pytest.mark.slow
@pytest.mark.pyomo
def test_bonmin_w_momip_ti2():
    """Test the bonmin solver with a known problem."""
    problem = momip_ti2()

    solver = PyomoBonminSolver(problem)

    results = solver.solve("f_1")

    # check the result is Pareto optimal
    # optimal solutions: x_1^2 + x_^2 = 0.25 and (x_3, x_4) = {(0, -1), (-1, 0)}
    assert results.success
    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2, 0.25)
    assert (xs["x_3"], xs["x_4"]) in [(0, -1), (-1, 0)]

    # check constraints
    gs = results.constraint_values
    assert np.isclose(gs["g_1"], 0, atol=1e-8) or gs["g_1"] < 0
    assert np.isclose(gs["g_2"], 0, atol=1e-8) or gs["g_2"] < 0

    results = solver.solve("f_2")

    # check the result is Pareto optimal
    # optimal solutions: x_1^2 + x_^2 = 0.25 and (x_3, x_4) = {(0, -1), (-1, 0)}
    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2, 0.25)
    assert (xs["x_3"], xs["x_4"]) in [(0, -1), (-1, 0)]

    # check constraints
    gs = results.constraint_values
    assert np.isclose(gs["g_1"], 0, atol=1e-8) or gs["g_1"] < 0
    assert np.isclose(gs["g_2"], 0, atol=1e-8) or gs["g_2"] < 0

    # test with mixed objectives
    problem_w_scal, target = add_scalarization_function(problem, func="f_1_min + f_2_min", symbol="s_1")

    solver = PyomoBonminSolver(problem_w_scal)

    results = solver.solve(target)

    # check the result is Pareto optimal
    # optimal solutions: x_1^2 + x_^2 = 0.25 and (x_3, x_4) = {(0, -1), (-1, 0)}
    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2, 0.25)
    assert (xs["x_3"], xs["x_4"]) in [(0, -1), (-1, 0)]

    # check constraints
    gs = results.constraint_values
    assert np.isclose(gs["g_1"], 0, atol=1e-8) or gs["g_1"] < 0
    assert np.isclose(gs["g_2"], 0, atol=1e-8) or gs["g_2"] < 0


@pytest.mark.slow
@pytest.mark.pyomo
def test_bonmin_w_momip_ti7():
    """Finish. Test the bonmin solver with a known problem."""
    problem = momip_ti7()

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-BB")
    solver = PyomoBonminSolver(problem, sol_options)

    results = solver.solve("f_2_min")

    # check the result is Pareto optimal
    assert results.success
    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    # check constraints
    gs = results.constraint_values
    assert np.isclose(gs["g_1"], 0, atol=1e-8) or gs["g_1"] < 0
    assert np.isclose(gs["g_2"], 0, atol=1e-8) or gs["g_2"] < 0

    results = solver.solve("f_2")

    # check the result is Pareto optimal
    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    # check constraints
    gs = results.constraint_values
    assert np.isclose(gs["g_1"], 0, atol=1e-8) or gs["g_1"] < 0
    assert np.isclose(gs["g_2"], 0, atol=1e-8) or gs["g_2"] < 0

    # test with mixed objectives
    problem_w_scal, target = add_scalarization_function(
        problem, func="0.25*f_1_min + 0.25*f_2_min + 0.5*f_3_min", symbol="s_1"
    )

    solver = PyomoBonminSolver(problem_w_scal, options=sol_options)

    results = solver.solve(target)

    # check the result is Pareto optimal
    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    # check constraints
    gs = results.constraint_values
    assert np.isclose(gs["g_1"], 0, atol=1e-8) or gs["g_1"] < 0
    assert np.isclose(gs["g_2"], 0, atol=1e-8) or gs["g_2"] < 0


@pytest.mark.slow
@pytest.mark.pyomo
def test_gurobi_solver():
    """Tests the Gurobi solver."""
    problem = simple_linear_test_problem()
    solver = PyomoGurobiSolver(problem)

    results = solver.solve("f_1")

    assert results.success

    xs = results.optimal_variables
    assert np.isclose(xs["x_1"], 4.2, atol=1e-8)
    assert np.isclose(xs["x_2"], 2.1, atol=1e-8)


def test_ipopt_solver():
    """Tests that the Ipopt solver works as expected."""
    n_variables = 8
    n_objectives = 3
    problem = dtlz2(n_variables, n_objectives)

    rp = {"f_1": 0.4, "f_2": 0.7, "f_3": 0.5}

    problem_w_asf, target = add_asf_diff(problem, "target", rp)

    solver = PyomoIpoptSolver(problem_w_asf)

    result = solver.solve(target)

    xs = result.optimal_variables
    fs = result.optimal_objectives

    npt.assert_allclose([xs[f"x_{i+1}"] for i in range(n_objectives - 1, n_variables)], 0.5)
    npt.assert_almost_equal(sum(fs[obj.symbol] ** 2 for obj in problem.objectives), 1.0)


def test_combinatorial_problem():
    """Test that CBC can be used to solve a simple combinatorial problem."""
    problem = simple_knapsack_vectors()

    rp = {"f_1": 8, "f_2": 3}

    problem_w_asf, target = add_asf_diff(problem, "target", rp)

    solver = PyomoCBCSolver(problem_w_asf)

    result = solver.solve(target)

    assert result.success
