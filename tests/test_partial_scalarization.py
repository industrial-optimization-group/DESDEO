"""Tests for add_asf_partial_diff in desdeo.tools.partial_scalarization."""

import numpy as np
import numpy.testing as npt
import pytest

from desdeo.problem.testproblems import dtlz2, river_pollution_problem
from desdeo.tools.partial_scalarization import add_asf_partial_diff
from desdeo.tools.scalarization import ScalarizationError
from desdeo.tools.scipy_solver_interfaces import ScipyMinimizeSolver


def flatten(nested):
    """Recursively flatten a nested list."""
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


@pytest.fixture
def river():
    """River pollution problem (5 objectives: f_1, f_2 min; f_3, f_4 max; f_5 min)."""
    return river_pollution_problem()


@pytest.fixture
def dtlz2_4obj():
    """DTLZ2 with 5 variables and 4 objectives (all minimized, on unit sphere)."""
    return dtlz2(n_variables=5, n_objectives=4)


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_symbol_returned(river):
    """The returned symbol should match the one supplied."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    _, sym = add_asf_partial_diff(river, "partial_asf", rp, w)
    assert sym == "partial_asf"


@pytest.mark.scalarization
def test_only_active_objectives_in_scalarization(river):
    """Only the active objectives should appear in the scalarization expression and constraints."""
    active = {"f_1", "f_2"}
    inactive = {"f_3", "f_4", "f_5"}

    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    problem, sym = add_asf_partial_diff(river, "partial_asf", rp, w)

    scal_flat = flatten(problem.scalarization_funcs[-1].func)

    for sym_active in active:
        assert f"{sym_active}_min" in scal_flat
    for sym_inactive in inactive:
        assert f"{sym_inactive}_min" not in scal_flat


@pytest.mark.scalarization
def test_only_active_constraints_added(river):
    """Only one constraint per active objective should be added."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    n_original_constraints = len(river.constraints or [])

    problem, _ = add_asf_partial_diff(river, "partial_asf", rp, w)

    added_constraints = (len(problem.constraints or [])) - n_original_constraints
    assert added_constraints == len(rp)

    added_symbols = {c.symbol for c in (problem.constraints or [])}
    for obj_sym in rp:
        assert f"{obj_sym}_con" in added_symbols
    for obj_sym in {"f_3", "f_4", "f_5"}:
        assert f"{obj_sym}_con" not in added_symbols


@pytest.mark.scalarization
def test_reference_point_values_in_constraints(river):
    """Reference point component values should appear in the generated constraint expressions."""
    rp = {"f_1": -6.5, "f_2": -3.7}
    w = {"f_1": 2.0, "f_2": 0.5}
    problem, _ = add_asf_partial_diff(river, "partial_asf", rp, w)

    for con in problem.constraints or []:
        if con.symbol in {"f_1_con", "f_2_con"}:
            con_flat = flatten(con.func)
            # objective symbol must be referenced
            obj_sym = con.symbol.replace("_con", "")
            assert f"{obj_sym}_min" in con_flat
            # The infix parser represents -6.5 as ["Negate", 6.5], so check magnitude.
            assert abs(rp[obj_sym]) in con_flat
            assert w[obj_sym] in con_flat


@pytest.mark.scalarization
def test_rho_in_scalarization(river):
    """The rho value should appear in the scalarization expression."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    problem, _ = add_asf_partial_diff(river, "partial_asf", rp, w, rho=0.123)

    scal_flat = flatten(problem.scalarization_funcs[-1].func)
    assert 0.123 in scal_flat


@pytest.mark.scalarization
def test_alpha_variable_added(river):
    """An auxiliary alpha variable should be added to the problem."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    n_vars_before = len(river.variables)
    problem, _ = add_asf_partial_diff(river, "partial_asf", rp, w)
    assert len(problem.variables) == n_vars_before + 1
    assert any(v.symbol == "_alpha" for v in problem.variables)


# ---------------------------------------------------------------------------
# Maximized-objective sign-flip tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_maximized_objective_sign_flipped(river):
    """Reference point components for maximized objectives must be sign-flipped.

    When the infix expression `f_i_min - (-rp)` is serialised to MathJSON the
    negation appears as a double-Negate wrapper, so the rp magnitude appears as
    a positive literal with *two* Negate tokens around it (plus one more for the
    - _alpha term, three total), whereas for a minimised objective the rp has
    only one Negate (two total).

    In the river pollution problem f_1–f_4 are maximised and f_5 is minimised.
    """
    rp = {"f_1": 3.5}
    w = {"f_1": 1.0}
    problem, _ = add_asf_partial_diff(river, "partial_asf", rp, w)

    con = next(c for c in (problem.constraints or []) if c.symbol == "f_1_con")
    con_flat = flatten(con.func)
    assert rp["f_1"] in con_flat
    # Negate(Negate(rp)) for the sign-flip + Negate(_alpha) = 3 Negates total
    assert con_flat.count("Negate") == 3


