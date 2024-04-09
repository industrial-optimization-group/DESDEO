"""Tests related to the Synchronous NIMBUS method."""

import numpy as np
import pytest

from desdeo.mcdm import infer_classifications, solve_intermediate_solutions, solve_sub_problems
from desdeo.problem import nimbus_test_problem
from desdeo.tools import IpoptOptions, create_pyomo_ipopt_solver


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
        create_solver=create_pyomo_ipopt_solver,
        solver_options=solver_options,
    )

    assert len(results) == num_desired

    for res in results:
        assert all(obj.symbol in res for obj in problem.objectives)
        assert all(var.symbol in res for var in problem.variables)


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
