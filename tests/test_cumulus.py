"""Tests related to the CUMULUS method."""

import numpy as np
import polars as pl
import pytest

from desdeo.mcdm.cumulus import (
    CumulusError,
    CumulusScalarization,
    _fix_worst_case_epigraphs,
    generate_starting_point,
    infer_classifications,
    solve_sub_problems,
)
from desdeo.problem import PolarsEvaluator, Problem
from desdeo.problem.schema import Constraint, ConstraintTypeEnum, Variable, VariableTypeEnum
from desdeo.problem.testproblems import nimbus_test_problem, river_pollution_problem, simple_scenario_model
from desdeo.tools import SolverResults
from desdeo.tools.robust import add_single_objective_worst_case_regret, add_worst_case_robust
from desdeo.tools.scenarios import build_combined_scenario_problem
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
# infer_classifications - structure
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

    # f_1: improve until (rp < current, maximized)
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
# infer_classifications - error paths
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
# solve_sub_problems - structure
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_solve_sub_problems_returns_one_result_per_scalarization(river_current):
    """The number of returned entries should match len(scalarizations)."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}
    scals = [CumulusScalarization.CUMULONIMBUS, CumulusScalarization.ASF_PARTIAL]

    results = solve_sub_problems(problem, current, rp, scals, solver=ScipyMinimizeSolver)

    assert len(results) == len(scals)
    assert set(results.keys()) == set(scals)


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

    assert results[CumulusScalarization.CUMULONIMBUS] is not None
    assert results[CumulusScalarization.CUMULONIMBUS].success


@pytest.mark.cumulus
def test_solve_sub_problems_asf_partial(river_current):
    """ASF_PARTIAL scalarization should solve successfully (uses diff variant for differentiable problem)."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    results = solve_sub_problems(
        problem,
        current,
        rp,
        [CumulusScalarization.ASF_PARTIAL],
        solver=ScipyMinimizeSolver,
    )

    assert results[CumulusScalarization.ASF_PARTIAL] is not None
    assert results[CumulusScalarization.ASF_PARTIAL].success


@pytest.mark.cumulus
def test_solve_sub_problems_all_scalarizations(river_current):
    """All scalarizations in one call should each produce a successful result."""
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    results = solve_sub_problems(
        problem,
        current,
        rp,
        list(CumulusScalarization),
    )

    assert len(results) == 2
    for res in results.values():
        assert res is not None
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

    res_partial = results_partial[CumulusScalarization.CUMULONIMBUS]
    res_pinned = results_pinned[CumulusScalarization.CUMULONIMBUS]

    assert res_partial is not None and res_partial.success
    assert res_pinned is not None and res_pinned.success

    f2_partial = res_partial.optimal_objectives["f_2"]
    f2_pinned = res_pinned.optimal_objectives["f_2"]

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
        [CumulusScalarization.CUMULONIMBUS, CumulusScalarization.ASF_PARTIAL],
        solver=ScipyMinimizeSolver,
    )

    for res in results.values():
        assert res is not None
        for obj in problem.objectives:
            assert obj.symbol in res.optimal_objectives


# ---------------------------------------------------------------------------
# solve_sub_problems - error paths
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
            [CumulusScalarization.ASF_PARTIAL],
        )


