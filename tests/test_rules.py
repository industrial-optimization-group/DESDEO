"""Tests for the rule extraction, instantiation, and parsing utilities."""

from dataclasses import dataclass

import numpy as np
import numpy.testing as npt
import pytest

from desdeo.explanations import (
    Rule,
    complete_bounds_from_population,
    extract_skoped_rules,
    instantiate_from_rules,
    instantiate_from_ruleset,
    parse_rules_to_variable_bounds,
)


@dataclass
class _DummyRule:
    """Mimics an `imodels` rule object."""

    agg_dict: Rule
    args: tuple


@dataclass
class _DummySkopeClassifier:
    """Mimics a trained `SkopeRulesClassifier`."""

    rules_: list[_DummyRule]


@pytest.fixture
def dummy_skope_classifier() -> _DummySkopeClassifier:
    """A dummy SkopeRulesClassifier with three hand-crafted rules and precisions."""
    rule_dicts: list[Rule] = [
        {("depth", "<"): "12.0", ("width", ">="): "9.5", ("thickness", ">"): "2.5"},
        {("depth", "<"): "0.2", ("width", ">="): "0.9", ("height", "<"): "0.1"},
        {("width", ">"): "8.0", ("height", "<="): "16.0"},
    ]
    precisions = [0.5, 0.3, 0.9]

    dummy_rules = [_DummyRule(agg_dict=rd, args=(p,)) for rd, p in zip(rule_dicts, precisions, strict=True)]
    return _DummySkopeClassifier(rules_=dummy_rules)


@pytest.mark.explanation_utils
def test_extract_skoped_rules(dummy_skope_classifier):
    """`extract_skoped_rules` returns the rule dicts and precisions of every rule."""
    rules, precisions = extract_skoped_rules(dummy_skope_classifier)

    assert len(rules) == len(precisions) == len(dummy_skope_classifier.rules_)

    for i, rule in enumerate(rules):
        assert rule == dummy_skope_classifier.rules_[i].agg_dict

    for i, precision in enumerate(precisions):
        npt.assert_almost_equal(precision, dummy_skope_classifier.rules_[i].args[0])


@pytest.mark.explanation_utils
def test_instantiate_from_rules_shape():
    """The shape of the instantiated samples matches the requested counts.

    Uses arbitrary, descriptive variable names to confirm the implementation
    does not depend on any naming convention.
    """
    variable_symbols = ["thickness", "width", "height", "depth"]
    bounds = [(0.0, 5.0), (0.0, 10.0), (0.0, 15.0), (0.0, 20.0)]
    rule: Rule = {("thickness", ">"): "1.0", ("width", "<="): "9.0"}

    samples = instantiate_from_rules(rule, variable_symbols=variable_symbols, variable_bounds=bounds, n_samples=1000)

    assert samples.shape == (1000, 4)


@pytest.mark.explanation_utils
def test_instantiate_from_rules_respects_bounds():
    """All sampled values lie within the variable box constraints, even when no rule applies."""
    variable_symbols = ["thickness", "width", "height", "depth"]
    bounds = [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0), (15.0, 20.0)]
    rule: Rule = {("thickness", ">"): "0.5"}

    samples = instantiate_from_rules(rule, variable_symbols=variable_symbols, variable_bounds=bounds, n_samples=500)

    for i, (lo, hi) in enumerate(bounds):
        assert np.all(samples[:, i] >= lo)
        assert np.all(samples[:, i] <= hi)


@pytest.mark.explanation_utils
def test_instantiate_from_rules_respects_rule_limits():
    """Rule-defined bounds tighten the sampling range for the affected variable."""
    rule: Rule = {("x_1", ">"): "2.5", ("x_1", "<="): "4.0"}
    variable_symbols = ["x_1"]
    bounds = [(0.0, 5.0)]

    samples = instantiate_from_rules(rule, variable_symbols=variable_symbols, variable_bounds=bounds, n_samples=1000)

    assert np.all(samples[:, 0] > 2.5)
    assert np.all(samples[:, 0] <= 4.0)


