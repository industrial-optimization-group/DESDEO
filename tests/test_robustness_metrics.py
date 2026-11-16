"""Tests for the scenario robustness metrics in desdeo.tools.robustness_metrics."""

import pytest

from desdeo.tools.robustness_metrics import (
    antifragile_objectives,
    antifragility,
    domain_criterion,
)

pytestmark = pytest.mark.scenario

MIN_OUTCOMES = {
    "A": {"a": {"f": 1.0}, "b": {"f": 4.0}},
    "B": {"a": {"f": 3.0}, "b": {"f": 2.0}},
    "C": {"a": {"f": 5.0}, "b": {"f": 2.0}},
}


def test_unknown_objective_raises():
    """Objectives without a direction are rejected."""
    with pytest.raises(ValueError):
        domain_criterion(MIN_OUTCOMES, {"g": False}, {})


def test_domain_criterion_directions_and_missing():
    """Thresholds are direction-aware and missing entries are not counted."""
    outcomes = {
        "A": {"a": {"f": 1.0, "g": 5.0}, "b": {"f": 4.0, "g": 3.0}, "c": {"g": 4.0}},
        "B": {"a": {"f": 3.0, "g": 2.0}, "b": {"f": 2.0}},
    }
    res = domain_criterion(outcomes, {"f": False, "g": True}, {"f": 3.0, "g": 4.0})
    # f <= 3 counts, g >= 4 counts; the threshold itself is inside the domain.
    assert res["A"].counts == {"f": 1, "g": 2}
    assert res["B"].counts == {"f": 2, "g": 0}
    assert res["A"].mean_count == pytest.approx(1.5)
    assert res["B"].mean_count == pytest.approx(1.0)


def test_domain_criterion_partial_and_empty_thresholds():
    """Only thresholded objectives are counted; unknown threshold keys are rejected."""
    res = domain_criterion(MIN_OUTCOMES, {"f": False, "h": True}, {"f": 2.0})
    assert res["A"].counts == {"f": 1}
    assert res["C"].counts == {"f": 1}
    empty = domain_criterion(MIN_OUTCOMES, {"f": False}, {})
    assert empty["A"].counts == {}
    assert empty["A"].mean_count is None
    with pytest.raises(ValueError):
        domain_criterion(MIN_OUTCOMES, {"f": False}, {"x": 1.0})


def test_domain_criterion_all_count():
    """all_count counts the leaves where every thresholded objective meets its threshold."""
    outcomes = {"A": {"l1": {"f": 1.0, "g": 1.0}, "l2": {"f": 3.0, "g": 1.0}, "l3": {"f": 2.0, "g": 2.0}}}
    res = domain_criterion(outcomes, {"f": False, "g": False}, {"f": 2.0, "g": 2.0})
    assert res["A"].counts == {"f": 2, "g": 3}
    assert res["A"].all_count == 2


def test_domain_criterion_all_count_maximised():
    """A maximised objective meets its threshold at or above it."""
    outcomes = {"A": {"l1": {"h": 4.9}}, "B": {"l1": {"h": 5.0}}}
    res = domain_criterion(outcomes, {"h": True}, {"h": 5.0})
    assert res["A"].all_count == 0
    assert res["B"].all_count == 1


def test_domain_criterion_tolerance():
    """Values within the relative tolerance of a threshold meet it; values beyond it do not."""
    outcomes = {
        "A": {"l1": {"f": 4 + 1e-9, "h": 6 - 1e-9}},
        "B": {"l1": {"f": 4.01, "h": 5.99}},
    }
    res = domain_criterion(outcomes, {"f": False, "h": True}, {"f": 4.0, "h": 6.0})
    assert res["A"].counts == {"f": 1, "h": 1}
    assert res["A"].all_count == 1
    assert res["B"].counts == {"f": 0, "h": 0}
    assert res["B"].all_count == 0


def test_domain_criterion_all_count_missing():
    """A sparse leaf is judged on the objectives it has; a leaf the design lacks is not counted."""
    outcomes = {
        "A": {"l1": {"f": 1.0}, "l2": {"f": 1.0, "g": 1.0}},
        "B": {"l1": {"f": 1.0, "g": 1.0}},
    }
    res = domain_criterion(outcomes, {"f": False, "g": False}, {"f": 2.0, "g": 2.0})
    assert res["A"].counts == {"f": 2, "g": 1}
    assert res["A"].all_count == 2
    assert res["B"].all_count == 1


