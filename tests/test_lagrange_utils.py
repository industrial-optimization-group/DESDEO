"""Tests for Lagrange multiplier utilities in desdeo.explanations.lagrange."""

import pytest

from desdeo.explanations.lagrange import (
    compute_tradeoffs,
    determine_active_objectives,
    filter_constraint_values,
    filter_lagrange_multipliers,
)


@pytest.mark.explanation_utils
def test_filter_multipliers_with_objective_symbols():
    """Filters raw multipliers down to one per objective using symbols."""
    raw = {
        "mu_f_1_upper": 0.5,
        "mu_f_1_eq": 0.3,
        "mu_f_2_upper": 0.8,
        "mu_f_2_eq": 0.1,
    }
    result = filter_lagrange_multipliers(raw, ["f_1", "f_2"])
    assert "f_1" in result
    assert "f_2" in result
    # Should prefer non-"eq" entries
    assert result["f_1"] == 0.5
    assert result["f_2"] == 0.8


@pytest.mark.explanation_utils
def test_filter_multipliers_without_symbols_uses_f_index():
    """Falls back to f_{index} pattern matching when no symbols provided."""
    raw = {
        "mu_f_0_upper": 1.0,
        "mu_f_0_eq": 0.5,
        "mu_f_1_upper": 2.0,
    }
    result = filter_lagrange_multipliers(raw, None)
    # Keys are the original constraint keys (preferred non-eq), plus f_{i} gap-fill entries
    assert result["mu_f_0_upper"] == 1.0
    assert result["mu_f_1_upper"] == 2.0


@pytest.mark.explanation_utils
def test_filter_multipliers_missing_objectives_get_zero():
    """Objectives not in the raw multipliers get 0.0."""
    raw = {"mu_f_1_upper": 0.5}
    result = filter_lagrange_multipliers(raw, ["f_1", "f_2", "f_3"])
    assert result["f_1"] == 0.5
    assert result["f_2"] == 0.0
    assert result["f_3"] == 0.0


@pytest.mark.explanation_utils
def test_filter_multipliers_empty_input():
    """Empty input returns empty dict (with zeros for symbols if given)."""
    result = filter_lagrange_multipliers({}, ["f_1"])
    assert result == {"f_1": 0.0}


@pytest.mark.explanation_utils
def test_filter_multipliers_prefers_non_eq_constraint():
    """When only eq entries exist, still returns them."""
    raw = {"mu_f_1_eq": 0.7}
    result = filter_lagrange_multipliers(raw, ["f_1"])
    assert result["f_1"] == 0.7


@pytest.mark.explanation_utils
def test_filter_multipliers_gap_in_f_indices_filled_with_zero():
    """When using f_{index} pattern and there's a gap, fills with 0."""
    raw = {"mu_f_0_upper": 1.0, "mu_f_2_upper": 3.0}
    result = filter_lagrange_multipliers(raw, None)
    # Should have original keys + gap-fill f_{i} entries for 0, 1, 2
    assert result["mu_f_0_upper"] == 1.0
    assert result["mu_f_2_upper"] == 3.0
    assert result.get("f_1", 0.0) == 0.0  # gap filled


@pytest.mark.explanation_utils
def test_filter_constraint_values_by_symbol():
    """Filters constraint values to one per objective, preferring non-eq."""
    raw = {"f_1_upper": -0.01, "f_1_eq": 0.0, "f_2_upper": -0.5}
    result = filter_constraint_values(raw, ["f_1", "f_2"])
    assert "f_1" in result
    assert "f_2" in result
    assert result["f_1"] == -0.01


@pytest.mark.explanation_utils
def test_filter_constraint_values_empty_input():
    """Empty input returns empty dict."""
    result = filter_constraint_values({}, ["f_1"])
    assert result == {}


