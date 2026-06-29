"""Tests for partial scalarization functions in desdeo.tools.partial_scalarization."""

import pytest

from desdeo.problem.testproblems import dtlz2, river_pollution_problem
from desdeo.tools.partial_scalarization import add_asf_partial_diff, add_asf_partial_nondiff, add_cumulonimbus_diff
from desdeo.tools.scalarization import ScalarizationError
from desdeo.tools.scipy_solver_interfaces import ScipyDeSolver, ScipyMinimizeSolver


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
    problem, sym = add_asf_partial_diff(river, "partial_asf", rp, w)  # noqa: RUF059

    scal_flat = flatten(problem.scalarization_funcs[-1].func)

    for sym_active in active:
        assert sym_active in scal_flat
    for sym_inactive in inactive:
        assert sym_inactive not in scal_flat


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
    for obj_sym in ("f_3", "f_4", "f_5"):
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
            assert obj_sym in con_flat
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

    The constraint for a maximised objective uses `(-1 * f_i)` (a Multiply by
    -1), and the corrected reference point is `-rp` (Negate(rp)).  So the
    expression `(-1 * f_i) - (-rp)` produces three Negate tokens: one from the
    `-1` literal, one from `Negate(rp)`, and one extra from `--rp` becoming
    `Negate(Negate(rp))`, plus one from `- _alpha`, totalling 4 Negates.
    For a minimised objective (no sign-flip) the expression `f_i - rp - _alpha`
    produces only 2 Negates.

    In the river pollution problem f_1-f_4 are maximised and f_5 is minimised.
    """
    rp = {"f_1": 3.5}
    w = {"f_1": 1.0}
    problem, _ = add_asf_partial_diff(river, "partial_asf", rp, w)

    con = next(c for c in (problem.constraints or []) if c.symbol == "f_1_con")
    con_flat = flatten(con.func)
    assert rp["f_1"] in con_flat
    assert "f_1" in con_flat
    # Negate(1) for -1*f_i + Negate(Negate(rp)) for the double-negation + Negate(_alpha) = 4 Negates
    assert con_flat.count("Negate") == 4


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
                obj.model_copy(update={"ideal": None}) if obj.symbol == "f_1" else obj for obj in dtlz2_4obj.objectives
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
                obj.model_copy(update={"nadir": None}) if obj.symbol == "f_1" else obj for obj in problem.objectives
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
    from desdeo.tools.scalarization import add_asf_generic_diff  # noqa: PLC0415

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
    diffs = [abs(res_partial.optimal_objectives[sym] - res_full.optimal_objectives[sym]) for sym in unconstrained]
    assert any(d > 1e-3 for d in diffs), (
        "Expected at least one unconstrained objective to differ between partial and full ASF."
    )


# ===========================================================================
# Tests for add_asf_partial_nondiff
# ===========================================================================


@pytest.mark.scalarization
def test_nondiff_symbol_returned(river):
    """The returned symbol should match the one supplied."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    _, sym = add_asf_partial_nondiff(river, "partial_asf_nd", rp, w)
    assert sym == "partial_asf_nd"


@pytest.mark.scalarization
def test_nondiff_no_alpha_variable_added(river):
    """The nondiff variant should not add an auxiliary alpha variable."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    n_vars_before = len(river.variables)
    result_problem, _ = add_asf_partial_nondiff(river, "partial_asf_nd", rp, w)
    assert len(result_problem.variables) == n_vars_before
    assert not any(v.symbol == "_alpha" for v in result_problem.variables)


@pytest.mark.scalarization
def test_nondiff_no_constraints_added(river):
    """The nondiff variant should not add any constraints."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    n_cons_before = len(river.constraints or [])
    result_problem, _ = add_asf_partial_nondiff(river, "partial_asf_nd", rp, w)
    assert len(result_problem.constraints or []) == n_cons_before


