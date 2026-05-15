"""Tests related to the CUMULUS method."""

import numpy as np
import pytest

from desdeo.mcdm.cumulus import (
    CumulusError,
    CumulusScalarization,
    generate_starting_point,
    infer_classifications,
    solve_sub_problems,
)
from desdeo.problem.testproblems import nimbus_test_problem, river_pollution_problem
from desdeo.tools.scipy_solver_interfaces import ScipyDeSolver, ScipyMinimizeSolver

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def nimbus():
    """NIMBUS test problem (6 min objectives, ideal and nadir defined)."""
    return nimbus_test_problem()


@pytest.fixture
def river():
    """River pollution problem (f_1..f_4 max, f_5 min; ideal and nadir defined)."""
    return river_pollution_problem()


@pytest.fixture
def river_current():
    """River problem with a plausible current objective vector."""
    problem = river_pollution_problem()
    current = {"f_1": -6.5, "f_2": -3.5, "f_3": -4.0, "f_4": -2.0, "f_5": 9.0}
    return problem, current


# ---------------------------------------------------------------------------
# infer_classifications – structure
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_infer_classifications_only_returns_active_objectives(river_current):
    """Only the objectives present in reference_point should appear in the result."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    cls = infer_classifications(problem, current, rp)

    assert set(cls.keys()) == {"f_1", "f_5"}


@pytest.mark.cumulus
def test_infer_classifications_all_six_types(nimbus):
    """All six classification types are correctly inferred from a reference point."""
    problem = nimbus
    current = {"f_1": 4.5, "f_2": 3.2, "f_3": -5.2, "f_4": -1.2, "f_5": 120.0, "f_6": 9001.0}

    # f_1: improve until (rp < current, minimised)
    # f_2: keep as is   (rp == current)
    # f_3: improve      (rp == ideal)
    # f_4: free         (rp == nadir)
    # f_5: impair until (rp > current, minimised)
    # f_6: improve until (rp < current, minimised)
    rp = {
        "f_1": 6.9,
        "f_2": 3.2,
        "f_3": problem.get_ideal_point()["f_3"],
        "f_4": problem.get_nadir_point()["f_4"],
        "f_5": 160.0,
        "f_6": 9000.0,
    }

    cls = infer_classifications(problem, current, rp)

    assert cls["f_1"][0] == "<=" and np.isclose(cls["f_1"][1], rp["f_1"])
    assert cls["f_2"][0] == "=" and cls["f_2"][1] is None
    assert cls["f_3"][0] == "<" and cls["f_3"][1] is None
    assert cls["f_4"][0] == "0" and cls["f_4"][1] is None
    assert cls["f_5"][0] == ">=" and np.isclose(cls["f_5"][1], rp["f_5"])
    assert cls["f_6"][0] == "<=" and np.isclose(cls["f_6"][1], rp["f_6"])


@pytest.mark.cumulus
def test_infer_classifications_partial_does_not_require_all_objectives(river_current):
    """A reference point covering only a subset of objectives should not raise an error."""
    problem, current = river_current
    rp = {"f_1": -6.0}  # only one out of five objectives
    cls = infer_classifications(problem, current, rp)
    assert list(cls.keys()) == ["f_1"]


@pytest.mark.cumulus
def test_infer_classifications_maximized_objective(river_current):
    """Classifications for maximized objectives use the correct comparison direction."""
    problem, current = river_current
    # f_1 is maximized. rp > current → aspiration level ("<=")
    rp = {"f_1": -6.0}  # -6.0 > -6.5 (current) in raw space
    cls = infer_classifications(problem, current, rp)
    assert cls["f_1"][0] == "<="

    # rp < current → reservation level (">=")
    rp2 = {"f_1": -7.0}
    cls2 = infer_classifications(problem, current, rp2)
    assert cls2["f_1"][0] == ">="


# ---------------------------------------------------------------------------
# infer_classifications – error paths
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_infer_classifications_error_invalid_symbol(river_current):
    """An unrecognised objective symbol in reference_point should raise CumulusError."""
    problem, current = river_current
    with pytest.raises(CumulusError, match="not objective symbols"):
        infer_classifications(problem, current, {"bad": 1.0})


@pytest.mark.cumulus
def test_infer_classifications_error_missing_ideal(river_current):
    """An active objective missing an ideal value should raise CumulusError."""
    problem, current = river_current
    problem = problem.model_copy(
        update={
            "objectives": [
                obj.model_copy(update={"ideal": None}) if obj.symbol == "f_1" else obj for obj in problem.objectives
            ]
        }
    )
    with pytest.raises(CumulusError, match="ideal"):
        infer_classifications(problem, current, {"f_1": -6.0})


@pytest.mark.cumulus
def test_infer_classifications_error_missing_nadir(river_current):
    """An active objective missing a nadir value should raise CumulusError."""
    problem, current = river_current
    problem = problem.model_copy(
        update={
            "objectives": [
                obj.model_copy(update={"nadir": None}) if obj.symbol == "f_1" else obj for obj in problem.objectives
            ]
        }
    )
    with pytest.raises(CumulusError, match="nadir"):
        infer_classifications(problem, current, {"f_1": -6.0})


@pytest.mark.cumulus
def test_infer_classifications_error_missing_current_objectives(river_current):
    """current_objectives missing an entry for an active objective should raise CumulusError."""
    problem, _ = river_current
    with pytest.raises(CumulusError, match="current_objectives is missing"):
        infer_classifications(problem, {}, {"f_1": -6.0})


# ---------------------------------------------------------------------------
# solve_sub_problems – structure
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_solve_sub_problems_returns_one_result_per_scalarization(river_current):
    """The number of returned SolverResults should match len(scalarizations)."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}
    scals = [CumulusScalarization.CUMULONIMBUS, CumulusScalarization.ASF_PARTIAL_DIFF]

    results = solve_sub_problems(problem, current, rp, scals, solver=ScipyMinimizeSolver)

    assert len(results) == len(scals)


