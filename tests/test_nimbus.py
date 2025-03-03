"""Tests related to the Synchronous NIMBUS method."""

import numpy as np
import numpy.testing as npt
import pytest

from desdeo.mcdm import (
    infer_classifications,
    solve_intermediate_solutions,
    solve_sub_problems,
)
from desdeo.problem import dtlz2, nimbus_test_problem, simple_data_problem
from desdeo.tools import (
    IpoptOptions,
    ProximalSolver,
    PyomoIpoptSolver,
    add_asf_diff,
    add_asf_nondiff,
)


@pytest.mark.nimbus
def test_solve_intermediate_solutions():
    """Tests that intermediate solutions are generated as expected."""
    # x_3 and x_4 must be 0.5
    problem = nimbus_test_problem()
    solution_1 = {"x_1": 0.0, "x_2": 3.0}
    solution_2 = {"x_1": 3.0, "x_2": 0.0}

    solver_options = IpoptOptions(tol=1e-8, max_iter=4000)

    num_desired = 5
    results = solve_intermediate_solutions(
        problem,
        solution_1,
        solution_2,
        num_desired,
        solver=PyomoIpoptSolver,
        solver_options=solver_options,
    )

    assert len(results) == num_desired

    for res in results:
        assert res.success
        assert all(obj.symbol in res.optimal_objectives for obj in problem.objectives)
        assert all(var.symbol in res.optimal_variables for var in problem.variables)


@pytest.mark.nimbus
def test_infer_classifications():
    """Test that classifications are inferred correctly."""
    problem = nimbus_test_problem()

    current_objectives = {"f_1": 4.5, "f_2": 3.2, "f_3": -5.2, "f_4": -1.2, "f_5": 120.0, "f_6": 9001.0}

    # f_1: improve until
    # f_2: keep as it is
    # f_3: improve without limit
    # f_4: let change freely
    # f_5: impair until
    # f_6: improve until
    reference_point = {"f_1": 6.9, "f_2": 3.2, "f_3": -6.0, "f_4": 2.0, "f_5": 160.0, "f_6": 9000.0}

    classifications = infer_classifications(problem, current_objectives, reference_point)

    # f_1: improve until
    assert classifications["f_1"][0] == "<="
    assert np.isclose(classifications["f_1"][1], reference_point["f_1"])

    # f_2: keep as it is
    assert classifications["f_2"][0] == "="
    assert classifications["f_2"][1] is None

    # f_3: improve without limit
    assert classifications["f_3"][0] == "<"
    assert classifications["f_3"][1] is None

    # f_4: let change freely
    assert classifications["f_4"][0] == "0"
    assert classifications["f_4"][1] is None

    # f_5: impair until
    assert classifications["f_5"][0] == ">="
    assert np.isclose(classifications["f_5"][1], reference_point["f_5"])

    # f_6: improve until
    assert classifications["f_6"][0] == "<="
    assert np.isclose(classifications["f_6"][1], reference_point["f_6"])


@pytest.mark.nimbus
def test_solve_discrete_sub_problems():
    """Test that the sub problems are solved correctly for a problem with a discrete representation."""
    problem = simple_data_problem()

    # get an initial point
    initial_ref_point = {"g_1": 1500, "g_2": 7.5, "g_3": -29.0}

    problem_w_sf, target = add_asf_nondiff(problem, "target", initial_ref_point)
    solver = ProximalSolver(problem_w_sf)
    initial_result = solver.solve(target)

    # {'g_1': 1406.25, 'g_2': 8.5, 'g_3': -37.5}
    initial_fs = initial_result.optimal_objectives

    ref_point = {"g_1": 2000.0, "g_2": 10.5, "g_3": -40.1}

    num_desired = 4

    solutions = solve_sub_problems(problem, initial_fs, ref_point, num_desired)

    assert len(solutions) == num_desired