@pytest.mark.scalarization
def test_nondiff_marked_as_nondifferentiable(river):
    """The added scalarization should be flagged as non-differentiable."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    result_problem, sym = add_asf_partial_nondiff(river, "partial_asf_nd", rp, w)
    scal = next(s for s in result_problem.scalarization_funcs if s.symbol == sym)
    assert not scal.is_twice_differentiable
    assert not scal.is_convex
    assert not scal.is_linear


@pytest.mark.scalarization
def test_nondiff_max_operator_in_expression(river):
    """The scalarization expression should contain the Max operator."""
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    result_problem, sym = add_asf_partial_nondiff(river, "partial_asf_nd", rp, w)
    scal = next(s for s in result_problem.scalarization_funcs if s.symbol == sym)
    scal_flat = flatten(scal.func)
    assert "Max" in scal_flat


@pytest.mark.scalarization
def test_nondiff_only_active_objectives_in_expression(river):
    """Only active objectives should appear in the scalarization expression."""
    active = {"f_1", "f_2"}
    inactive = {"f_3", "f_4", "f_5"}
    rp = {"f_1": -6.0, "f_2": -3.0}
    w = {"f_1": 1.0, "f_2": 1.0}
    result_problem, sym = add_asf_partial_nondiff(river, "partial_asf_nd", rp, w)  # noqa: RUF059
    scal_flat = flatten(result_problem.scalarization_funcs[-1].func)
    for s in active:
        assert s in scal_flat
    for s in inactive:
        assert s not in scal_flat


@pytest.mark.scalarization
def test_nondiff_default_weights_from_ideal_nadir(river):
    """When weights=None the nadir-ideal range is used as the default weights."""
    rp = {"f_1": -6.0, "f_5": 5.0}
    result_problem, _ = add_asf_partial_nondiff(river, "partial_asf_nd", rp)
    scal_flat = flatten(result_problem.scalarization_funcs[-1].func)
    for sym in rp:
        obj = next(o for o in river.objectives if o.symbol == sym)
        expected_w = abs(obj.nadir - obj.ideal)
        assert expected_w in scal_flat


@pytest.mark.scalarization
def test_nondiff_weights_aug_appear_in_expression(dtlz2_4obj):
    """When weights_aug is provided its values should appear in the augmentation part."""
    rp = {"f_1": 0.4, "f_2": 0.8}
    w = {"f_1": 0.5, "f_2": 0.5}
    w_aug = {"f_1": 0.3, "f_2": 0.7}
    result_problem, _ = add_asf_partial_nondiff(dtlz2_4obj, "partial_asf_nd", rp, w, weights_aug=w_aug)
    scal_flat = flatten(result_problem.scalarization_funcs[-1].func)
    for val in w_aug.values():
        assert val in scal_flat


@pytest.mark.scalarization
def test_nondiff_reference_point_aug_appear_in_expression(dtlz2_4obj):
    """When reference_point_aug is provided its values should appear in the augmentation part."""
    rp = {"f_1": 0.4, "f_2": 0.8}
    w = {"f_1": 0.5, "f_2": 0.5}
    rp_aug = {"f_1": 1.0, "f_2": 0.2}
    result_problem, _ = add_asf_partial_nondiff(dtlz2_4obj, "partial_asf_nd", rp, w, reference_point_aug=rp_aug)
    scal_flat = flatten(result_problem.scalarization_funcs[-1].func)
    for val in rp_aug.values():
        assert val in scal_flat


@pytest.mark.scalarization
def test_nondiff_error_invalid_reference_point_key(river):
    """An unrecognised objective symbol in reference_point should raise ScalarizationError."""
    with pytest.raises(ScalarizationError, match="not objective symbols"):
        add_asf_partial_nondiff(river, "partial_asf_nd", {"bad_obj": 1.0}, {"bad_obj": 1.0})


@pytest.mark.scalarization
def test_nondiff_error_missing_weight(river):
    """Omitting a weight for one active objective should raise ScalarizationError."""
    with pytest.raises(ScalarizationError, match="weights is missing"):
        add_asf_partial_nondiff(river, "partial_asf_nd", {"f_1": -6.0, "f_2": -3.0}, {"f_1": 1.0})


@pytest.mark.scalarization
def test_nondiff_error_missing_reference_point_aug_coverage(dtlz2_4obj):
    """reference_point_aug missing a key from reference_point should raise ScalarizationError."""
    rp = {"f_1": 0.4, "f_2": 0.8}
    w = {"f_1": 0.5, "f_2": 0.5}
    with pytest.raises(ScalarizationError, match="reference_point_aug is missing"):
        add_asf_partial_nondiff(dtlz2_4obj, "partial_asf_nd", rp, w, reference_point_aug={"f_1": 1.0})


@pytest.mark.scalarization
def test_nondiff_error_missing_weights_aug_coverage(dtlz2_4obj):
    """weights_aug missing a key from reference_point should raise ScalarizationError."""
    rp = {"f_1": 0.4, "f_2": 0.8}
    w = {"f_1": 0.5, "f_2": 0.5}
    with pytest.raises(ScalarizationError, match="weights_aug is missing"):
        add_asf_partial_nondiff(dtlz2_4obj, "partial_asf_nd", rp, w, weights_aug={"f_1": 0.3})


@pytest.mark.scalarization
def test_nondiff_solves_successfully(river):
    """The problem built with the nondiff partial ASF should be solvable."""
    rp = {"f_1": -6.0, "f_5": 5.0}
    w = {"f_1": 1.0, "f_5": 1.0}
    result_problem, target = add_asf_partial_nondiff(river, "partial_asf_nd", rp, w)
    res = ScipyDeSolver(result_problem).solve(target)
    assert res.success


@pytest.mark.scalarization
def test_nondiff_matches_diff_solution(river):
    """The nondiff and diff partial ASF should converge to the same optimum.

    Both formulations express the same mathematical function; they should reach
    the same Pareto-optimal solution (up to solver tolerance).
    """
    rp = {"f_1": -6.0, "f_5": 5.0}
    w = {"f_1": 1.0, "f_5": 1.0}

    problem_diff, target_diff = add_asf_partial_diff(river, "asf_diff", rp, w)
    problem_nondiff, target_nondiff = add_asf_partial_nondiff(river, "asf_nondiff", rp, w)

    res_diff = ScipyMinimizeSolver(problem_diff).solve(target_diff)
    res_nondiff = ScipyDeSolver(problem_nondiff).solve(target_nondiff)

    assert res_diff.success
    assert res_nondiff.success

    for sym in rp:
        assert abs(res_diff.optimal_objectives[sym] - res_nondiff.optimal_objectives[sym]) < 1e-3


# ===========================================================================
# Tests for add_cumulonimbus_diff
# ===========================================================================

# River pollution problem: f_1 (max), f_2 (max), f_3 (max), f_4 (max), f_5 (min)
# DTLZ2 4-obj: f_1..f_4 all minimized, values on unit sphere


@pytest.fixture
def river_current():
    """River problem with a plausible current objective vector."""
    problem = river_pollution_problem()
    # Rough mid-range values consistent with the problem.
    current = {"f_1": -6.5, "f_2": -3.5, "f_3": -4.0, "f_4": -2.0, "f_5": 9.0}
    return problem, current


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_cumulonimbus_symbol_returned(river_current):
    """The returned symbol should match the one supplied."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}
    _, sym = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    assert sym == "cumulonimbus"