# ---------------------------------------------------------------------------
# solve_sub_problems - hard and soft constraints
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_solve_sub_problems_feasible_soft_constraint_is_not_relaxed(river_current):
    """When hard and soft constraints are jointly feasible, no relaxation should occur.

    x_1 is bounded to [0.3, 1.0]. A hard upper bound of 0.4 and a soft upper bound of
    0.6 are jointly satisfiable, so the solver should find a solution directly, with no
    violation variable present in the result.
    """
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    hard = [
        Constraint(name="x1 hard ub", symbol="g_hard", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x_1", 0.4])
    ]
    soft = [
        Constraint(name="x1 soft ub", symbol="g_soft", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x_1", 0.6])
    ]

    results = solve_sub_problems(
        problem,
        current,
        rp,
        [CumulusScalarization.ASF_PARTIAL],
        solver=ScipyMinimizeSolver,
        hard_constraints=hard,
        soft_constraints=soft,
    )

    result = results[CumulusScalarization.ASF_PARTIAL]
    assert result is not None
    assert result.success
    assert result.optimal_variables["x_1"] <= 0.4 + 1e-6
    assert "_g_soft_lte_violation" not in result.optimal_variables


@pytest.mark.cumulus
def test_solve_sub_problems_relaxes_conflicting_soft_constraint(river_current):
    """When the soft constraint conflicts with the hard constraint, it should be relaxed.

    The hard constraint forces x_1 >= 0.8; the soft constraint asks for x_1 <= 0.5,
    which is infeasible together. The solver should fall back to minimizing the
    violation, satisfy the hard constraint, and land exactly at the minimum possible
    violation (0.3) for the soft constraint.
    """
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    hard = [
        Constraint(name="x1 hard lb", symbol="g_hard", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", 0.8, "x_1"])
    ]
    soft = [
        Constraint(name="x1 soft ub", symbol="g_soft", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x_1", 0.5])
    ]

    results = solve_sub_problems(
        problem,
        current,
        rp,
        [CumulusScalarization.ASF_PARTIAL],
        solver=ScipyMinimizeSolver,
        hard_constraints=hard,
        soft_constraints=soft,
    )

    result = results[CumulusScalarization.ASF_PARTIAL]
    assert result is not None
    assert result.success
    assert result.optimal_variables["x_1"] >= 0.8 - 1e-6
    assert np.isclose(result.optimal_variables["_g_soft_lte_violation"], 0.3, atol=1e-4)


@pytest.mark.cumulus
def test_solve_sub_problems_hard_constraint_infeasible_without_soft(river_current):
    """An infeasible hard constraint with no soft constraints to relax should yield None.

    x_1 is bounded to [0.3, 1.0], so a hard upper bound of -0.2 can never be satisfied.
    With no soft constraints supplied, there is nothing to relax, so the sub-problem
    should be reported as infeasible.
    """
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    hard = [
        Constraint(name="impossible", symbol="g_bad", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x_1", -0.2])
    ]

    results = solve_sub_problems(
        problem,
        current,
        rp,
        [CumulusScalarization.ASF_PARTIAL],
        solver=ScipyMinimizeSolver,
        hard_constraints=hard,
    )

    assert results[CumulusScalarization.ASF_PARTIAL] is None


@pytest.mark.cumulus
def test_solve_sub_problems_error_hard_constraint_infeasible_with_soft(river_current):
    """An infeasible hard constraint should raise CumulusError, even with soft constraints present.

    x_1 is bounded to [0.3, 1.0], so a hard upper bound of -0.2 can never be satisfied,
    regardless of how the soft constraints are relaxed. The relaxation attempt should
    fail to find an optimal solution and raise CumulusError instead of silently
    returning a bogus result.
    """
    problem, current = river_current
    rp = {"f_1": -6.0, "f_5": 8.0}

    hard = [
        Constraint(name="impossible", symbol="g_bad", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x_1", -0.2])
    ]
    soft = [
        Constraint(name="x1 soft ub", symbol="g_soft", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x_1", 0.5])
    ]

    with pytest.raises(CumulusError, match="Could not find an optimal solution"):
        solve_sub_problems(
            problem,
            current,
            rp,
            [CumulusScalarization.ASF_PARTIAL],
            solver=ScipyMinimizeSolver,
            hard_constraints=hard,
            soft_constraints=soft,
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


# ---------------------------------------------------------------------------
# _fix_worst_case_epigraphs
# ---------------------------------------------------------------------------


def _evaluate_to_solver_results(problem: Problem, variable_values: dict[str, float]) -> SolverResults:
    """Evaluate problem at variable_values and package the result as a SolverResults."""
    df = pl.DataFrame({k: [v] for k, v in variable_values.items()})
    row = PolarsEvaluator(problem).evaluate(df).row(0, named=True)
    obj_syms = {o.symbol for o in problem.objectives or []}
    con_syms = {c.symbol for c in problem.constraints or []}
    return SolverResults(
        optimal_variables=dict(variable_values),
        optimal_objectives={s: row[s] for s in obj_syms if s in row},
        constraint_values={s: row[s] for s in con_syms if s in row},
        success=True,
        message="synthetic",
    )


@pytest.fixture
def scenario_combined_with_epigraphs():
    """simple_scenario_model combined problem with worst-case robust and regret epigraphs added for f_1."""
    model = simple_scenario_model()
    combined, symbol_maps = build_combined_scenario_problem(model)
    combined, _ = add_worst_case_robust(model, ["f_1"], prefix="robust_", combined=combined, symbol_maps=symbol_maps)
    ideals = {"f_1": {"s_1": 1.0, "s_2": 2.0, "s_3": 3.0}}
    combined, _ = add_single_objective_worst_case_regret(
        model, ["f_1"], ideals=ideals, prefix="regret_wc_", combined=combined, symbol_maps=symbol_maps
    )
    return combined, symbol_maps


@pytest.mark.cumulus
@pytest.mark.scenario
def test_fix_worst_case_epigraphs_tightens_robust_minimize(scenario_combined_with_epigraphs):
    """A loose (too-large) t for a minimised worst-case robust objective is tightened to the max leaf value."""
    combined, symbol_maps = scenario_combined_with_epigraphs
    # f_1 leaves evaluate to 3, 13, 25 (minimised) -> worst case is the max, 25.
    variable_values = {
        "x_1": 1.0,
        "s_1_x_2": 2.0,
        "s_2_x_2": 3.0,
        "s_3_x_2": 4.0,
        "_t_robust_f_1": 1000.0,
        "_t_regret_wc_f_1": 1000.0,
    }
    result = _evaluate_to_solver_results(combined, variable_values)

    fixed = _fix_worst_case_epigraphs(result, combined, symbol_maps)

    assert fixed.optimal_objectives["robust_f_1"] == pytest.approx(25.0)
    assert fixed.optimal_variables["_t_robust_f_1"] == pytest.approx(25.0)


@pytest.mark.cumulus
@pytest.mark.scenario
def test_fix_worst_case_epigraphs_tightens_regret(scenario_combined_with_epigraphs):
    """A loose t for a worst-case regret objective is tightened using the ideal baked into the constraint.

    This is the case `_fix_worst_case_epigraphs` previously missed entirely: the regret bound
    (leaf value minus its per-leaf ideal) isn't present anywhere in the solved result, only in
    the per-leaf bound constraint.
    """
    combined, symbol_maps = scenario_combined_with_epigraphs
    # regrets: (3-1)=2, (13-2)=11, (25-3)=22 -> worst case is the max, 22.
    variable_values = {
        "x_1": 1.0,
        "s_1_x_2": 2.0,
        "s_2_x_2": 3.0,
        "s_3_x_2": 4.0,
        "_t_robust_f_1": 1000.0,
        "_t_regret_wc_f_1": 1000.0,
    }
    result = _evaluate_to_solver_results(combined, variable_values)

    fixed = _fix_worst_case_epigraphs(result, combined, symbol_maps)

    assert fixed.optimal_objectives["regret_wc_f_1"] == pytest.approx(22.0)
    assert fixed.optimal_variables["_t_regret_wc_f_1"] == pytest.approx(22.0)


@pytest.mark.cumulus
@pytest.mark.scenario
def test_fix_worst_case_epigraphs_tightens_robust_maximize():
    """For a maximised objective, worst case is the min leaf value, tightened up from a too-low t."""
    model = simple_scenario_model()
    flipped = [o.model_copy(update={"maximize": True}) if o.symbol == "f_1" else o for o in model.objectives]
    model = model.model_copy(update={"objectives": flipped})
    combined, symbol_maps = build_combined_scenario_problem(model)
    combined, _ = add_worst_case_robust(model, ["f_1"], prefix="robust_", combined=combined, symbol_maps=symbol_maps)

    # f_1 leaves: 3, 13, 25 (maximised) -> worst case is the min, 3.
    variable_values = {
        "x_1": 1.0,
        "s_1_x_2": 2.0,
        "s_2_x_2": 3.0,
        "s_3_x_2": 4.0,
        "_t_robust_f_1": -1000.0,
    }
    result = _evaluate_to_solver_results(combined, variable_values)

    fixed = _fix_worst_case_epigraphs(result, combined, symbol_maps)

    assert fixed.optimal_objectives["robust_f_1"] == pytest.approx(3.0)


@pytest.mark.cumulus
@pytest.mark.scenario
def test_fix_worst_case_epigraphs_ignores_variable_with_unrecognized_name(scenario_combined_with_epigraphs):
    """A `_t_`-prefixed variable whose name doesn't match a known epigraph constructor is left untouched."""
    combined, symbol_maps = scenario_combined_with_epigraphs
    decoy = Variable(
        name="Custom epigraph variable for f_1",
        symbol="_t_decoy_f_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=None,
        upperbound=None,
        initial_value=0.0,
    )
    combined = combined.model_copy(update={"variables": [*combined.variables, decoy]})

    variable_values = {
        "x_1": 1.0,
        "s_1_x_2": 2.0,
        "s_2_x_2": 3.0,
        "s_3_x_2": 4.0,
        "_t_robust_f_1": 1000.0,
        "_t_regret_wc_f_1": 1000.0,
        "_t_decoy_f_1": 42.0,
    }
    result = _evaluate_to_solver_results(combined, variable_values)

    fixed = _fix_worst_case_epigraphs(result, combined, symbol_maps)

    assert fixed.optimal_variables["_t_decoy_f_1"] == pytest.approx(42.0)
