"""Tests for desdeo.mcdm.jina."""

import math
import os
from pathlib import Path

import pytest

from desdeo.mcdm.jina import (
    Target,
    aggregate_outcomes,
    build_jina_problem,
    leaf_ranges,
    leaf_reference_points,
    match_pool,
    objective_ranges,
    score_designs,
    shift_reference_point,
    solve_variants,
    target_ranges,
    target_values,
)
from desdeo.problem.scenario import Scenario, ScenarioModel
from desdeo.problem.schema import Objective, Problem, Variable, VariableTypeEnum
from desdeo.problem.testproblems import simple_scenario_model, summer_cabin_battery_problem_split_scenario
from desdeo.tools import CVXPYSolver, GurobipySolver
from desdeo.tools.partial_scalarization import add_asf_partial_diff
from desdeo.tools.scenario_designs import default_design_variables, evaluate_design, outcomes_from_combined

pytestmark = pytest.mark.scenario

SOLVERS = [
    pytest.param(GurobipySolver, marks=pytest.mark.gurobipy, id="gurobipy"),
    pytest.param(CVXPYSolver, marks=pytest.mark.cvxpy, id="cvxpy"),
]


def _objective(symbol: str, func: str, *, maximize: bool = False, ideal=None, nadir=None) -> Objective:
    return Objective(
        name=symbol,
        symbol=symbol,
        func=func,
        maximize=maximize,
        ideal=ideal,
        nadir=nadir,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )


@pytest.fixture(name="model")
def simple_model_fixture() -> ScenarioModel:
    """Return the simple scenario model."""
    return simple_scenario_model()


@pytest.fixture(name="sparse_model")
def sparse_model_fixture(model) -> ScenarioModel:
    """Return the simple scenario model with an extra objective f_4 that only leaf s_2 has."""
    objectives = (*model.objectives, _objective("f_4", "x_2", ideal=-5.2, nadir=6.1))
    s_2 = model.scenarios["s_2"]
    s_2 = s_2.model_copy(update={"objectives": {**s_2.objectives, "f_4": len(objectives) - 1}})
    fields = {name: getattr(model, name) for name in type(model).model_fields}
    return ScenarioModel(**(fields | {"objectives": objectives, "scenarios": {**model.scenarios, "s_2": s_2}}))


def _maximize_f_3(model: ScenarioModel) -> ScenarioModel:
    """Return the model with the base objective f_3 replaced by a maximised f_3 = x_2."""
    base = model.base_problem.model_copy(update={"objectives": [_objective("f_3", "x_2", maximize=True)]})
    return model.with_base_problem(base)


def _midpoint(ranges: dict[str, tuple[float, float]]) -> dict[str, float]:
    return {sym: (ideal + nadir) / 2 for sym, (ideal, nadir) in ranges.items()}


def test_targets_aggregated(model):
    """Every objective of the simple model is in every leaf, so each gets one aggregated target."""
    leaves = ("s_1", "s_2", "s_3")
    for measure, prefix in [("worst_case", "robust_"), ("expected_value", "E_"), ("cvar", "CVAR_")]:
        jp = build_jina_problem(model, "aggregated", measure)
        assert [t.symbol for t in jp.targets] == [f"{prefix}f_3", f"{prefix}f_1", f"{prefix}f_2"]
        assert [t.objective for t in jp.targets] == ["f_3", "f_1", "f_2"]
        assert all(t.leaf is None and t.leaves == leaves and not t.maximize for t in jp.targets)
        objectives = {obj.symbol for obj in jp.problem.objectives}
        assert {t.symbol for t in jp.targets} <= objectives
        assert jp.probabilities == {"s_1": 0.2, "s_2": 0.3, "s_3": 0.5}


def test_targets_per_scenario(model):
    """In the per-scenario view each objective of each leaf is a target, ordered by objective then leaf."""
    jp = build_jina_problem(model, "per_scenario")
    assert [(t.objective, t.leaf) for t in jp.targets] == [
        (obj, leaf) for obj in ["f_3", "f_1", "f_2"] for leaf in ["s_1", "s_2", "s_3"]
    ]
    assert all(t.symbol == f"{t.leaf}_{t.objective}" and t.leaves == (t.leaf,) for t in jp.targets)
    assert {obj.symbol for obj in jp.problem.objectives} == {t.symbol for t in jp.targets}