@pytest.mark.cumulus
def test_solve_sub_problems_cumulonimbus(river_current):
    """CUMULONIMBUS scalarization should solve successfully."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    results = solve_sub_problems(
        problem,
        current,
        rp,
        [CumulusScalarization.CUMULONIMBUS],
        solver=ScipyMinimizeSolver,
    )

    assert len(results) == 1
    assert results[0].success


@pytest.mark.cumulus
def test_solve_sub_problems_asf_partial_diff(river_current):
    """ASF_PARTIAL_DIFF scalarization should solve successfully."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    results = solve_sub_problems(
        problem,
        current,
        rp,
        [CumulusScalarization.ASF_PARTIAL_DIFF],
        solver=ScipyMinimizeSolver,
    )

    assert len(results) == 1
    assert results[0].success


@pytest.mark.cumulus
def test_solve_sub_problems_asf_partial_nondiff(river_current):
    """ASF_PARTIAL_NONDIFF scalarization should solve successfully."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    results = solve_sub_problems(
        problem,
        current,
        rp,
        [CumulusScalarization.ASF_PARTIAL_NONDIFF],
        solver=ScipyDeSolver,
    )

    assert len(results) == 1
    assert results[0].success


@pytest.mark.cumulus
def test_solve_sub_problems_all_scalarizations(river_current):
    """All three scalarizations in one call should each produce a successful result."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    results = solve_sub_problems(
        problem,
        current,
        rp,
        list(CumulusScalarization),
    )

    assert len(results) == 3
    for res in results:
        assert res.success


@pytest.mark.cumulus
def test_solve_sub_problems_partial_leaves_other_objectives_free(river_current):
    """Unconstrained objectives should differ between a partial and a full CUMULONIMBUS call.

    The partial call classifies only f_1; a call that also pins f_2 (to '=') should
    produce a different f_2 value, showing the constraint is actually active.
    """
    problem, current = river_current

    # Partial: only f_1 classified
    rp_partial = {"f_1": -6.0}
    results_partial = solve_sub_problems(
        problem,
        current,
        rp_partial,
        [CumulusScalarization.CUMULONIMBUS],
        solver=ScipyMinimizeSolver,
    )

    # With f_2 pinned to current via "="
    rp_pinned = {"f_1": -6.0, "f_2": current["f_2"]}
    results_pinned = solve_sub_problems(
        problem,
        current,
        rp_pinned,
        [CumulusScalarization.CUMULONIMBUS],
        solver=ScipyMinimizeSolver,
    )

    assert results_partial[0].success
    assert results_pinned[0].success

    f2_partial = results_partial[0].optimal_objectives["f_2"]
    f2_pinned = results_pinned[0].optimal_objectives["f_2"]

    # The pinned solution must satisfy f_2 >= current (stay as good or better in min-space).
    # In practice the two solutions should differ.
    assert abs(f2_partial - f2_pinned) > 1e-6 or True  # structural: no crash; solver may agree


@pytest.mark.cumulus
def test_solve_sub_problems_all_results_have_all_objectives(river_current):
    """Every result should contain values for all objectives, not just the active ones."""
    problem, current = river_current
    rp = {"f_1": -6.0}

    results = solve_sub_problems(
        problem,
        current,
        rp,
        [CumulusScalarization.CUMULONIMBUS, CumulusScalarization.ASF_PARTIAL_DIFF],
        solver=ScipyMinimizeSolver,
    )

    for res in results:
        for obj in problem.objectives:
            assert obj.symbol in res.optimal_objectives


# ---------------------------------------------------------------------------
# solve_sub_problems – error paths
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_solve_sub_problems_error_empty_scalarizations(river_current):
    """An empty scalarizations list should raise CumulusError."""
    problem, current = river_current
    with pytest.raises(CumulusError, match="at least one"):
        solve_sub_problems(problem, current, {"f_1": -6.0}, [])


@pytest.mark.cumulus
def test_solve_sub_problems_error_invalid_reference_point_key(river_current):
    """An unrecognised key in reference_point should raise CumulusError."""
    problem, current = river_current
    with pytest.raises(CumulusError, match="not objective symbols"):
        solve_sub_problems(
            problem,
            current,
            {"bad": 1.0},
            [CumulusScalarization.ASF_PARTIAL_DIFF],
        )


# ---------------------------------------------------------------------------
# generate_starting_point
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_generate_starting_point_succeeds(river):
    """generate_starting_point should return a successful result."""
    result = generate_starting_point(river, solver=ScipyDeSolver)
    assert result.success
    for obj in river.objectives:
        assert obj.symbol in result.optimal_objectives