@pytest.mark.explanation_utils
def test_instantiate_from_rules_unknown_symbols_are_ignored():
    """Rule keys referring to unknown variable symbols are silently skipped."""
    variable_symbols = ["thickness"]
    bounds = [(0.0, 5.0)]
    # Only "thickness" is recognized; the "speed" key must not affect sampling.
    rule: Rule = {("thickness", ">"): "1.0", ("speed", "<="): "0.0"}

    samples = instantiate_from_rules(rule, variable_symbols=variable_symbols, variable_bounds=bounds, n_samples=200)

    assert samples.shape == (200, 1)
    assert np.all(samples[:, 0] > 1.0)


@pytest.mark.explanation_utils
def test_instantiate_from_ruleset_weighted():
    """Higher-weighted rules generate more samples than lower-weighted ones.

    Each rule constrains ``speed`` to a disjoint sub-range of ``[0, 3]`` so
    we can count how many samples each rule contributed by inspecting values.
    """
    rule_a: Rule = {("speed", "<="): "1.0"}
    rule_b: Rule = {("speed", ">"): "1.0", ("speed", "<="): "2.0"}
    rule_c: Rule = {("speed", ">"): "2.0", ("speed", "<="): "3.0"}
    weights = [0.5, 0.3, 0.9]
    variable_symbols = ["speed"]
    bounds = [(0.0, 3.0)]

    samples = instantiate_from_ruleset(
        rules_list=[rule_a, rule_b, rule_c],
        weights=weights,
        variable_symbols=variable_symbols,
        variable_bounds=bounds,
        n_samples=1000,
    )

    count_a = int(np.sum(samples[:, 0] <= 1.0))
    count_b = int(np.sum((samples[:, 0] > 1.0) & (samples[:, 0] <= 2.0)))
    count_c = int(np.sum(samples[:, 0] > 2.0))

    # Highest weight (rule_c) produces the most samples; lowest (rule_b) the fewest.
    assert count_c > count_a
    assert count_c > count_b
    assert count_a > count_b


@pytest.mark.explanation_utils
def test_instantiate_from_ruleset_ignores_negative_weights():
    """Rules paired with a negative weight are excluded from instantiation."""
    rule_a: Rule = {("x_1", ">"): "1.0"}
    rule_b: Rule = {("x_1", ">"): "2.0"}
    rule_c: Rule = {("x_1", ">"): "3.0"}
    weights = [0.5, -0.3, 0.9]
    variable_symbols = ["x_1"]
    bounds = [(0.0, 10.0)]

    samples_with_negative = instantiate_from_ruleset(
        rules_list=[rule_a, rule_b, rule_c],
        weights=weights,
        variable_symbols=variable_symbols,
        variable_bounds=bounds,
        n_samples=1000,
    )

    samples_only_positive = instantiate_from_ruleset(
        rules_list=[rule_a, rule_c],
        weights=[0.5, 0.9],
        variable_symbols=variable_symbols,
        variable_bounds=bounds,
        n_samples=1000,
    )

    # Dropping a negative-weight rule must yield the same number of samples as
    # if that rule had not been included at all.
    assert samples_with_negative.shape == samples_only_positive.shape


@pytest.mark.explanation_utils
def test_instantiate_from_ruleset_total_count():
    """Total samples across all rules is approximately ``n_samples``."""
    rule_a: Rule = {("x_1", ">"): "1.0"}
    rule_b: Rule = {("x_1", ">"): "2.0"}
    rule_c: Rule = {("x_1", ">"): "3.0"}
    weights = [0.5, 0.3, 0.9]
    variable_symbols = ["x_1"]
    bounds = [(0.0, 10.0)]
    n_samples = 1000

    samples = instantiate_from_ruleset(
        rules_list=[rule_a, rule_b, rule_c],
        weights=weights,
        variable_symbols=variable_symbols,
        variable_bounds=bounds,
        n_samples=n_samples,
    )

    npt.assert_allclose(samples.shape[0], n_samples, atol=5)