def test_targets_sparse(sparse_model):
    """An objective that only one leaf has stays a per-leaf target in the aggregated view."""
    jp = build_jina_problem(sparse_model, "aggregated")
    assert [(t.symbol, t.leaf) for t in jp.targets] == [
        ("robust_f_3", None),
        ("robust_f_1", None),
        ("robust_f_2", None),
        ("s_2_f_4", "s_2"),
    ]
    per_scenario = build_jina_problem(sparse_model, "per_scenario")
    assert [t.symbol for t in per_scenario.targets if t.objective == "f_4"] == ["s_2_f_4"]


def test_targets_shared_objective():
    """An objective identical in every leaf is one target over all leaves in both views."""
    cabin = summer_cabin_battery_problem_split_scenario()
    for view in ["aggregated", "per_scenario"]:
        f_2 = [t for t in build_jina_problem(cabin, view).targets if t.objective == "f_2"]
        assert [(t.symbol, t.leaf, t.leaves) for t in f_2] == [("f_2", None, ("S1a", "S1b", "S2a", "S2b"))]


def test_maximize_targets(model):
    """Targets of a maximised objective are maximised in both views."""
    max_model = _maximize_f_3(model)
    assert [t.maximize for t in build_jina_problem(max_model, "aggregated").targets] == [True, False, False]
    per_scenario = build_jina_problem(max_model, "per_scenario").targets
    assert [t.maximize for t in per_scenario if t.objective == "f_3"] == [True] * 3


def test_build_rejects_unknown_view_and_measure(model):
    """Unknown views and measures are rejected when building."""
    with pytest.raises(ValueError, match="view"):
        build_jina_problem(model, "per-scenario")
    with pytest.raises(ValueError, match="measure"):
        build_jina_problem(model, "aggregated", "nope")


def test_solve_variants_invalid_arguments(model):
    """Design variables not in the problem and targets without a range are rejected before solving."""
    jp = build_jina_problem(model, "aggregated")
    ranges = {t.symbol: (0.0, 10.0) for t in jp.targets}
    rp = dict.fromkeys(ranges, 5.0)
    with pytest.raises(ValueError, match="x_2"):
        solve_variants(jp, rp, ranges, GurobipySolver, design_variables=["x_2"])
    with pytest.raises(ValueError, match="robust_f_1"):
        solve_variants(jp, rp, {**ranges, "robust_f_1": None}, GurobipySolver, design_variables=["x_1"])
    with pytest.raises(ValueError, match="robust_f_2"):
        solve_variants(jp, rp, {"robust_f_3": (0.0, 1.0)}, GurobipySolver, design_variables=["x_1"])


def test_shift_reference_point(model):
    """Every target of the emphasised objective moves toward its own ideal, in either direction."""
    jp = build_jina_problem(_maximize_f_3(model), "per_scenario")
    ranges = {t.symbol: (6.0, 0.0) if t.maximize else (0.0, 6.0) for t in jp.targets}
    rp = dict.fromkeys(ranges, 3.0)

    shifted = shift_reference_point(rp, jp.targets, ranges, "f_3", 3.0)
    assert shifted == {sym: 5.0 if sym.endswith("f_3") else 3.0 for sym in rp}
    assert shift_reference_point(rp, jp.targets, ranges, None, 3.0) == rp
    assert shift_reference_point(rp, jp.targets, ranges, None, 3.0) is not rp


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("measure", ["worst_case", "expected_value"])
@pytest.mark.parametrize("maximize", [False, True], ids=["min", "max"])
def test_solve_variants(model, solver, measure, maximize):
    """Every variant solves, uses its shifted reference point, and reports a binding target."""
    model = _maximize_f_3(model) if maximize else model
    jp = build_jina_problem(model, "aggregated", measure)
    ranges = target_ranges(jp, model, solver)
    f_3 = jp.targets[0]
    assert f_3.maximize == maximize
    for t in jp.targets:
        ideal, nadir = ranges[t.symbol]
        assert ideal >= nadir if t.maximize else ideal <= nadir

    rp = _midpoint(ranges)
    results = solve_variants(jp, rp, ranges, solver, design_variables=["x_1"])

    assert [r.name for r in results] == ["balanced", "emphasis_f_3", "emphasis_f_1", "emphasis_f_2"]
    for r in results:
        assert r.success, r.message
        emphasize = None if r.name == "balanced" else r.name.removeprefix("emphasis_")
        assert r.effective_reference_point == shift_reference_point(rp, jp.targets, ranges, emphasize, 3.0)
        assert set(r.design) == {"x_1"}
        assert set(r.leaf_objectives) == {"s_1", "s_2", "s_3"}
        assert set(r.target_values) == set(rp)
        assert r.binding
    assert results[0].effective_reference_point == rp

    # The maximised f_3 = x_2 is pushed above the balanced solution's value when emphasised.
    sign = -1 if maximize else 1
    assert sign * results[1].target_values[f_3.symbol] <= sign * results[0].target_values[f_3.symbol] + 1e-6


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("maximize", [False, True], ids=["min", "max"])
def test_solve_variants_cvar(model, solver, maximize):
    """The CVaR problem builds and every variant solves."""
    model = _maximize_f_3(model) if maximize else model
    jp = build_jina_problem(model, "aggregated", "cvar", cvar_alpha=0.8)
    assert jp.targets[0].maximize == maximize
    ranges = target_ranges(jp, model, solver)
    results = solve_variants(jp, _midpoint(ranges), ranges, solver, design_variables=["x_1"])
    assert all(r.success for r in results), [r.message for r in results]