@pytest.mark.scalarization
def test_cumulonimbus_alpha_variable_added(river_current):
    """An auxiliary alpha variable should be added to the problem."""
    problem, current = river_current
    n_vars_before = len(problem.variables)
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}
    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    assert len(result_problem.variables) == n_vars_before + 1
    assert any(v.symbol == "_alpha" for v in result_problem.variables)


@pytest.mark.scalarization
def test_cumulonimbus_only_active_objectives_in_scalarization(river_current):
    """Only classified objectives should appear in the scalarization augmentation expression."""
    problem, current = river_current
    active = {"f_1", "f_2"}
    inactive = {"f_3", "f_4", "f_5"}
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}

    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    scal_flat = flatten(result_problem.scalarization_funcs[-1].func)

    for sym in active:
        assert sym in scal_flat
    for sym in inactive:
        assert sym not in scal_flat


@pytest.mark.scalarization
def test_cumulonimbus_unclassified_objectives_have_no_constraint(river_current):
    """Objectives absent from classifications should produce no constraints."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}
    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)

    added_symbols = {c.symbol for c in (result_problem.constraints or [])}
    for sym in ("f_3", "f_4", "f_5"):
        assert not any(s.startswith(sym) for s in added_symbols)


# ---------------------------------------------------------------------------
# Per-classification constraint tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_cumulonimbus_lt_classification_adds_two_constraints(river_current):
    """Classification '<' should add _lt and _eq constraints for the objective."""
    problem, current = river_current
    cls = {"f_1": ("<", None)}
    n_before = len(problem.constraints or [])  # noqa: F841
    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    added = [c for c in (result_problem.constraints or []) if c.symbol.startswith("f_1")]
    symbols = {c.symbol for c in added}
    assert "f_1_lt" in symbols
    assert "f_1_eq" in symbols
    assert len(added) == 2


@pytest.mark.scalarization
def test_cumulonimbus_lte_classification_adds_two_constraints(river_current):
    """Classification '<=' should add _lte and _eq constraints for the objective."""
    problem, current = river_current
    cls = {"f_1": ("<=", -6.0)}
    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    added = [c for c in (result_problem.constraints or []) if c.symbol.startswith("f_1")]
    symbols = {c.symbol for c in added}
    assert "f_1_lte" in symbols
    assert "f_1_eq" in symbols
    assert len(added) == 2


@pytest.mark.scalarization
def test_cumulonimbus_eq_classification_adds_one_constraint(river_current):
    """Classification '=' should add only an _eq constraint."""
    problem, current = river_current
    cls = {"f_1": ("=", None)}
    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    added = [c for c in (result_problem.constraints or []) if c.symbol.startswith("f_1")]
    symbols = {c.symbol for c in added}
    assert "f_1_eq" in symbols
    assert len(added) == 1


@pytest.mark.scalarization
def test_cumulonimbus_gte_classification_adds_one_constraint(river_current):
    """Classification '>=' should add only a _gte constraint."""
    problem, current = river_current
    cls = {"f_1": (">=", -6.0)}
    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    added = [c for c in (result_problem.constraints or []) if c.symbol.startswith("f_1")]
    symbols = {c.symbol for c in added}
    assert "f_1_gte" in symbols
    assert len(added) == 1


@pytest.mark.scalarization
def test_cumulonimbus_free_classification_adds_no_constraint(river_current):
    """Classification '0' (free) should add no constraints."""
    problem, current = river_current
    # Must include at least one other active objective in the augmentation.
    cls = {"f_1": ("0", None), "f_2": (">=", -3.0)}
    n_before = len(problem.constraints or [])  # noqa: F841
    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    added = [c for c in (result_problem.constraints or []) if c.symbol.startswith("f_1")]
    assert len(added) == 0


# ---------------------------------------------------------------------------
# Error tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_cumulonimbus_error_invalid_objective_symbol(river_current):
    """An unrecognised objective symbol in classifications should raise ScalarizationError."""
    problem, current = river_current
    with pytest.raises(ScalarizationError, match="not objective symbols"):
        add_cumulonimbus_diff(problem, "cumulonimbus", {"bad_obj": ("<", None)}, current)


@pytest.mark.scalarization
def test_cumulonimbus_error_missing_current_for_lt(river_current):
    """A '<' classification with missing current_objective_vector entry should raise ScalarizationError."""
    problem, _ = river_current
    incomplete_current = {"f_2": -3.5}  # f_1 missing
    with pytest.raises(ScalarizationError, match="current_objective_vector is missing"):
        add_cumulonimbus_diff(problem, "cumulonimbus", {"f_1": ("<", None)}, incomplete_current)


@pytest.mark.scalarization
def test_cumulonimbus_error_missing_current_for_eq(river_current):
    """An '=' classification with missing current_objective_vector entry should raise ScalarizationError."""
    problem, _ = river_current
    incomplete_current = {"f_2": -3.5}
    with pytest.raises(ScalarizationError, match="current_objective_vector is missing"):
        add_cumulonimbus_diff(problem, "cumulonimbus", {"f_1": ("=", None)}, incomplete_current)


@pytest.mark.scalarization
def test_cumulonimbus_error_invalid_classification_string(river_current):
    """An unsupported classification string should raise ScalarizationError."""
    problem, current = river_current
    with pytest.raises(ScalarizationError, match="not supported"):
        add_cumulonimbus_diff(problem, "cumulonimbus", {"f_1": ("?", None)}, current)


@pytest.mark.scalarization
def test_cumulonimbus_error_missing_reference_point_aug_coverage(river_current):
    """reference_point_aug missing a key that classifications has should raise ScalarizationError."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}
    rp_aug_incomplete = {"f_1": -6.0}  # missing f_2
    with pytest.raises(ScalarizationError, match="reference_point_aug is missing"):
        add_cumulonimbus_diff(problem, "cumulonimbus", cls, current, reference_point_aug=rp_aug_incomplete)