@pytest.mark.nimbus
@pytest.mark.slow
def test_solve_sub_problems():
    """Test that the scalarization problems in NIMBUS are solved as expected."""
    n_variables = 8
    n_objectives = 3

    problem = dtlz2(n_variables, n_objectives)

    solver_options = IpoptOptions()

    # get some initial solution
    initial_rp = {"f_1": 0.4, "f_2": 0.3, "f_3": 0.8}
    problem_w_sf, target = add_asf_diff(problem, "target", initial_rp)
    solver = PyomoIpoptSolver(problem_w_sf, solver_options)
    initial_result = solver.solve(target)

    # f1: 0.4355, f2: 0.3355, f3: 0.8355
    initial_fs = initial_result.optimal_objectives

    # let f1 worsen until 0.6, keep f2, improve f3 until 0.6
    first_rp = {"f_1": 0.6, "f_2": initial_fs["f_2"], "f_3": 0.6}

    num_desired = 4
    solutions = solve_sub_problems(
        problem, initial_fs, first_rp, num_desired, solver=PyomoIpoptSolver, solver_options=solver_options
    )

    assert len(solutions) == num_desired

    # check that the solutions are Pareto optimal
    for solution in solutions:
        assert solution.success
        npt.assert_almost_equal(
            [solution.optimal_variables[f"x_{i+1}"] for i in range(n_objectives - 1, n_variables)], 0.5
        )
        npt.assert_almost_equal(
            sum(solution.optimal_objectives[f"{obj.symbol}"] ** 2 for obj in problem.objectives), 1.0
        )

    # check that solutions make sense
    for i, solution in enumerate(solutions):
        fs = solution.optimal_objectives

        # f1 should have worsened, but only until 0.6
        assert fs["f_1"] > initial_fs["f_1"]
        assert np.isclose(fs["f_1"], 0.6) or fs["f_1"] > 0.6

        # f2 should be same or better
        if i == 0:
            # NIMBUS scalarization, f_2 must be either as good or better
            assert np.isclose(fs["f_2"], initial_fs["f_2"]) or fs["f_2"] < initial_fs["f_2"]
        else:
            # other scalarization functions are more lenient, f2 is close to current point
            assert abs(fs["f_2"] - initial_fs["f_2"]) < 0.1

        # f3 should have improved
        assert fs["f_3"] < initial_fs["f_3"]


@pytest.mark.nimbus
def test_article_example():
    """Check that we get similar results for NIMBUS as in the original article.

    References:
         Miettinen, K., & Mäkelä, M. M. (2006). Synchronous approach in
            interactive multiobjective optimization. European Journal of Operational Research, 170(3), 909-922.


    """
    problem = nimbus_test_problem()

    # From Fig. 2
    starting_point = {
        "f_1": 5.437906,
        "f_2": 9.124742,
        "f_3": -4.669013,
        "f_4": -0.2192304,
        "f_5": 1582.05,
        "f_6": 1788.815,
    }

    # From Fig. 2
    """
    starting_classifications = {
        "f_1": (">=", 3.0),
        "f_2": ("<=", 4.0),
        "f_3": (">=", -3.0),
        "f_4": (">=", 1.0),
        "f_5": ("<", None),
        "f_6": ("<", None),
    }
    """

    starting_rp = {
        "f_1": 3.0,
        "f_2": 4.0,
        "f_3": -3.0,
        "f_4": 1.0,
        "f_5": problem.get_ideal_point()["f_5"],
        "f_6": problem.get_ideal_point()["f_6"],
    }

    num_desired_start = 2
    results = solve_sub_problems(
        problem,
        starting_point,
        starting_rp,
        num_desired_start,
        solver=PyomoIpoptSolver,
        solver_options=IpoptOptions(),
    )

    fs = results[0].optimal_objectives

    # f1 worsened until 3.0
    assert fs["f_1"] < starting_point["f_1"] and (np.isclose(fs["f_1"], 3.0) or fs["f_1"] > 3.0)

    # f2 improved until 4.0
    assert fs["f_2"] < starting_point["f_2"] and (np.isclose(fs["f_2"], 4.0) or fs["f_2"] > 4.0)

    # f3 worsened unti -3.0
    assert fs["f_3"] > starting_point["f_3"] and (np.isclose(fs["f_3"], -3.0) or fs["f_3"] < -3.0)

    # f4 worsened until 1.0
    assert fs["f_4"] > starting_point["f_4"] and (np.isclose(fs["f_4"], 1.0) or fs["f_3"] < 1.0)

    # f5 improved
    assert fs["f_5"] < starting_point["f_5"] or np.isclose(fs["f_5"], starting_point["f_5"])

    # f6 improved
    assert fs["f_6"] < starting_point["f_6"] or np.isclose(fs["f_6"], starting_point["f_6"])