@pytest.mark.parametrize("solver", SOLVERS)
def test_solve_variants_per_scenario_sparse(sparse_model, solver):
    """Per-leaf targets, including a leaf-only objective, can be solved."""
    jp = build_jina_problem(sparse_model, "per_scenario")
    ranges = target_ranges(jp, sparse_model, solver)
    results = solve_variants(jp, _midpoint(ranges), ranges, solver, design_variables=["x_1"])
    assert [r.name for r in results] == ["balanced", "emphasis_f_3", "emphasis_f_1", "emphasis_f_2", "emphasis_f_4"]
    assert all(r.success for r in results), [r.message for r in results]


@pytest.mark.gurobipy
def test_solve_variants_failure(model):
    """A variant that cannot be built is reported as unsuccessful."""
    jp = build_jina_problem(model, "aggregated")
    results = solve_variants(jp, {"nope": 0.0}, {"nope": (0.0, 1.0)}, GurobipySolver, design_variables=["x_1"])
    assert [r.name for r in results] == ["balanced"]
    assert not results[0].success
    assert "nope" in results[0].message


@pytest.mark.gurobipy
def test_solve_variants_degenerate_target(model):
    """A target with a zero range is left out of the scalarisation but still reported."""
    jp = build_jina_problem(model, "aggregated")
    ranges = target_ranges(jp, model, GurobipySolver)
    rp = _midpoint(ranges)
    ranges["robust_f_1"] = (5.0, 5.0)
    with pytest.warns(UserWarning, match="robust_f_1") as record:
        results = solve_variants(jp, rp, ranges, GurobipySolver, design_variables=["x_1"])
    assert len(record) == 1
    assert [r.name for r in results] == ["balanced", "emphasis_f_3", "emphasis_f_2"]
    for r in results:
        assert r.success, r.message
        assert set(r.effective_reference_point) == {"robust_f_3", "robust_f_2"}
        assert "robust_f_1" in r.target_values

    with pytest.raises(ValueError, match="nonzero range"):
        solve_variants(jp, {"robust_f_1": 5.0}, ranges, GurobipySolver, design_variables=["x_1"])


def _mixed_scale_model() -> ScenarioModel:
    """Return a two-leaf model with f1 = x in [0, 1] and f2 = 1e7 (1 - x) + 1 - y, y free per leaf."""
    base = Problem(
        name="Mixed scales",
        description="Objectives of very different magnitudes.",
        variables=[
            Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0),
            Variable(name="y", symbol="y", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0),
        ],
        objectives=[_objective("f1", "x"), _objective("f2", "1e7 * (1 - x) + 1 - y")],
    )
    return ScenarioModel(
        scenario_tree={"ROOT": ["s1", "s2"]},
        base_problem=base,
        scenarios={"s1": Scenario(), "s2": Scenario()},
        anticipation_stop={"ROOT": ["x"]},
    )