@pytest.mark.scalarization
def test_cumulonimbus_error_missing_weights_aug_coverage(river_current):
    """weights_aug missing a key that classifications has should raise ScalarizationError."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}
    w_aug_incomplete = {"f_1": 1.0}  # missing f_2
    with pytest.raises(ScalarizationError, match="weights_aug is missing"):
        add_cumulonimbus_diff(problem, "cumulonimbus", cls, current, weights_aug=w_aug_incomplete)


# ---------------------------------------------------------------------------
# Augmentation reference point / weights tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_cumulonimbus_weights_aug_appear_in_scalarization(river_current):
    """When weights_aug is given its values should appear in the augmentation expression."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}
    w_aug = {"f_1": -0.3, "f_2": -0.7}  # negative: maximize objectives (nadir < ideal)
    result_problem, _ = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current, weights_aug=w_aug)
    scal_flat = flatten(result_problem.scalarization_funcs[-1].func)
    for val in w_aug.values():
        assert abs(val) in scal_flat


@pytest.mark.scalarization
def test_cumulonimbus_reference_point_aug_appear_in_scalarization(river_current):
    """When reference_point_aug is given its values should appear in the augmentation expression."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}
    rp_aug = {"f_1": -6.0, "f_2": -3.0}
    w_aug = {"f_1": -1.0, "f_2": -1.0}  # negative: maximize objectives
    result_problem, _ = add_cumulonimbus_diff(
        problem, "cumulonimbus", cls, current, reference_point_aug=rp_aug, weights_aug=w_aug
    )
    scal_flat = flatten(result_problem.scalarization_funcs[-1].func)
    for val in rp_aug.values():
        assert abs(val) in scal_flat


@pytest.mark.scalarization
def test_cumulonimbus_aug_params_do_not_affect_constraints(river_current):
    """reference_point_aug and weights_aug should not appear in the constraint expressions."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0)}
    rp_aug = {"f_1": -5.0, "f_2": -2.5}
    w_aug = {"f_1": -0.42, "f_2": -0.58}  # negative: maximize objectives
    result_problem, _ = add_cumulonimbus_diff(
        problem, "cumulonimbus", cls, current, reference_point_aug=rp_aug, weights_aug=w_aug
    )
    for con in result_problem.constraints or []:
        con_flat = flatten(con.func)
        for val in w_aug.values():
            assert val not in con_flat
        for val in rp_aug.values():
            assert abs(val) not in con_flat