def test_domain_criterion_all_count_empty_thresholds():
    """Without thresholds no leaf is counted."""
    res = domain_criterion(MIN_OUTCOMES, {"f": False}, {})
    assert res["A"].all_count == 0
    assert res["A"].mean_count is None


# f is minimised, g is maximised. Per-leaf spreads (over A and B):
# f: base 2, s1 4, s2 2. g (min-space): base 0, s1 4, s2 1.
AF_OUTCOMES = {
    "A": {"base": {"f": 10.0, "g": 5.0}, "s1": {"f": 8.0, "g": 7.0}, "s2": {"f": 14.0, "g": 5.0}},
    "B": {"base": {"f": 12.0, "g": 5.0}, "s1": {"f": 12.0, "g": 3.0}, "s2": {"f": 12.0, "g": 6.0}},
}
AF_MAXIMIZE = {"f": False, "g": True}


def test_antifragility_minimised_objective():
    """Upside, downside and deviations for a minimised objective."""
    a = antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base")["A"].objectives["f"]
    assert a.upside == pytest.approx(0.5)
    assert a.downside == pytest.approx(2.0)
    assert a.antifragility == pytest.approx(-1.5 / 2.5)
    assert (a.n_gain, a.n_loss) == (1, 1)
    assert a.upside_raw == pytest.approx(2.0)
    assert a.downside_raw == pytest.approx(4.0)
    assert a.best_gain_leaf == "s1"
    assert a.worst_loss_leaf == "s2"
    assert a.worst_outcome == pytest.approx(14.0)
    assert a.taleb_class is None
    devs = {d.leaf: d for d in a.deviations}
    assert set(devs) == {"s1", "s2"}
    assert devs["s1"].improvement == pytest.approx(0.5)
    assert devs["s2"].improvement == pytest.approx(-2.0)
    assert devs["s2"].improvement_raw == pytest.approx(-4.0)
    assert devs["s2"].value == pytest.approx(14.0)
    assert devs["s1"].event_class == "gain"
    assert devs["s2"].event_class == "bounded_loss"


def test_antifragility_maximised_objective():
    """Upside, downside and deviations for a maximised objective."""
    res = antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base")
    a = res["A"].objectives["g"]
    assert a.upside == pytest.approx(0.5)
    assert a.downside == pytest.approx(0.0)
    assert a.antifragility == pytest.approx(1.0)
    assert (a.n_gain, a.n_loss) == (1, 0)
    assert a.worst_loss_leaf is None
    assert a.worst_outcome == pytest.approx(5.0)

    b = res["B"].objectives["g"]
    assert b.upside == pytest.approx(1.0)
    assert b.downside == pytest.approx(0.5)
    assert b.antifragility == pytest.approx(1 / 3)
    assert b.upside_raw == pytest.approx(1.0)
    assert b.downside_raw == pytest.approx(2.0)
    assert b.best_gain_leaf == "s2"
    assert b.worst_loss_leaf == "s1"
    assert b.worst_outcome == pytest.approx(3.0)
    devs = {d.leaf: d for d in b.deviations}
    assert devs["s1"].value == pytest.approx(3.0)
    assert devs["s1"].improvement_raw == pytest.approx(-2.0)
    assert devs["s2"].improvement_raw == pytest.approx(1.0)


def test_antifragility_unchanged_design():
    """A design that never deviates from its baseline has AF 0."""
    b = antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base")["B"].objectives["f"]
    assert (b.upside, b.downside, b.antifragility) == (0.0, 0.0, 0.0)
    assert (b.n_gain, b.n_loss) == (0, 0)
    assert b.best_gain_leaf is None
    assert b.worst_loss_leaf is None
    assert all(d.event_class == "untouched" for d in b.deviations)


def test_antifragility_mean_upside():
    """The mean upside averages the clipped gains over disrupted leaves."""
    outcomes = {
        "A": {"base": {"f": 4.0}, "s1": {"f": 2.0}, "s2": {"f": 3.0}},
        "B": {"base": {"f": 4.0}, "s1": {"f": 4.0}, "s2": {"f": 4.0}},
    }
    a = antifragility(outcomes, {"f": False}, "base", upside="mean")["A"].objectives["f"]
    # Normalised gains are 1 (s1) and 1 (s2).
    assert a.upside == pytest.approx(1.0)
    outcomes["A"]["s2"]["f"] = 5.0
    a = antifragility(outcomes, {"f": False}, "base", upside="mean")["A"].objectives["f"]
    # Gains are 1 (s1) and 0 (s2 is a loss).
    assert a.upside == pytest.approx(0.5)
    assert a.downside == pytest.approx(1.0)