@pytest.mark.gurobipy
def test_target_ranges_pareto_rows():
    """Payoff rows give exact ideals on mixed scales, and Pareto rows do not count the free y in the nadir."""
    model = _mixed_scale_model()
    jp = build_jina_problem(model, "per_scenario")
    pareto = target_ranges(jp, model, GurobipySolver)
    single = target_ranges(jp, model, GurobipySolver, pareto_rows=False)

    assert pareto["f1"] == pytest.approx((0.0, 1.0), abs=1e-9)
    for sym in ["s1_f2", "s2_f2"]:
        ideal, nadir = pareto[sym]
        assert ideal == pytest.approx(0.0, abs=1e-6)
        # At x = 0, the Pareto row has y = 1; x is only held within 1e-6 of its optimum.
        assert nadir == pytest.approx(1e7, rel=2e-6)
        assert nadir <= 1e7 + 1e-6
        assert single[sym][0] == ideal
        assert single[sym][1] >= nadir


def _solve_balanced(jp, rp, ranges, rho=1e-3):
    """Solve the balanced ASF directly; return the results and the scalarization symbol."""
    weights = {sym: abs(nadir - ideal) for sym, (ideal, nadir) in ranges.items() if sym in rp}
    problem, symbol = add_asf_partial_diff(jp.problem, "_asf", rp, weights=weights, weights_aug=weights, rho=rho)
    return GurobipySolver(problem).solve(symbol), symbol


@pytest.mark.gurobipy
@pytest.mark.parametrize("measure", ["worst_case", "expected_value", "cvar"])
@pytest.mark.parametrize("maximize", [False, True], ids=["min", "max"])
def test_aggregate_outcomes_matches_symbolic(model, measure, maximize):
    """The numpy aggregation of per-leaf outcomes equals the solved aggregated objective values."""
    model = _maximize_f_3(model) if maximize else model
    jp = build_jina_problem(model, "aggregated", measure, cvar_alpha=0.6)
    assert jp.targets[0].maximize == maximize
    ranges = target_ranges(jp, model, GurobipySolver)
    results, _ = _solve_balanced(jp, _midpoint(ranges), ranges)
    assert results.success

    values = target_values(jp, outcomes_from_combined(results.optimal_objectives, jp.symbol_maps))
    symbolic = {t.symbol: (results.optimal_objectives[t.symbol], t.maximize) for t in jp.targets}
    # Auxiliary variables of a target are only pushed towards optimal by the small augmentation term,
    # so the symbolic value bounds the aggregate from the worse side, tightly up to the solver's
    # feasibility tolerance.
    for sym, (value, maximized) in symbolic.items():
        sign = -1 if maximized else 1
        assert sign * values[sym] <= sign * value + 1e-5
        assert values[sym] == pytest.approx(value, rel=1e-3)


def test_aggregate_outcomes_values(model):
    """Worst case follows the direction, EV is weighted, and missing leaves omit a target."""
    jp = build_jina_problem(_maximize_f_3(model), "aggregated", "expected_value")
    leaf_objectives = {
        "s_1": {"f_1": 1.0, "f_2": 4.0, "f_3": 1.0},
        "s_2": {"f_1": 2.0, "f_2": 5.0, "f_3": 2.0},
        "s_3": {"f_1": 3.0, "f_2": 6.0},
    }
    probabilities = {"s_1": 0.5, "s_2": 0.25, "s_3": 0.25}
    worst = aggregate_outcomes(jp.targets, leaf_objectives, "worst_case")
    assert worst == {"E_f_1": 3.0, "E_f_2": 6.0}
    expected = aggregate_outcomes(jp.targets, leaf_objectives, "expected_value", probabilities=probabilities)
    assert expected == pytest.approx({"E_f_1": 1.75, "E_f_2": 4.75})

    leaf_objectives["s_3"]["f_3"] = 3.0
    assert aggregate_outcomes(jp.targets, leaf_objectives, "worst_case")["E_f_3"] == 1.0
    # CVaR at alpha = 0.5 of (1, 2, 3) with weights (0.5, 0.25, 0.25) is the mean of the upper half.
    cvar = aggregate_outcomes(jp.targets, leaf_objectives, "cvar", probabilities=probabilities, cvar_alpha=0.5)
    assert cvar["E_f_1"] == pytest.approx(2.5)
    # The maximised f_3 takes the mean of its lower half: 1 has probability 0.5.
    assert cvar["E_f_3"] == pytest.approx(1.0)