@pytest.mark.scalarization
def test_cumulonimbus_solves_with_aug_params(river_current):
    """A problem built with reference_point_aug and weights_aug should be solvable."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_5": (">=", 10.0)}
    rp_aug = {"f_1": -6.5, "f_5": 9.0}
    w_aug = {"f_1": -1.0, "f_5": 1.0}  # f_1 maximize (negative), f_5 minimize (positive)
    result_problem, target = add_cumulonimbus_diff(
        problem, "cumulonimbus", cls, current, reference_point_aug=rp_aug, weights_aug=w_aug
    )
    res = ScipyMinimizeSolver(result_problem).solve(target)
    assert res.success


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


@pytest.mark.scalarization
def test_cumulonimbus_solves_successfully(river_current):
    """Solving a problem with add_cumulonimbus_diff should succeed."""
    problem, current = river_current
    cls = {"f_1": ("<", None), "f_2": (">=", -3.0), "f_5": ("=", None)}
    result_problem, target = add_cumulonimbus_diff(problem, "cumulonimbus", cls, current)
    res = ScipyMinimizeSolver(result_problem).solve(target)
    assert res.success


@pytest.mark.scalarization
def test_cumulonimbus_fewer_constraints_than_full_nimbus(river_current):
    """Cumulonimbus with a partial classification should produce fewer constraints than full NIMBUS.

    This verifies that unclassified objectives genuinely produce no constraints,
    so the partial problem is strictly less constrained than its full-NIMBUS counterpart.
    """
    from desdeo.tools.scalarization import add_nimbus_sf_diff  # noqa: PLC0415

    problem, current = river_current

    # Partial: classify only f_1 and f_5 — f_2, f_3, f_4 are free.
    cls_partial = {"f_1": ("<", None), "f_5": (">=", 10.0)}
    problem_partial, _ = add_cumulonimbus_diff(problem, "cumulus_sf", cls_partial, current)

    # Full NIMBUS: all five objectives classified with equivalent or richer classifications.
    cls_full = {
        "f_1": ("<", None),
        "f_2": (">=", -3.0),
        "f_3": (">=", -4.0),
        "f_4": ("0", None),
        "f_5": (">=", 10.0),
    }
    problem_full, _ = add_nimbus_sf_diff(problem, "nimbus_sf", cls_full, current)

    n_original = len(problem.constraints or [])
    n_partial = len(problem_partial.constraints or []) - n_original
    n_full = len(problem_full.constraints or []) - n_original

    assert n_partial < n_full, (
        f"Partial cumulonimbus should add fewer constraints ({n_partial}) than full NIMBUS ({n_full})."
    )