def test_taleb_absolute_floors():
    """Absolute floors are direction-aware and inclusive at the boundary."""
    res = antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base", absolute_floors={"f": 13.0, "g": 3.0})
    assert res["A"].objectives["f"].taleb_class == "fragile"
    assert {d.leaf: d.event_class for d in res["A"].objectives["f"].deviations} == {"s1": "gain", "s2": "fragile"}
    assert res["B"].objectives["f"].taleb_class == "robust"
    # B's worst g is exactly the floor, which is not a violation.
    assert res["B"].objectives["g"].taleb_class == "antifragile"
    assert res["A"].objectives["g"].taleb_class == "antifragile"

    res = antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base", absolute_floors={"g": 3.5, "f": 14.0})
    assert res["B"].objectives["g"].taleb_class == "fragile"
    assert {d.leaf: d.event_class for d in res["B"].objectives["g"].deviations} == {"s1": "fragile", "s2": "gain"}
    assert res["A"].objectives["f"].taleb_class == "antifragile"


def test_taleb_absolute_floor_on_baseline():
    """Breaching an absolute floor in the baseline leaf makes a design fragile."""
    # The worst outcome includes the baseline leaf.
    res = antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base", absolute_floors={"f": 11.0})
    assert res["B"].objectives["f"].taleb_class == "fragile"
    assert all(d.event_class == "fragile" for d in res["B"].objectives["f"].deviations)


def test_taleb_loss_floors():
    """Loss floors are strict bounds on the largest raw loss."""
    res = antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base", loss_floors={"g": 2.0})
    assert res["B"].objectives["g"].taleb_class == "antifragile"
    assert res["A"].objectives["f"].taleb_class is None
    res = antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base", loss_floors={"g": 1.9})
    assert res["B"].objectives["g"].taleb_class == "fragile"
    assert {d.leaf: d.event_class for d in res["B"].objectives["g"].deviations} == {"s1": "fragile", "s2": "gain"}


def test_taleb_fragile_on_any_large_raw_loss():
    """A raw loss above the loss floor makes a design fragile even outside the worst normalised leaf."""
    outcomes = {
        "A": {"b": {"f": 0.0}, "s1": {"f": 1.0}, "s2": {"f": 4.0}},
        "B": {"b": {"f": 0.0}, "s1": {"f": -1.0}, "s2": {"f": -6.0}},
    }
    a = antifragility(outcomes, {"f": False}, "b", loss_floors={"f": 2.0})["A"].objectives["f"]
    # Normalised losses: s1 -1/2, s2 -4/10, so the worst normalised leaf s1 has raw loss 1 but s2 has 4.
    assert a.worst_loss_leaf == "s1"
    assert a.downside_raw == pytest.approx(1.0)
    assert a.max_loss_raw == pytest.approx(4.0)
    assert {d.leaf: d.event_class for d in a.deviations} == {"s1": "bounded_loss", "s2": "fragile"}
    assert a.taleb_class == "fragile"


def test_taleb_gain_tolerance():
    """Improvements within the tolerance are not gains."""
    outcomes = {
        "A": {"base": {"f": 1.0}, "s1": {"f": 1.0 - 1e-12}},
        "B": {"base": {"f": 1.0}, "s1": {"f": 2.0}},
    }
    a = antifragility(outcomes, {"f": False}, "base", loss_floors={"f": 10.0})["A"].objectives["f"]
    assert a.n_gain == 0
    assert a.taleb_class == "robust"
    assert a.deviations[0].event_class == "untouched"


def test_antifragility_zero_spread_and_missing():
    """Zero spread gives zero deviation; missing baselines give empty results."""
    outcomes = {
        "A": {"base": {"f": 1.0, "h": 2.0}, "s1": {"f": 1.0}, "s2": {"f": 3.0, "h": 1.0}},
        "B": {"base": {"f": 1.0}, "s1": {"f": 1.0}, "s2": {"f": 2.0, "h": 4.0}},
        "C": {"s1": {"f": 1.0}},
    }
    res = antifragility(outcomes, {"f": False, "h": False}, "base", missing="skip")
    a_f = res["A"].objectives["f"]
    # Leaf s1 has zero spread, so the deviation there is 0.
    assert {d.leaf: d.improvement for d in a_f.deviations} == {"s1": 0.0, "s2": pytest.approx(-2.0)}
    # h has a baseline for A only, and A has no h value in s1.
    a_h = res["A"].objectives["h"]
    assert [d.leaf for d in a_h.deviations] == ["s2"]
    assert a_h.upside == pytest.approx(1 / 3)
    b_h = res["B"].objectives["h"]
    assert b_h.deviations == []
    assert b_h.antifragility is None
    assert b_h.worst_outcome == pytest.approx(4.0)
    # C has no baseline at all but still appears.
    assert res["C"].objectives["f"].antifragility is None
    assert res["C"].objectives["f"].worst_outcome == pytest.approx(1.0)