@pytest.mark.gurobipy
@pytest.mark.parametrize("measure", ["worst_case", "expected_value"])
def test_asf_score_matches_solved(model, measure):
    """The numpy ASF score equals the solved optimum and is lowest for the design solved at that point."""
    jp = build_jina_problem(model, "aggregated", measure)
    ranges = target_ranges(jp, model, GurobipySolver)
    rp = _midpoint(ranges)
    results, symbol = _solve_balanced(jp, rp, ranges)
    values = {t.symbol: results.optimal_objectives[t.symbol] for t in jp.targets}
    score = score_designs({"direct": values}, rp, ranges, jp.targets, "asf")["direct"]
    assert score == pytest.approx(results.scalarization_values[symbol], abs=1e-6)

    variants = solve_variants(jp, rp, ranges, GurobipySolver, design_variables=["x_1"])
    scores = score_designs({r.name: r.target_values for r in variants}, rp, ranges, jp.targets, "asf")
    assert scores["balanced"] == pytest.approx(score, abs=1e-6)
    assert all(scores["balanced"] <= s + 1e-6 for s in scores.values())


def test_score_designs_methods(model):
    """GUESS and STOM are finite on normal input, and a missing target scores +inf for every method."""
    jp = build_jina_problem(_maximize_f_3(model), "aggregated")
    ranges = {"robust_f_3": (6.0, 0.0), "robust_f_1": (0.0, 10.0), "robust_f_2": (-5.0, 5.0)}
    rp = {"robust_f_3": 4.0, "robust_f_1": 5.0, "robust_f_2": 0.0}
    designs = {
        "a": {"robust_f_3": 3.0, "robust_f_1": 4.0, "robust_f_2": 1.0},
        "b": {"robust_f_3": 5.0, "robust_f_1": 6.0},
    }
    for method in ["asf", "guess", "stom"]:
        scores = score_designs(designs, rp, ranges, jp.targets, method)
        assert math.isfinite(scores["a"])
        assert scores["b"] == math.inf

    # max((4 - 5) / 10, (1 - 0) / 10, (-3 + 4) / 6) + rho * (4 / 10 + 1 / 10 - 3 / 6)
    assert score_designs(designs, rp, ranges, jp.targets, "asf", rho=1e-3)["a"] == pytest.approx(1 / 6)
    with pytest.raises(ValueError):
        score_designs(designs, rp, ranges, jp.targets, "nope")


def test_score_designs_degenerate_range(model):
    """A target with a zero range is left out of the score, with one warning."""
    jp = build_jina_problem(model, "aggregated")
    ranges = {"robust_f_3": (0.0, 10.0), "robust_f_1": (2.0, 2.0), "robust_f_2": (0.0, 10.0)}
    rp = {"robust_f_3": 5.0, "robust_f_1": 0.0, "robust_f_2": 5.0}
    designs = {"a": {"robust_f_3": 6.0, "robust_f_1": 2.0, "robust_f_2": 5.0}}
    for method in ["asf", "guess", "stom"]:
        with pytest.warns(UserWarning, match="robust_f_1") as record:
            scores = score_designs(designs, rp, ranges, jp.targets, method, rho=0.0)
        assert len(record) == 1
        assert math.isfinite(scores["a"])
    assert score_designs(designs, rp, ranges, jp.targets, "asf", rho=0.0, warn=False)["a"] == pytest.approx(0.1)

    with pytest.warns(UserWarning, match="robust_f_1") as record:
        match_pool(designs, rp, ranges, jp.targets)
    assert len(record) == 1

    with pytest.raises(ValueError, match="nonzero range"):
        score_designs(designs, {"robust_f_1": 0.0}, ranges, jp.targets, "asf")


def test_score_designs_missing_range(model):
    """A reference point target without a range is rejected by scoring and matching."""
    jp = build_jina_problem(model, "aggregated")
    ranges = {"robust_f_3": (0.0, 10.0), "robust_f_1": None}
    rp = {"robust_f_3": 5.0, "robust_f_1": 5.0, "robust_f_2": 5.0}
    designs = {"a": dict.fromkeys(rp, 1.0)}
    for method in ["asf", "guess", "stom"]:
        with pytest.raises(ValueError, match=r"No range for targets \['robust_f_1', 'robust_f_2'\]"):
            score_designs(designs, rp, ranges, jp.targets, method)
    with pytest.raises(ValueError, match="No range"):
        match_pool(designs, rp, ranges, jp.targets)