@pytest.mark.explanation_utils
def test_tradeoffs_basic_computation():
    """Tradeoff[i][j] = -lambda_j / lambda_i for i != j, 1.0 on diagonal."""
    multipliers = {"f_1": 2.0, "f_2": 4.0, "f_3": 1.0}
    result = compute_tradeoffs(multipliers)
    assert result is not None

    # Diagonal
    assert result["f_1"]["f_1"] == 1.0
    assert result["f_2"]["f_2"] == 1.0

    # Off-diagonal: tradeoff[f_1][f_2] = -4.0 / 2.0 = -2.0
    assert result["f_1"]["f_2"] == pytest.approx(-2.0)
    # tradeoff[f_2][f_1] = -2.0 / 4.0 = -0.5
    assert result["f_2"]["f_1"] == pytest.approx(-0.5)


@pytest.mark.explanation_utils
def test_tradeoffs_zero_multiplier_handled():
    """Zero multiplier should not cause division by zero."""
    multipliers = {"f_1": 0.0, "f_2": 3.0}
    result = compute_tradeoffs(multipliers)
    assert result is not None
    # When lambda_i == 0, tradeoff[i][j] = 0.0 for j != i
    assert result["f_1"]["f_2"] == 0.0
    assert result["f_1"]["f_1"] == 1.0


@pytest.mark.explanation_utils
def test_tradeoffs_none_input():
    """None input returns None."""
    assert compute_tradeoffs(None) is None


@pytest.mark.explanation_utils
def test_tradeoffs_empty_input():
    """Empty dict returns None."""
    assert compute_tradeoffs({}) is None


@pytest.mark.explanation_utils
def test_tradeoffs_single_objective():
    """Single objective should return 1x1 matrix with diagonal = 1."""
    result = compute_tradeoffs({"f_1": 5.0})
    assert result == {"f_1": {"f_1": 1.0}}


@pytest.mark.explanation_utils
def test_active_objectives_from_constraint_values():
    """Active objectives are those with constraint value >= 0."""
    multipliers = [{"f_1": 1.0, "f_2": 0.5}]
    constraints = [{"f_1": 0.0, "f_2": -0.5}]  # f_1 active, f_2 not
    result = determine_active_objectives(multipliers, constraints, ["f_1", "f_2"])
    assert result == [["f_1"]]


@pytest.mark.explanation_utils
def test_active_objectives_from_multiplier_magnitude():
    """When no constraint values, use multiplier magnitude > threshold."""
    multipliers = [{"f_1": 1.0, "f_2": 1e-8, "f_3": 0.5}]
    result = determine_active_objectives(multipliers, None, ["f_1", "f_2", "f_3"], threshold=1e-5)
    assert result == [["f_1", "f_3"]]


@pytest.mark.explanation_utils
def test_active_objectives_none_multiplier_entry():
    """None in multipliers list produces empty active list."""
    result = determine_active_objectives([None, {"f_1": 1.0}], None, ["f_1"], threshold=1e-5)
    assert result[0] == []
    assert result[1] == ["f_1"]


@pytest.mark.explanation_utils
def test_active_objectives_no_symbols_uses_dict_keys():
    """Without objective_symbols, uses multiplier dict keys."""
    multipliers = [{"f_1": 1.0, "f_2": 0.0}]
    result = determine_active_objectives(multipliers, threshold=1e-5)
    assert result == [["f_1"]]


@pytest.mark.explanation_utils
def test_active_objectives_multiple_solutions():
    """Works with multiple solutions."""
    multipliers = [
        {"f_1": 1.0, "f_2": 0.5},
        {"f_1": 0.0, "f_2": 2.0},
    ]
    constraints = [
        {"f_1": 0.0, "f_2": 0.0},  # both active
        {"f_1": -1.0, "f_2": 0.0},  # only f_2 active
    ]
    result = determine_active_objectives(multipliers, constraints, ["f_1", "f_2"])
    assert result[0] == ["f_1", "f_2"]
    assert result[1] == ["f_2"]
