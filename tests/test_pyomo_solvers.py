"""Tests for the pyomo solver interfaces."""

import numpy.testing as npt
import numpy as np
import pytest

from desdeo.problem import binh_and_korn, momip_ti2, momip_ti17
from desdeo.tools.scalarization import add_scalarization_function
from desdeo.tools.pyomo_solver_interfaces import BonminOptions, create_pyomo_bonmin_solver


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

    results = solver("f_1")

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

    results = solver("f_2")

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

    solver = create_pyomo_bonmin_solver(problem_w_scal)

    results = solver(target)

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
def test_bonmin_w_momip_ti17():
    """TODO: Finish. Test the bonmin solver with a known problem."""
    problem = momip_ti17()

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-BB")
    solver = create_pyomo_bonmin_solver(problem, sol_options)

    results = solver("f_2_min")

    # check the result is Pareto optimal
    assert results.success
    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    # check constraints
    gs = results.constraint_values
    assert np.isclose(gs["g_1"], 0, atol=1e-8) or gs["g_1"] < 0
    assert np.isclose(gs["g_2"], 0, atol=1e-8) or gs["g_2"] < 0

    results = solver("f_2")

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

    solver = create_pyomo_bonmin_solver(problem_w_scal, options=sol_options)

    results = solver(target)

    # check the result is Pareto optimal
    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    # check constraints
    gs = results.constraint_values
    assert np.isclose(gs["g_1"], 0, atol=1e-8) or gs["g_1"] < 0
    assert np.isclose(gs["g_2"], 0, atol=1e-8) or gs["g_2"] < 0