def test_match_pool_degenerate_objective(sparse_model):
    """An objective whose only target has a zero range gets no emphasis scorer."""
    jp = build_jina_problem(sparse_model, "aggregated")
    ranges = {t.symbol: (0.0, 10.0) for t in jp.targets} | {"s_2_f_4": (1.0, 1.0)}
    rp = dict.fromkeys(ranges, 5.0)
    pool = {"a": dict.fromkeys(ranges, 4.0)}
    with pytest.warns(UserWarning, match="s_2_f_4"):
        picks = match_pool(pool, rp, ranges, jp.targets)
    assert picks == {"a": ["asf", "asf_emphasis_f_3", "asf_emphasis_f_1", "asf_emphasis_f_2", "guess", "stom"]}
    with pytest.raises(ValueError, match="asf_emphasis_f_4"), pytest.warns(UserWarning, match="s_2_f_4"):
        match_pool(pool, rp, ranges, jp.targets, scorers=["asf_emphasis_f_4"])


def test_score_designs_stom_aspiration_beyond_ideal(model):
    """An aspiration better than the ideal does not invert the STOM ranking."""
    jp = build_jina_problem(model, "aggregated")
    ranges = {"robust_f_3": (0.0, 10.0)}
    designs = {"good": {"robust_f_3": 1.0}, "bad": {"robust_f_3": 2.0}}
    scores = score_designs(designs, {"robust_f_3": -5.0}, ranges, jp.targets, "stom")
    assert scores["good"] < scores["bad"]


def test_score_designs_guess_aspiration_at_nadir(model):
    """GUESS stays finite with aspirations at or near the nadir."""
    jp = build_jina_problem(model, "aggregated")
    ranges = {"robust_f_3": (0.0, 10.0), "robust_f_1": (0.0, 10.0)}
    designs = {"a": {"robust_f_3": 3.0, "robust_f_1": 4.0}}
    for rp in [{"robust_f_3": 10.0, "robust_f_1": 10.0}, {"robust_f_3": 10.0 - 1e-12, "robust_f_1": 5.0}]:
        assert math.isfinite(score_designs(designs, rp, ranges, jp.targets, "guess")["a"])


def test_match_pool(model):
    """Each scorer picks its best design not excluded."""
    jp = build_jina_problem(model, "aggregated")
    ranges = {t.symbol: (0.0, 10.0) for t in jp.targets}
    rp = dict.fromkeys(ranges, 5.0)
    pool = {
        "f_3_good": {"robust_f_3": 1.0, "robust_f_1": 6.0, "robust_f_2": 6.0},
        "f_1_good": {"robust_f_3": 6.0, "robust_f_1": 1.0, "robust_f_2": 6.0},
        "f_2_good": {"robust_f_3": 6.0, "robust_f_1": 6.0, "robust_f_2": 1.0},
        "balanced": {"robust_f_3": 4.0, "robust_f_1": 4.0, "robust_f_2": 4.0},
        "partial": {"robust_f_3": 0.0, "robust_f_1": 0.0},
    }
    picks = match_pool(pool, rp, ranges, jp.targets)
    assert picks["balanced"][0] == "asf"
    assert "asf_emphasis_f_3" in picks["f_3_good"]
    assert "asf_emphasis_f_1" in picks["f_1_good"]
    assert "asf_emphasis_f_2" in picks["f_2_good"]
    assert "partial" not in picks

    excluded = match_pool(pool, rp, ranges, jp.targets, exclude={"balanced", "f_1_good"})
    assert not set(excluded) & {"balanced", "f_1_good"}
    assert all(excluded.values())

    assert match_pool(pool, rp, ranges, jp.targets, exclude=set(pool)) == {}
    assert list(match_pool(pool, rp, ranges, jp.targets, scorers=["asf"])) == ["balanced"]