@pytest.mark.scalarization
def test_minimized_objective_sign_not_flipped(river):
    """Reference point components for minimized objectives must not be sign-flipped.

    For a minimised objective with a positive rp the expression is `f_i_min - rp`,
    which produces a single Negate(rp) in MathJSON plus Negate(_alpha) = 2 total.

    In the river pollution problem only f_5 is minimised.
    """
    rp = {"f_5": 1.5}
    w = {"f_5": 1.0}
    problem, _ = add_asf_partial_diff(river, "partial_asf", rp, w)

    con = next(c for c in (problem.constraints or []) if c.symbol == "f_5_con")
    con_flat = flatten(con.func)
    assert rp["f_5"] in con_flat
    # Negate(rp) + Negate(_alpha) = exactly 2 Negates total
    assert con_flat.count("Negate") == 2


# ---------------------------------------------------------------------------
# Augmentation-term tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_weights_aug_appear_in_scalarization(dtlz2_4obj):
    """When weights_aug is given, its values should appear in the augmentation sum."""
    problem = dtlz2_4obj
    rp = {"f_1": 0.4, "f_2": 0.8}
    w = {"f_1": 0.5, "f_2": 0.5}
    w_aug = {"f_1": 0.3, "f_2": 0.7}

    problem_w_asf, _ = add_asf_partial_diff(problem, "asf", rp, w, weights_aug=w_aug)
    scal_flat = flatten(problem_w_asf.scalarization_funcs[-1].func)

    for val in w_aug.values():
        assert val in scal_flat


@pytest.mark.scalarization
def test_reference_point_aug_appear_in_scalarization(dtlz2_4obj):
    """When reference_point_aug is given, its values should appear in the augmentation sum."""
    problem = dtlz2_4obj
    rp = {"f_1": 0.4, "f_2": 0.8}
    w = {"f_1": 0.5, "f_2": 0.5}
    rp_aug = {"f_1": 1.0, "f_2": 0.2}

    problem_w_asf, _ = add_asf_partial_diff(problem, "asf", rp, w, reference_point_aug=rp_aug)
    scal_flat = flatten(problem_w_asf.scalarization_funcs[-1].func)

    for val in rp_aug.values():
        assert val in scal_flat


# ---------------------------------------------------------------------------
# Default-weights (nadir - ideal) tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_default_weights_from_ideal_nadir(river):
    """When weights=None the nadir-ideal range is used and those values appear in expressions."""
    # River pollution problem has ideal/nadir defined on all objectives.
    rp = {"f_1": -6.0, "f_5": 5.0}
    problem_w_asf, _ = add_asf_partial_diff(river, "asf", rp)  # no explicit weights

    scal_flat = flatten(problem_w_asf.scalarization_funcs[-1].func)

    for sym in rp:
        obj = next(o for o in river.objectives if o.symbol == sym)
        expected_w = abs(obj.nadir - obj.ideal)
        assert expected_w in scal_flat


@pytest.mark.scalarization
def test_default_weights_solves_successfully(river):
    """A problem built with default weights should be solvable."""
    rp = {"f_1": -6.0, "f_5": 5.0}
    problem_w_asf, target = add_asf_partial_diff(river, "asf", rp)
    res = ScipyMinimizeSolver(problem_w_asf).solve(target)
    assert res.success


@pytest.mark.scalarization
def test_error_missing_ideal_when_no_weights(dtlz2_4obj):
    """When weights=None and an active objective lacks an ideal value, raise ScalarizationError."""
    problem = dtlz2_4obj.model_copy(
        update={
            "objectives": [
                obj.model_copy(update={"ideal": None}) if obj.symbol == "f_1" else obj
                for obj in dtlz2_4obj.objectives
            ]
        }
    )
    with pytest.raises(ScalarizationError, match="ideal is missing"):
        add_asf_partial_diff(problem, "asf", {"f_1": 0.4, "f_2": 0.8})


