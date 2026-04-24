"""Tests that scenario-based stochastic problems can actually be solved."""

import pytest

from desdeo.problem.testproblems import simple_scenario_model
from desdeo.tools import guess_best_solver
from desdeo.tools.stochastic import add_expected_asf

_REF = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}
_IDEAL = {"f_1": -100.0, "f_2": -100.0, "f_3": -100.0}
_NADIR = {"f_1": 100.0, "f_2": 100.0, "f_3": 100.0}


@pytest.fixture(name="model")
def simple_model_fixture():
    """Return the simple_scenario_model test instance."""
    return simple_scenario_model()


@pytest.fixture(name="asf_problem")
def expected_asf_problem_fixture(model):
    """Return (combined_problem, expected_symbol) from add_expected_asf."""
    return add_expected_asf(model, "asf", _REF, ideal=_IDEAL, nadir=_NADIR)


@pytest.fixture(name="solve_result")
def solve_result_fixture(asf_problem):
    """Solve the combined expected ASF problem and return (result, expected_symbol)."""
    problem, expected_symbol = asf_problem
    solver_class = guess_best_solver(problem)
    solver = solver_class(problem)
    return solver.solve(expected_symbol), expected_symbol


@pytest.mark.scenario
@pytest.mark.slow
def test_expected_asf_solves_successfully(solve_result):
    """The combined expected ASF problem reports a successful solve."""
    result, _ = solve_result
    assert result.success


@pytest.mark.scenario
@pytest.mark.slow
def test_expected_asf_result_has_shared_variable(solve_result):
    """The result contains the shared (non-anticipative) variable x_1."""
    result, _ = solve_result
    assert "x_1" in result.optimal_variables


@pytest.mark.scenario
@pytest.mark.slow
def test_expected_asf_result_has_leaf_variables(solve_result):
    """The result contains per-leaf copies of x_2 for all three scenarios."""
    result, _ = solve_result
    assert "x_2_s_1" in result.optimal_variables
    assert "x_2_s_2" in result.optimal_variables
    assert "x_2_s_3" in result.optimal_variables


@pytest.mark.scenario
@pytest.mark.slow
def test_expected_asf_optimal_scalarization_is_finite(solve_result):
    """The optimal value of the expected ASF scalarization is a finite number."""
    import math

    result, expected_symbol = solve_result
    value = result.optimal_objectives.get(expected_symbol) or result.optimal_extras.get(expected_symbol)
    assert value is not None
    assert math.isfinite(value)