@pytest.mark.gurobipy
def test_leaf_reference_points_and_evaluate_design(sparse_model):
    """Aggregated targets apply to every leaf, per-leaf targets to their leaf, and a design evaluates at them."""
    jp = build_jina_problem(sparse_model, "aggregated")
    erp = {"robust_f_3": 1.0, "robust_f_1": 2.0, "robust_f_2": 3.0, "s_2_f_4": 4.0}
    leaf_rps = leaf_reference_points(jp.targets, erp)
    assert leaf_rps == {
        "s_1": {"f_3": 1.0, "f_1": 2.0, "f_2": 3.0},
        "s_2": {"f_3": 1.0, "f_1": 2.0, "f_2": 3.0, "f_4": 4.0},
        "s_3": {"f_3": 1.0, "f_1": 2.0, "f_2": 3.0},
    }
    ranges = {"robust_f_3": (0.0, 1.0), "robust_f_1": (0.0, 2.0), "robust_f_2": (0.0, 3.0), "s_2_f_4": (0.0, 4.0)}
    per_leaf_ranges = leaf_ranges(jp.targets, ranges)
    assert per_leaf_ranges["s_1"] == {"f_3": (0.0, 1.0), "f_1": (0.0, 2.0), "f_2": (0.0, 3.0)}
    assert per_leaf_ranges["s_2"]["f_4"] == (0.0, 4.0)
    outcomes = evaluate_design(
        sparse_model,
        {"x_1": 1.0},
        GurobipySolver,
        {},
        leaf_reference_points=leaf_rps,
        leaf_ranges=per_leaf_ranges,
    )
    assert all(outcome.status for outcome in outcomes.values())
    assert set(outcomes["s_2"].objectives) == {"f_1", "f_2", "f_3", "f_4"}


def test_objective_ranges():
    """Per-leaf target ranges combine to the best ideal and the worst nadir of each objective."""
    targets = [
        Target(symbol="s1_f_1", objective="f_1", leaf="s1", leaves=("s1",), maximize=False),
        Target(symbol="s2_f_1", objective="f_1", leaf="s2", leaves=("s2",), maximize=False),
        Target(symbol="s1_f_3", objective="f_3", leaf="s1", leaves=("s1",), maximize=True),
        Target(symbol="s2_f_3", objective="f_3", leaf="s2", leaves=("s2",), maximize=True),
        Target(symbol="robust_f_2", objective="f_2", leaf=None, leaves=("s1", "s2"), maximize=False),
        Target(symbol="s1_f_4", objective="f_4", leaf="s1", leaves=("s1",), maximize=False),
    ]
    ranges = {
        "s1_f_1": (0.0, 10.0),
        "s2_f_1": (-2.0, 8.0),
        "s1_f_3": (10.0, 0.0),
        "s2_f_3": (12.0, 1.0),
        "robust_f_2": (1.0, 5.0),
    }
    assert objective_ranges(targets, ranges) == {"f_1": (-2.0, 10.0), "f_3": (12.0, 0.0), "f_2": (1.0, 5.0)}


@pytest.mark.slow
@pytest.mark.gurobipy
@pytest.mark.githubskip
def test_solve_variants_summer_cabin():
    """A worst-case run on the summer cabin gives feasible investment designs."""
    cabin = summer_cabin_battery_problem_split_scenario()
    jp = build_jina_problem(cabin, "aggregated")
    ranges = target_ranges(jp, cabin, GurobipySolver)
    design_variables = default_design_variables(cabin)
    results = solve_variants(jp, _midpoint(ranges), ranges, GurobipySolver, design_variables=design_variables)

    assert [r.name for r in results] == ["balanced", "emphasis_f_1", "emphasis_f_2", "emphasis_f_3"]
    for r in results:
        assert r.success, r.message
        assert set(r.design) == {"y", "E", "n", "c_s1", "d_s1", "soc_s1", "buy_s1", "sell_s1"}
        if round(r.design["y"]) == 1:
            assert r.design["E"] >= 14 - 1e-6


@pytest.mark.slow
@pytest.mark.gurobipy
@pytest.mark.githubskip
@pytest.mark.skipif("DESDEO_DH_DIR" not in os.environ, reason="DESDEO_DH_DIR is not set.")
def test_solve_variants_dh():
    """A worst-case run on the district heating model solves."""
    model = ScenarioModel.model_validate_json((Path(os.environ["DESDEO_DH_DIR"]) / "dh_p9.json").read_text())
    jp = build_jina_problem(model, "aggregated")
    ranges = target_ranges(jp, model, GurobipySolver)
    results = solve_variants(
        jp, _midpoint(ranges), ranges, GurobipySolver, design_variables=default_design_variables(model)
    )
    assert all(r.success for r in results), [r.message for r in results]