@pytest.mark.scalarization
def test_error_missing_nadir_when_no_weights():
    """When weights=None and an active objective lacks a nadir value, raise ScalarizationError."""
    problem = river_pollution_problem()
    # Strip nadir from one active objective.
    problem = problem.model_copy(
        update={
            "objectives": [
                obj.model_copy(update={"nadir": None}) if obj.symbol == "f_1" else obj
                for obj in problem.objectives
            ]
        }
    )
    with pytest.raises(ScalarizationError, match="nadir is missing"):
        add_asf_partial_diff(problem, "asf", {"f_1": -6.0, "f_5": 5.0})


# ---------------------------------------------------------------------------
# Error tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_error_invalid_reference_point_key(river):
    """An unrecognised objective symbol in reference_point should raise ScalarizationError."""
    with pytest.raises(ScalarizationError, match="not objective symbols"):
        add_asf_partial_diff(river, "asf", {"bad_obj": 1.0}, {"bad_obj": 1.0})


@pytest.mark.scalarization
def test_error_missing_weight(river):
    """Omitting a weight for one of the active objectives should raise ScalarizationError."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    with pytest.raises(ScalarizationError, match="weights is missing"):
        add_asf_partial_diff(river, "asf", rp, {"f_1": 1.0})


@pytest.mark.scalarization
def test_error_missing_reference_point_aug_coverage(dtlz2_4obj):
    """reference_point_aug missing a key that reference_point has should raise ScalarizationError."""
    rp = {"f_1": 0.4, "f_2": 0.8}
    w = {"f_1": 0.5, "f_2": 0.5}
    rp_aug_incomplete = {"f_1": 1.0}  # missing f_2
    with pytest.raises(ScalarizationError, match="reference_point_aug is missing"):
        add_asf_partial_diff(dtlz2_4obj, "asf", rp, w, reference_point_aug=rp_aug_incomplete)


@pytest.mark.scalarization
def test_error_missing_weights_aug_coverage(dtlz2_4obj):
    """weights_aug missing a key that reference_point has should raise ScalarizationError."""
    rp = {"f_1": 0.4, "f_2": 0.8}
    w = {"f_1": 0.5, "f_2": 0.5}
    w_aug_incomplete = {"f_1": 0.3}  # missing f_2
    with pytest.raises(ScalarizationError, match="weights_aug is missing"):
        add_asf_partial_diff(dtlz2_4obj, "asf", rp, w, weights_aug=w_aug_incomplete)


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_partial_scalarization_solves_successfully(river):
    """Solving the problem with a partial ASF should succeed without errors.

    Only f_1 (maximized) and f_5 (minimized) are included; f_2, f_3, f_4 are ignored.
    """
    rp = {"f_1": -6.0, "f_5": 5.0}
    w = {"f_1": 1.0, "f_5": 1.0}

    problem_w_asf, target = add_asf_partial_diff(river, "asf", rp, w)
    res = ScipyMinimizeSolver(problem_w_asf).solve(target)

    assert res.success
    assert "f_1" in res.optimal_objectives
    assert "f_5" in res.optimal_objectives


@pytest.mark.scalarization
def test_partial_vs_full_scalarization_different_results(river):
    """Scalarizing only a subset of objectives leads to a different optimum than the full ASF.

    With the partial ASF (f_1 and f_5 only) the unconstrained objectives (f_2, f_3, f_4)
    are free to take values that differ from the full-ASF solution, which steers all five.
    """
    from desdeo.tools.scalarization import add_asf_generic_diff

    rp_partial = {"f_1": -6.0, "f_5": 5.0}
    w_partial = {"f_1": 1.0, "f_5": 1.0}

    rp_full = {"f_1": -6.0, "f_2": -3.0, "f_3": 3.0, "f_4": 2.0, "f_5": 5.0}
    w_full = {"f_1": 1.0, "f_2": 1.0, "f_3": 1.0, "f_4": 1.0, "f_5": 1.0}

    problem_partial, target_partial = add_asf_partial_diff(river, "asf_partial", rp_partial, w_partial)
    problem_full, target_full = add_asf_generic_diff(river, "asf_full", rp_full, w_full)

    res_partial = ScipyMinimizeSolver(problem_partial).solve(target_partial)
    res_full = ScipyMinimizeSolver(problem_full).solve(target_full)

    assert res_partial.success
    assert res_full.success

    # At least one of the unconstrained objectives differs between the two solutions.
    unconstrained = ["f_2", "f_3", "f_4"]
    diffs = [
        abs(res_partial.optimal_objectives[sym] - res_full.optimal_objectives[sym])
        for sym in unconstrained
    ]
    assert any(d > 1e-3 for d in diffs), (
        "Expected at least one unconstrained objective to differ between partial and full ASF."
    )
