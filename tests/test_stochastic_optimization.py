"""Tests that scenario-based stochastic problems can actually be solved."""

import math

import pytest

from desdeo.problem.testproblems import simple_scenario_model
from desdeo.tools import guess_best_solver
from desdeo.tools.robust import add_weighted_scenarios, add_worst_case_robust
from desdeo.tools.scalarization import add_asf_diff
from desdeo.tools.scenarios import build_combined_scenario_problem
from desdeo.tools.stochastic import add_conditional_value_at_risk, add_expected_asf, add_expected_value

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
    assert "s_1_x_2" in result.optimal_variables
    assert "s_2_x_2" in result.optimal_variables
    assert "s_3_x_2" in result.optimal_variables


@pytest.mark.scenario
@pytest.mark.slow
def test_expected_asf_has_per_leaf_objective_values(solve_result):
    """The result contains a finite objective value for every per-leaf objective."""
    result, _ = solve_result
    objectives = result.optimal_objectives or {}
    leaf_obj_syms = [f"s_{i}_{f}" for i in (1, 2, 3) for f in ("f_1", "f_2", "f_3")]
    for sym in leaf_obj_syms:
        assert sym in objectives, f"Missing objective value for {sym}"
        assert math.isfinite(objectives[sym]), f"Non-finite value for {sym}: {objectives[sym]}"


@pytest.mark.scenario
@pytest.mark.slow
def test_expected_asf_optimal_scalarization_is_finite(solve_result):
    """The optimal value of the expected ASF scalarization is a finite number."""
    result, expected_symbol = solve_result
    value = (result.optimal_objectives or {}).get(expected_symbol) or (result.scalarization_values or {}).get(
        expected_symbol
    )
    assert value is not None
    assert math.isfinite(value)


# ---------------------------------------------------------------------------
# add_conditional_value_at_risk — solving tests
# ---------------------------------------------------------------------------


@pytest.fixture(name="cvar_asf_problem")
def cvar_asf_problem_fixture(model):
    """Combined problem with CVaR (alpha=0.95) of the per-leaf ASF scalarizations."""
    asf_base, scal = add_asf_diff(model.base_problem, "asf", _REF, ideal=_IDEAL, nadir=_NADIR)
    asf_model = model.with_base_problem(problem=asf_base)
    combined, symbol_maps = build_combined_scenario_problem(asf_model)
    return add_conditional_value_at_risk(asf_model, [scal], alpha=0.95, combined=combined, symbol_maps=symbol_maps)


@pytest.fixture(name="cvar_solve_result")
def cvar_solve_result_fixture(cvar_asf_problem):
    """Solve the CVaR-ASF problem and return (result, cvar_symbol)."""
    problem, added = cvar_asf_problem
    cvar_sym = added["asf"]
    solver_class = guess_best_solver(problem)
    solver = solver_class(problem)
    return solver.solve(cvar_sym), cvar_sym


@pytest.mark.scenario
@pytest.mark.slow
def test_cvar_asf_solves_successfully(cvar_solve_result):
    """The CVaR-ASF problem reports a successful solve."""
    result, _ = cvar_solve_result
    assert result.success


@pytest.mark.scenario
@pytest.mark.slow
def test_cvar_asf_value_is_finite(cvar_solve_result):
    """The optimal CVaR value is a finite number."""
    result, cvar_sym = cvar_solve_result
    value = (result.scalarization_values or {}).get(cvar_sym)
    assert value is not None
    assert math.isfinite(value)


@pytest.mark.scenario
@pytest.mark.slow
def test_cvar_asf_var_variables_in_result(cvar_solve_result):
    """The result contains the VaR threshold and per-leaf auxiliary variables."""
    result, _ = cvar_solve_result
    assert "VAR_asf" in result.optimal_variables
    assert "s_1_VAR_asf" in result.optimal_variables
    assert "s_2_VAR_asf" in result.optimal_variables
    assert "s_3_VAR_asf" in result.optimal_variables


@pytest.mark.scenario
@pytest.mark.slow
def test_cvar_asf_auxiliary_variables_nonnegative(cvar_solve_result):
    """The optimal auxiliary z_s variables satisfy z_s >= 0."""
    result, _ = cvar_solve_result
    for s in ("s_1", "s_2", "s_3"):
        assert result.optimal_variables[f"{s}_VAR_asf"] >= -1e-6


# ---------------------------------------------------------------------------
# add_worst_case_robust — solving tests
# ---------------------------------------------------------------------------


@pytest.fixture(name="robust_asf_problem")
def robust_asf_problem_fixture(model):
    """Combined problem with min-max robust ASF scalarization."""
    asf_base, scal = add_asf_diff(model.base_problem, "asf", _REF, ideal=_IDEAL, nadir=_NADIR)
    asf_model = model.with_base_problem(problem=asf_base)
    combined, symbol_maps = build_combined_scenario_problem(asf_model)
    return add_worst_case_robust(asf_model, [scal], combined=combined, symbol_maps=symbol_maps)