def test_antifragility_shared_loss_with_zero_leaf_spread():
    """A loss all designs share in a leaf is normalised by the objective's spread over all leaves."""
    outcomes = {
        "A": {"base": {"f": 1.0}, "s1": {"f": 3.0}, "s2": {"f": 0.0}},
        "B": {"base": {"f": 2.0}, "s1": {"f": 3.0}, "s2": {"f": 1.0}},
    }
    res = antifragility(outcomes, {"f": False}, "base", loss_floors={"f": 1.0})
    a_f = res["A"].objectives["f"]
    # Leaf s1 has zero spread over the designs; f spans 0..3 over all leaves and designs.
    assert {d.leaf: d.improvement for d in a_f.deviations}["s1"] == pytest.approx(-2.0 / 3.0)
    assert a_f.n_loss == 1
    assert a_f.downside == pytest.approx(2.0 / 3.0)
    assert a_f.max_loss_raw == pytest.approx(2.0)
    assert a_f.taleb_class == "fragile"

    # With the same value everywhere there is nothing to normalise by, so the deviations are 0.
    flat = {"A": {"base": {"f": 1.0}, "s1": {"f": 1.0}}, "B": {"base": {"f": 1.0}, "s1": {"f": 1.0}}}
    assert antifragility(flat, {"f": False}, "base")["A"].objectives["f"].deviations[0].improvement == 0.0


def test_antifragility_errors():
    """Invalid baseline, floor keys and upside modes are rejected."""
    with pytest.raises(ValueError):
        antifragility(AF_OUTCOMES, AF_MAXIMIZE, "missing")
    with pytest.raises(ValueError):
        antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base", absolute_floors={"x": 1.0})
    with pytest.raises(ValueError):
        antifragility(AF_OUTCOMES, AF_MAXIMIZE, "base", upside="median")


def test_antifragile_objectives():
    """Only objectives with some positive upside are listed."""
    outcomes = {
        "A": {"base": {"f": 1.0, "h": 1.0}, "s1": {"f": 0.0, "h": 2.0}},
        "B": {"base": {"f": 1.0, "h": 1.0}, "s1": {"f": 1.0, "h": 1.0}},
    }
    res = antifragility(outcomes, {"f": False, "h": False}, "base")
    assert antifragile_objectives(res) == ["f"]