@pytest.mark.explanation_utils
def test_parse_rules_to_variable_bounds():
    """Parsed bounds contain entries for every variable with the tightest rule values."""
    rules: list[Rule] = [
        {("thickness", ">"): "1.0", ("width", "<="): "9.0"},
        {("thickness", ">"): "2.0"},
        {("height", "<="): "0.5"},
    ]
    accuracies = [0.6, 0.8, 0.7]
    variable_symbols = ["thickness", "width", "height"]
    bounds = [(0.0, 10.0), (0.0, 10.0), (0.0, 10.0)]

    parsed = parse_rules_to_variable_bounds(rules, accuracies, variable_symbols, bounds)

    for symbol in variable_symbols:
        assert symbol in parsed
        assert ">" in parsed[symbol]
        assert "<=" in parsed[symbol]

    # thickness ">" should adopt the tighter bound 2.0 (accuracy 0.8 wins over 0.6)
    assert parsed["thickness"][">"][0] == 2.0
    assert parsed["thickness"][">"][1] == 0.8

    # width "<=" comes from the only rule referencing it
    assert parsed["width"]["<="][0] == 9.0
    assert parsed["width"]["<="][1] == 0.6

    # height "<=" tightens to 0.5
    assert parsed["height"]["<="][0] == 0.5
    assert parsed["height"]["<="][1] == 0.7


@pytest.mark.explanation_utils
def test_parse_rules_missing_bound_gets_box_constraint():
    """Variables without a relevant rule fall back to the box constraint with accuracy ``-1``."""
    rules: list[Rule] = [{("x_1", ">"): "2.0"}]
    accuracies = [0.9]
    variable_symbols = ["x_1", "x_2"]
    bounds = [(-1.0, 5.0), (0.0, 7.0)]

    parsed = parse_rules_to_variable_bounds(rules, accuracies, variable_symbols, bounds)

    # x_1 has a rule for ">", but not for "<=" — that bound falls back to the box upper limit
    assert parsed["x_1"][">"][0] == 2.0
    assert parsed["x_1"][">"][1] == 0.9
    assert parsed["x_1"]["<="][0] == 5.0
    assert parsed["x_1"]["<="][1] == -1

    # x_2 has no rule at all
    assert parsed["x_2"][">"][0] == 0.0
    assert parsed["x_2"][">"][1] == -1
    assert parsed["x_2"]["<="][0] == 7.0
    assert parsed["x_2"]["<="][1] == -1


@pytest.mark.explanation_utils
def test_complete_bounds_from_population():
    """Bounds with accuracy ``-1`` are replaced by the population's per-variable extrema."""
    rules: list[Rule] = [{("thickness", ">"): "2.0"}]
    accuracies = [0.9]
    variable_symbols = ["thickness", "width"]
    bounds = [(0.0, 10.0), (0.0, 10.0)]

    parsed = parse_rules_to_variable_bounds(rules, accuracies, variable_symbols, bounds)

    population = np.array(
        [
            [3.0, 4.0],
            [4.0, 6.0],
            [5.0, 8.0],
        ]
    )

    completed = complete_bounds_from_population(parsed, population, variable_symbols)

    # thickness ">" was set by the rule (accuracy 0.9), should NOT be overwritten
    assert completed["thickness"][">"][0] == 2.0
    assert completed["thickness"][">"][1] == 0.9

    # thickness "<=" had accuracy -1, should be replaced with population max (5.0)
    assert completed["thickness"]["<="][0] == 5.0

    # width ">" had accuracy -1 → population min (4.0)
    assert completed["width"][">"][0] == 4.0
    # width "<=" had accuracy -1 → population max (8.0)
    assert completed["width"]["<="][0] == 8.0