@pytest.fixture(name="robust_solve_result")
def robust_solve_result_fixture(robust_asf_problem):
    """Solve the min-max robust ASF problem and return (result, robust_symbol)."""
    problem, added = robust_asf_problem
    robust_sym = added["asf"]
    solver_class = guess_best_solver(problem)
    solver = solver_class(problem)
    return solver.solve(robust_sym), robust_sym


@pytest.mark.scenario
@pytest.mark.slow
def test_robust_asf_solves_successfully(robust_solve_result):
    """The min-max robust ASF problem reports a successful solve."""
    result, _ = robust_solve_result
    assert result.success


@pytest.mark.scenario
@pytest.mark.slow
def test_robust_asf_value_is_finite(robust_solve_result):
    """The optimal robust ASF value is a finite number."""
    result, robust_sym = robust_solve_result
    value = (result.scalarization_values or {}).get(robust_sym)
    assert value is not None
    assert math.isfinite(value)


@pytest.mark.scenario
@pytest.mark.slow
def test_robust_asf_has_shared_variable(robust_solve_result):
    """The result contains the shared (non-anticipative) variable x_1."""
    result, _ = robust_solve_result
    assert "x_1" in result.optimal_variables


# ---------------------------------------------------------------------------
# add_weighted_scenarios — solving tests
# ---------------------------------------------------------------------------

_LEAF_WEIGHTS = {"s_1": 0.5, "s_2": 0.3, "s_3": 0.2}


@pytest.fixture(name="weighted_asf_problem")
def weighted_asf_problem_fixture(model):
    """Combined problem with a user-weighted sum of the per-leaf ASF scalarizations."""
    asf_base, scal = add_asf_diff(model.base_problem, "asf", _REF, ideal=_IDEAL, nadir=_NADIR)
    asf_model = model.with_base_problem(problem=asf_base)
    combined, symbol_maps = build_combined_scenario_problem(asf_model)
    return add_weighted_scenarios(asf_model, [scal], weights=_LEAF_WEIGHTS, combined=combined, symbol_maps=symbol_maps)


@pytest.fixture(name="weighted_solve_result")
def weighted_solve_result_fixture(weighted_asf_problem):
    """Solve the weighted-ASF problem and return (result, weighted_symbol)."""
    problem, added = weighted_asf_problem
    weighted_sym = added["asf"]
    solver_class = guess_best_solver(problem)
    solver = solver_class(problem)
    return solver.solve(weighted_sym), weighted_sym


@pytest.mark.scenario
@pytest.mark.slow
def test_weighted_asf_solves_successfully(weighted_solve_result):
    """The weighted-ASF problem reports a successful solve.

    Regression test: the aggregated scalarization used to reference the per-leaf
    scalarization symbols instead of inlining their expressions, which no evaluator
    could resolve because all scalarization functions are computed in one pass.
    """
    result, _ = weighted_solve_result
    assert result.success


@pytest.mark.scenario
@pytest.mark.slow
def test_weighted_asf_value_is_finite(weighted_solve_result):
    """The optimal weighted ASF value is a finite number."""
    result, weighted_sym = weighted_solve_result
    value = (result.scalarization_values or {}).get(weighted_sym)
    assert value is not None
    assert math.isfinite(value)


@pytest.mark.scenario
@pytest.mark.slow
def test_weighted_asf_matches_expected_value_when_weights_are_probabilities(model):
    """With the scenario probabilities as weights, the result matches add_expected_value."""
    asf_base, scal = add_asf_diff(model.base_problem, "asf", _REF, ideal=_IDEAL, nadir=_NADIR)
    asf_model = model.with_base_problem(problem=asf_base)
    combined, symbol_maps = build_combined_scenario_problem(asf_model)

    weighted_problem, weighted_added = add_weighted_scenarios(
        asf_model,
        [scal],
        weights=asf_model.leaf_scenarios,
        combined=combined,
        symbol_maps=symbol_maps,
    )
    expected_problem, expected_added = add_expected_value(asf_model, [scal], combined=combined, symbol_maps=symbol_maps)

    weighted_sym, expected_sym = weighted_added["asf"], expected_added["asf"]
    weighted_value = guess_best_solver(weighted_problem)(weighted_problem).solve(weighted_sym)
    expected_value = guess_best_solver(expected_problem)(expected_problem).solve(expected_sym)

    assert weighted_value.success
    assert expected_value.success
    assert (weighted_value.scalarization_values or {})[weighted_sym] == pytest.approx(
        (expected_value.scalarization_values or {})[expected_sym], rel=1e-4
    )


@pytest.mark.scenario
@pytest.mark.slow
def test_weighted_asf_has_shared_variable(weighted_solve_result):
    """The result contains the shared (non-anticipative) variable x_1."""
    result, _ = weighted_solve_result
    assert "x_1" in result.optimal_variables