def test_parity_with_reference_formulas():
    """All metrics on a minimised example, with expected values derived by hand."""
    # Three designs, two minimised objectives, baseline "b0" and disruptions "s1", "s2".
    outcomes = {
        "A": {"b0": {"f": 2.0, "k": 10.0}, "s1": {"f": 4.0, "k": 6.0}, "s2": {"f": 1.0, "k": 12.0}},
        "B": {"b0": {"f": 3.0, "k": 8.0}, "s1": {"f": 2.0, "k": 9.0}, "s2": {"f": 3.0, "k": 8.0}},
        "C": {"b0": {"f": 6.0, "k": 9.0}, "s1": {"f": 6.0, "k": 7.0}, "s2": {"f": 2.0, "k": 10.0}},
    }
    maximize = {"f": False, "k": False}
    # Per-leaf best/spread: f: b0 2/4, s1 2/4, s2 1/2; k: b0 8/2, s1 6/3, s2 8/4.
    domain = domain_criterion(outcomes, maximize, {"f": 3.0, "k": 9.0})
    assert domain["A"].counts == {"f": 2, "k": 1}
    assert domain["B"].counts == {"f": 3, "k": 3}
    assert domain["C"].counts == {"f": 1, "k": 2}
    assert domain["C"].mean_count == pytest.approx(1.5)
    assert (domain["A"].all_count, domain["B"].all_count, domain["C"].all_count) == (0, 3, 0)

    af = antifragility(outcomes, maximize, "b0", absolute_floors={"f": 5.0}, loss_floors={"k": 2.5})
    # A f: s1 d = (2-4)/4 = -.5, s2 d = (2-1)/2 = .5 -> U .5, D .5, AF 0
    a_f = af["A"].objectives["f"]
    assert (a_f.upside, a_f.downside) == (pytest.approx(0.5), pytest.approx(0.5))
    assert a_f.antifragility == pytest.approx(0.0, abs=1e-8)
    assert a_f.taleb_class == "antifragile"
    # A k: s1 d = (10-6)/3 = 4/3, s2 d = (10-12)/4 = -.5 -> AF = (4/3-.5)/(4/3+.5); D_raw 2 <= 2.5
    a_k = af["A"].objectives["k"]
    assert a_k.antifragility == pytest.approx((4 / 3 - 0.5) / (4 / 3 + 0.5))
    assert a_k.downside_raw == pytest.approx(2.0)
    assert a_k.taleb_class == "antifragile"
    # B k: s1 d = (8-9)/3 = -1/3, s2 d = 0 -> AF -1, robust (D_raw 1, no gains)
    b_k = af["B"].objectives["k"]
    assert b_k.antifragility == pytest.approx(-1.0)
    assert b_k.taleb_class == "robust"
    # C f: worst outcome 6 > floor 5 -> fragile; s2 d = (6-2)/2 = 2
    c_f = af["C"].objectives["f"]
    assert c_f.taleb_class == "fragile"
    assert c_f.upside == pytest.approx(2.0)
    assert c_f.upside_raw == pytest.approx(4.0)
    # C k: s1 d = (9-7)/3 = 2/3, s2 d = (9-10)/4 = -.25 -> D_raw 1
    c_k = af["C"].objectives["k"]
    assert c_k.antifragility == pytest.approx((2 / 3 - 0.25) / (2 / 3 + 0.25))
    assert c_k.downside_raw == pytest.approx(1.0)
    assert c_k.taleb_class == "antifragile"


def test_antifragility_missing_worst():
    """B missing non-baseline leaf-b gets worst value 5.0 as a deviation; skip gives no deviation."""
    outcomes = {
        "A": {"a": {"f": 1.0}, "b": {"f": 3.0}},
        "B": {"a": {"f": 2.0}},
        "C": {"a": {"f": 4.0}, "b": {"f": 5.0}},
    }
    maximize = {"f": False}
    # B baseline=2.0, filled leaf-b=5.0; spread leaf-b=(5-3)=2; imp_raw=2-5=-3; imp=-3/2=-1.5
    res = antifragility(outcomes, maximize, baseline_leaf="a")
    dev = res["B"].objectives["f"].deviations[0]
    assert dev.leaf == "b"
    assert dev.value == pytest.approx(5.0)
    assert dev.improvement_raw == pytest.approx(-3.0)
    assert dev.improvement == pytest.approx(-1.5)
    assert res["B"].objectives["f"].worst_outcome == pytest.approx(5.0)
    # With skip, B has no non-baseline value -> no deviations, antifragility None
    res_skip = antifragility(outcomes, maximize, baseline_leaf="a", missing="skip")
    assert res_skip["B"].objectives["f"].deviations == []
    assert res_skip["B"].objectives["f"].antifragility is None


def test_antifragility_missing_worst_baseline():
    """B missing baseline leaf-a gets worst baseline 4.0, producing deviations; skip gives None."""
    outcomes = {
        "A": {"a": {"f": 1.0}, "b": {"f": 3.0}},
        "B": {"b": {"f": 2.0}},
        "C": {"a": {"f": 4.0}, "b": {"f": 5.0}},
    }
    maximize = {"f": False}
    # B baseline filled to 4.0 (worst of 1,4); leaf-b=2.0; spread leaf-b=(5-2)=3; imp_raw=4-2=2; imp=2/3
    res = antifragility(outcomes, maximize, baseline_leaf="a")
    dev = res["B"].objectives["f"].deviations[0]
    assert dev.leaf == "b"
    assert dev.improvement_raw == pytest.approx(2.0)
    assert res["B"].objectives["f"].worst_outcome == pytest.approx(4.0)
    # With skip, B's baseline is NaN -> no deviations, antifragility None
    res_skip = antifragility(outcomes, maximize, baseline_leaf="a", missing="skip")
    assert res_skip["B"].objectives["f"].antifragility is None


def test_missing_policy_invalid():
    """missing='drop' raises ValueError in antifragility."""
    outcomes = {"A": {"a": {"f": 1.0}}}
    maximize = {"f": False}
    with pytest.raises(ValueError, match="missing must be"):
        antifragility(outcomes, maximize, baseline_leaf="a", missing="drop")
