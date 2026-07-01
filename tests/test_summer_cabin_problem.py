"""Structural tests for the summer cabin electricity optimization problem."""

# ruff: noqa: N806
import pytest

from desdeo.mcdm.cumulus import (
    CumulusScalarization,
    _scenario_aug_weights,
    infer_classifications,
    solve_sub_problems,
)
from desdeo.problem.schema import ConstraintTypeEnum, TensorVariable
from desdeo.problem.testproblems import (
    summer_cabin_battery_problem,
    summer_cabin_battery_problem_split,
    summer_cabin_battery_problem_split_scenario,
    summer_cabin_battery_robust_ev_problem,
)
from desdeo.tools import CVXPYSolver, GurobipySolver, PyomoBonminSolver, PyomoGurobiSolver, PyomoIpoptSolver
from desdeo.tools.partial_scalarization import add_cumulonimbus_diff
from desdeo.tools.robust import add_worst_case_robust
from desdeo.tools.scenarios import (
    build_combined_scenario_problem,
    build_scenario_problem,
    build_scenario_symbol_maps,
    resolve_elem,
)
from desdeo.tools.stochastic import add_expected_value
from desdeo.tools.utils import payoff_table_method

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="base_problem")
def base_problem_fixture():
    """Return the monolithic summer cabin battery problem."""
    return summer_cabin_battery_problem()


@pytest.fixture(name="split_problem")
def split_problem_fixture():
    """Return the split (3-segment) summer cabin battery problem."""
    return summer_cabin_battery_problem_split()


@pytest.fixture(name="scenario_model")
def scenario_model_fixture():
    """Return the split + scenario model."""
    return summer_cabin_battery_problem_split_scenario()


# ---------------------------------------------------------------------------
# base problem — structure
# ---------------------------------------------------------------------------


def test_base_builds(base_problem):
    """Problem builds without error."""
    assert base_problem is not None


def test_base_objectives(base_problem):
    """Base problem has exactly two objectives: f_1 (cost) and f_2 (investment)."""
    symbols = [o.symbol for o in base_problem.objectives]
    assert symbols == ["f_1", "f_2"]


def test_base_constraint_count(base_problem):
    """Base problem has exactly 6 constraints."""
    assert len(base_problem.constraints) == 6


def test_base_constraint_symbols(base_problem):
    """All expected constraint symbols are present."""
    syms = {c.symbol for c in base_problem.constraints}
    assert syms == {"cap_ub_con", "cap_lb_con", "soc_con_1", "soc_con", "soc_cap_con", "energy_bal"}


def test_base_soc_dynamics_eq(base_problem):
    """SOC dynamics constraints are equality constraints."""
    con_map = {c.symbol: c for c in base_problem.constraints}
    assert con_map["soc_con_1"].cons_type == ConstraintTypeEnum.EQ
    assert con_map["soc_con"].cons_type == ConstraintTypeEnum.EQ


def test_base_capacity_constraints_lte(base_problem):
    """Capacity linking constraints are LTE."""
    con_map = {c.symbol: c for c in base_problem.constraints}
    assert con_map["cap_ub_con"].cons_type == ConstraintTypeEnum.LTE
    assert con_map["cap_lb_con"].cons_type == ConstraintTypeEnum.LTE


def test_base_variable_symbols(base_problem):
    """Base problem has expected decision variable symbols."""
    syms = {v.symbol for v in base_problem.variables}
    assert {"y", "E", "n", "c", "d", "soc", "buy", "sell"} <= syms


def test_base_tensor_variables_shape(base_problem):
    """Tensor variables have the expected shape T=2208."""
    T = 2208
    tensor_syms = {v.symbol: v for v in base_problem.variables if isinstance(v, TensorVariable)}
    for sym in ("c", "d", "soc", "buy", "sell"):
        assert tensor_syms[sym].shape == [T], f"{sym} has wrong shape"


def test_base_constants(base_problem):
    """Base problem has expected constant symbols."""
    syms = {c.symbol for c in (base_problem.constants or [])}
    assert {"p", "l", "sol"} <= syms


# ---------------------------------------------------------------------------
# split problem — structure
# ---------------------------------------------------------------------------


def test_split_builds(split_problem):
    """Split problem builds without error."""
    assert split_problem is not None


def test_split_objectives(split_problem):
    """Split problem has the same two objective symbols as the base."""
    symbols = [o.symbol for o in split_problem.objectives]
    assert symbols == ["f_1", "f_2"]


def test_split_constraint_count(split_problem):
    """Split problem has 2 shared + 4 per segment x 3 segments = 14 constraints."""
    assert len(split_problem.constraints) == 14


def test_split_shared_constraints(split_problem):
    """Split problem retains the two shared capacity linking constraints."""
    syms = {c.symbol for c in split_problem.constraints}
    assert "cap_ub_con" in syms
    assert "cap_lb_con" in syms


def test_split_per_segment_constraint_symbols(split_problem):
    """Each segment has four constraints: soc_con_sk_1, soc_con_sk, soc_cap_con_sk, energy_bal_sk."""
    syms = {c.symbol for c in split_problem.constraints}
    for k in (1, 2, 3):
        assert f"soc_con_s{k}_1" in syms
        assert f"soc_con_s{k}" in syms
        assert f"soc_cap_con_s{k}" in syms
        assert f"energy_bal_s{k}" in syms


def test_split_segment_variable_symbols(split_problem):
    """Each segment has 5 TensorVariable symbols."""
    syms = {v.symbol for v in split_problem.variables}
    for k in (1, 2, 3):
        for role in ("c", "d", "soc", "buy", "sell"):
            assert f"{role}_s{k}" in syms, f"Missing {role}_s{k}"


def test_split_segment_tensor_shapes(split_problem):
    """Each segment TensorVariable has shape S=736 (T/3)."""
    S = 736
    tensor_map = {v.symbol: v for v in split_problem.variables if isinstance(v, TensorVariable)}
    for k in (1, 2, 3):
        for role in ("c", "d", "soc", "buy", "sell"):
            sym = f"{role}_s{k}"
            assert tensor_map[sym].shape == [S], f"{sym} has shape {tensor_map[sym].shape}, expected [{S}]"


# ---------------------------------------------------------------------------
# scenario model — structure
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_scenario_model_builds(scenario_model):
    """ScenarioModel builds without error."""
    assert scenario_model is not None


@pytest.mark.scenario
def test_scenario_model_leaf_names(scenario_model):
    """ScenarioModel has exactly the four expected leaf scenario names."""
    assert set(scenario_model.scenarios.keys()) == {"S1a", "S1b", "S2a", "S2b"}


@pytest.mark.scenario
def test_scenario_tree(scenario_model):
    """Scenario tree has the expected branching structure."""
    tree = scenario_model.scenario_tree
    assert set(tree["ROOT"]) == {"S1", "S2"}
    assert set(tree["S1"]) == {"S1a", "S1b"}
    assert set(tree["S2"]) == {"S2a", "S2b"}


@pytest.mark.scenario
def test_scenario_probabilities_sum_to_one(scenario_model):
    """Leaf probabilities sum to 1.0."""
    probs = scenario_model.scenario_probabilities
    leaf_sum = probs["S1a"] + probs["S1b"] + probs["S2a"] + probs["S2b"]
    assert leaf_sum == pytest.approx(1.0)


@pytest.mark.scenario
def test_scenario_probabilities_values(scenario_model):
    """Each leaf probability matches the expected value."""
    probs = scenario_model.scenario_probabilities
    assert probs["S1a"] == pytest.approx(0.81)
    assert probs["S1b"] == pytest.approx(0.09)
    assert probs["S2a"] == pytest.approx(0.09)
    assert probs["S2b"] == pytest.approx(0.01)


@pytest.mark.scenario
def test_s1a_no_extra_variables(scenario_model):
    """S1a (no outage) adds no extra variables."""
    s1a = scenario_model.scenarios["S1a"]
    assert len(s1a.variables) == 0


@pytest.mark.scenario
def test_s1b_adds_s3_variables(scenario_model):
    """S1b (s3 outage) adds unmet_s3 and z_s3."""
    s1b = scenario_model.scenarios["S1b"]
    assert "unmet_s3" in s1b.variables
    assert "z_s3" in s1b.variables
    assert "unmet_s2" not in s1b.variables


@pytest.mark.scenario
def test_s2a_adds_s2_variables(scenario_model):
    """S2a (s2 outage) adds unmet_s2 and z_s2."""
    s2a = scenario_model.scenarios["S2a"]
    assert "unmet_s2" in s2a.variables
    assert "z_s2" in s2a.variables
    assert "unmet_s3" not in s2a.variables


@pytest.mark.scenario
def test_s2b_adds_both_segment_variables(scenario_model):
    """S2b (both outages) adds variables for both s2 and s3."""
    s2b = scenario_model.scenarios["S2b"]
    for sym in ("unmet_s2", "z_s2", "unmet_s3", "z_s3"):
        assert sym in s2b.variables, f"Missing {sym} in S2b"


@pytest.mark.scenario
def test_all_scenarios_add_f3_objective(scenario_model):
    """Every leaf scenario adds an f_3 objective."""
    for name, scenario in scenario_model.scenarios.items():
        assert "f_3" in scenario.objectives, f"Scenario {name} missing f_3"


@pytest.mark.scenario
def test_s1a_no_extra_constraints(scenario_model):
    """S1a adds no extra constraints (no outage)."""
    s1a = scenario_model.scenarios["S1a"]
    assert len(s1a.constraints) == 0


@pytest.mark.scenario
def test_s1b_constraint_symbols(scenario_model):
    """S1b has exactly the 4 outage constraints for s3."""
    s1b = scenario_model.scenarios["S1b"]
    assert set(s1b.constraints.keys()) == {"energy_bal_s3", "energy_bal_out_s3", "bigm_s3", "outage_trade_s3"}


@pytest.mark.scenario
def test_s2a_constraint_symbols(scenario_model):
    """S2a has exactly the 4 outage constraints for s2."""
    s2a = scenario_model.scenarios["S2a"]
    assert set(s2a.constraints.keys()) == {"energy_bal_s2", "energy_bal_out_s2", "bigm_s2", "outage_trade_s2"}


@pytest.mark.scenario
def test_s2b_constraint_symbols(scenario_model):
    """S2b has 8 outage constraints (4 per outage segment)."""
    s2b = scenario_model.scenarios["S2b"]
    expected = {
        "energy_bal_s2",
        "energy_bal_out_s2",
        "bigm_s2",
        "outage_trade_s2",
        "energy_bal_s3",
        "energy_bal_out_s3",
        "bigm_s3",
        "outage_trade_s3",
    }
    assert set(s2b.constraints.keys()) == expected


@pytest.mark.scenario
def test_anticipation_stop_root(scenario_model):
    """ROOT anticipation stop includes investment variables and s1 schedule."""
    root_stop = scenario_model.anticipation_stop["ROOT"]
    for sym in ("y", "E", "n"):
        assert sym in root_stop, f"Missing {sym} in ROOT anticipation_stop"
    for role in ("c", "d", "soc", "buy", "sell"):
        assert f"{role}_s1" in root_stop, f"Missing {role}_s1 in ROOT anticipation_stop"


@pytest.mark.scenario
def test_anticipation_stop_s1(scenario_model):
    """S1 anticipation stop includes the s2 schedule variables."""
    s1_stop = scenario_model.anticipation_stop["S1"]
    for role in ("c", "d", "soc", "buy", "sell"):
        assert f"{role}_s2" in s1_stop, f"Missing {role}_s2 in S1 anticipation_stop"


@pytest.mark.scenario
def test_anticipation_stop_s2_includes_outage_vars(scenario_model):
    """S2 anticipation stop includes s2 schedule plus the s2 outage variables."""
    s2_stop = scenario_model.anticipation_stop["S2"]
    for role in ("c", "d", "soc", "buy", "sell"):
        assert f"{role}_s2" in s2_stop
    assert "unmet_s2" in s2_stop
    assert "z_s2" in s2_stop


@pytest.mark.scenario
def test_anticipation_stop_symbols_in_pool(scenario_model):
    """Every symbol in anticipation_stop references a variable in the base or pool."""
    base_syms = {v.symbol for v in scenario_model.base_problem.variables}
    pool_syms = {v.symbol for v in scenario_model.variables}
    all_syms = base_syms | pool_syms
    for node, symbols in scenario_model.anticipation_stop.items():
        for sym in symbols:
            assert sym in all_syms, f"anticipation_stop[{node!r}] references unknown symbol {sym!r}"


@pytest.mark.scenario
def test_f3_elem_name_derived_from_scenario_names(scenario_model):
    """resolve_elem for f_3 (scenario-only) should use the common scenario name, not the symbol."""
    combined, symbol_maps = build_combined_scenario_problem(scenario_model)
    info = resolve_elem("f_3", symbol_maps, combined, scenario_model)
    assert info.elem_name == "Power outage"
    assert info.elem_name != "f_3"


@pytest.mark.scenario
def test_build_scenario_problem_works_for_all_leaves(scenario_model):
    """build_scenario_problem succeeds for each leaf and has 3 objectives."""
    for name in ("S1a", "S1b", "S2a", "S2b"):
        prob = build_scenario_problem(scenario_model, name)
        assert prob is not None
        obj_syms = [o.symbol for o in prob.objectives]
        assert "f_3" in obj_syms, f"Scenario {name} problem missing f_3"


# ---------------------------------------------------------------------------
# CUMULUS augmentation weights for scenario problems
# ---------------------------------------------------------------------------


@pytest.fixture(name="robust_ev_problem")
def robust_ev_problem_fixture():
    """Return summer_cabin_battery_robust_ev_problem with real ideal/nadir from the payoff table."""
    return summer_cabin_battery_robust_ev_problem()


@pytest.mark.cvxpy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_cumulus_scenario_aug_weights_structure(robust_ev_problem, scenario_model):
    """_scenario_aug_weights zeros aggregation objectives and assigns |nadir-ideal| to per-scenario ones."""
    _, symbol_maps = build_combined_scenario_problem(scenario_model)

    # Reference point over the EV (aggregation) objectives as a DM would use.
    reference_point = {"E_f_1": 5.0, "E_f_2": 5.0, "E_f_3": 0.5}

    weights_aug = _scenario_aug_weights(robust_ev_problem, reference_point, symbol_maps)

    # Aggregation objectives in reference_point must have weight 0.
    for sym in reference_point:
        assert weights_aug[sym] == pytest.approx(0.0), f"{sym} (aggregation) should have weight 0"

    # Every per-scenario / shared objective must appear with its real |nadir - ideal|.
    per_scenario_syms = {
        combined_sym for leaf_map in symbol_maps.get("objectives", {}).values() for combined_sym in leaf_map.values()
    }
    obj_by_sym = {obj.symbol: obj for obj in robust_ev_problem.objectives}
    for sym in per_scenario_syms:
        obj = obj_by_sym.get(sym)
        assert obj is not None and obj.ideal is not None and obj.nadir is not None, (
            f"{sym} is missing ideal/nadir on the robust_ev_problem"
        )
        assert sym in weights_aug, f"{sym} missing from weights_aug"
        assert weights_aug[sym] == pytest.approx(obj.nadir - obj.ideal), (
            f"{sym}: expected {obj.nadir - obj.ideal}, got {weights_aug[sym]}"
        )

    # Objectives outside both groups must be absent.
    all_obj_syms = {obj.symbol for obj in robust_ev_problem.objectives}
    for sym in all_obj_syms - per_scenario_syms - set(reference_point):
        assert sym not in weights_aug, f"Unexpected objective {sym} in weights_aug"


# ---------------------------------------------------------------------------
# Solver tests — payoff table on expected-value combined problem
# ---------------------------------------------------------------------------


@pytest.fixture(name="combined_ev_problem")
def combined_ev_problem_fixture():
    """Return the expected-value combined problem built from the scenario model."""
    model = summer_cabin_battery_problem_split_scenario()
    problem, _ = add_expected_value(model, symbols=["f_1", "f_2", "f_3"])
    return problem


def _check_payoff_table(ideal, nadir):
    assert set(ideal.keys()) == set(nadir.keys())
    for sym in ideal:
        assert ideal[sym] <= nadir[sym] + 1e-6, f"{sym}: ideal {ideal[sym]} > nadir {nadir[sym]}"
    for sym in ("E_f_1", "E_f_2", "E_f_3"):
        assert sym in ideal, f"Expected objective {sym} missing from payoff table"


@pytest.mark.gurobipy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_payoff_table_gurobipy(combined_ev_problem):
    """Payoff table method runs to completion with GurobipySolver."""
    ideal, nadir = payoff_table_method(combined_ev_problem, GurobipySolver)
    _check_payoff_table(ideal, nadir)


@pytest.mark.pyomo
@pytest.mark.scenario
def test_pyomo_gurobi_constructs(combined_ev_problem):
    """PyomoGurobiSolver can be constructed (model builds without error)."""
    assert PyomoGurobiSolver(combined_ev_problem) is not None


@pytest.mark.pyomo
@pytest.mark.scenario
def test_pyomo_bonmin_constructs(combined_ev_problem):
    """PyomoBonminSolver can be constructed (model builds without error)."""
    assert PyomoBonminSolver(combined_ev_problem) is not None


@pytest.mark.pyomo
@pytest.mark.scenario
def test_pyomo_ipopt_constructs(combined_ev_problem):
    """PyomoIpoptSolver can be constructed (model builds without error)."""
    assert PyomoIpoptSolver(combined_ev_problem) is not None


@pytest.mark.gurobipy
@pytest.mark.scenario
def test_gurobipy_constructs(combined_ev_problem):
    """GurobipySolver can be constructed (model builds without error)."""
    assert GurobipySolver(combined_ev_problem) is not None


@pytest.mark.cvxpy
@pytest.mark.scenario
def test_cvxpy_constructs(combined_ev_problem):
    """CVXPYSolver can be constructed (model builds without error)."""
    assert CVXPYSolver(combined_ev_problem) is not None


@pytest.mark.cvxpy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_payoff_table_cvxpy(combined_ev_problem):
    """Payoff table method runs to completion with CVXPYSolver."""
    ideal, nadir = payoff_table_method(combined_ev_problem, CVXPYSolver)
    _check_payoff_table(ideal, nadir)


# ---------------------------------------------------------------------------
# Worst-case robust combined problem
# ---------------------------------------------------------------------------


@pytest.fixture(name="combined_wc_problem")
def combined_wc_problem_fixture():
    """Return the worst-case robust combined problem built from the scenario model."""
    model = summer_cabin_battery_problem_split_scenario()
    problem, _ = add_worst_case_robust(model, symbols=["f_1", "f_2", "f_3"])
    return problem


def _check_wc_payoff_table(ideal, nadir):
    assert set(ideal.keys()) == set(nadir.keys())
    for sym in ideal:
        assert ideal[sym] <= nadir[sym] + 1e-6, f"{sym}: ideal {ideal[sym]} > nadir {nadir[sym]}"
    for sym in ("robust_f_1", "robust_f_2", "robust_f_3"):
        assert sym in ideal, f"Expected objective {sym} missing from payoff table"


@pytest.mark.pyomo
@pytest.mark.scenario
def test_pyomo_gurobi_constructs_wc(combined_wc_problem):
    """PyomoGurobiSolver can be constructed for the worst-case robust problem."""
    assert PyomoGurobiSolver(combined_wc_problem) is not None


@pytest.mark.pyomo
@pytest.mark.scenario
def test_pyomo_bonmin_constructs_wc(combined_wc_problem):
    """PyomoBonminSolver can be constructed for the worst-case robust problem."""
    assert PyomoBonminSolver(combined_wc_problem) is not None


@pytest.mark.pyomo
@pytest.mark.scenario
def test_pyomo_ipopt_constructs_wc(combined_wc_problem):
    """PyomoIpoptSolver can be constructed for the worst-case robust problem."""
    assert PyomoIpoptSolver(combined_wc_problem) is not None


@pytest.mark.gurobipy
@pytest.mark.scenario
def test_gurobipy_constructs_wc(combined_wc_problem):
    """GurobipySolver can be constructed for the worst-case robust problem."""
    assert GurobipySolver(combined_wc_problem) is not None


@pytest.mark.cvxpy
@pytest.mark.scenario
def test_cvxpy_constructs_wc(combined_wc_problem):
    """CVXPYSolver can be constructed for the worst-case robust problem."""
    assert CVXPYSolver(combined_wc_problem) is not None


@pytest.mark.gurobipy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_payoff_table_gurobipy_wc(combined_wc_problem):
    """Payoff table method runs to completion with GurobipySolver on the worst-case robust problem."""
    ideal, nadir = payoff_table_method(combined_wc_problem, GurobipySolver)
    _check_wc_payoff_table(ideal, nadir)


@pytest.mark.cvxpy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_payoff_table_cvxpy_wc(combined_wc_problem):
    """Payoff table method runs to completion with CVXPYSolver on the worst-case robust problem."""
    ideal, nadir = payoff_table_method(combined_wc_problem, CVXPYSolver)
    _check_wc_payoff_table(ideal, nadir)


# ---------------------------------------------------------------------------
# CUMULUS / CUMULONIMBUS scalarization on the robust EV problem
# ---------------------------------------------------------------------------

_ASPIRATION_CALL = {
    "current_objectives": {"f_2": 6340, "E_f_1": 400, "robust_f_3": 0},
    "reference_point": {"f_2": 0, "E_f_1": 0, "robust_f_3": 0},
}
_RESERVATION_CALL = {
    "current_objectives": {"f_2": 6340, "E_f_1": 197.33, "robust_f_3": 0},
    "reference_point": {"f_2": 0, "E_f_1": 400.57, "robust_f_3": 0},
}


@pytest.mark.cvxpy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_cumulonimbus_aspiration_call_classifications(robust_ev_problem):
    """When rp < current for a minimized objective, classification is '<' or '<='."""
    classifications = infer_classifications(
        robust_ev_problem,
        _ASPIRATION_CALL["current_objectives"],
        _ASPIRATION_CALL["reference_point"],
    )

    # robust_f_3: rp=0 == ideal=0 → "improve" ("<"), which with the stay-equal
    # constraint reduces to robust_f_3 ≤ 0 (same effective behaviour as "=").
    assert classifications["robust_f_3"][0] == "<"

    # f_2 and E_f_1: rp=0 < current → aspiration or full-improve
    assert classifications["f_2"][0] in ("<", "<="), f"f_2 got unexpected class {classifications['f_2']}"
    assert classifications["E_f_1"][0] in ("<", "<="), f"E_f_1 got unexpected class {classifications['E_f_1']}"


@pytest.mark.cvxpy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_cumulonimbus_reservation_call_classifications(robust_ev_problem):
    """When rp > current for a minimized objective, classification is '>=' with that level."""
    classifications = infer_classifications(
        robust_ev_problem,
        _RESERVATION_CALL["current_objectives"],
        _RESERVATION_CALL["reference_point"],
    )

    # robust_f_3: rp=0 == ideal=0 → "<" (improve toward ideal, same effective behaviour as "=")
    assert classifications["robust_f_3"][0] == "<"

    # f_2: rp=0 < current=6340 → aspiration or full-improve
    assert classifications["f_2"][0] in ("<", "<="), f"f_2 got unexpected class {classifications['f_2']}"

    # E_f_1: rp=400.57 > current=197.33 → reservation
    cls, level = classifications["E_f_1"]
    assert cls == ">=", f"E_f_1 should be reservation (>=), got {cls}"
    assert level == pytest.approx(400.57)


@pytest.mark.cvxpy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_cumulonimbus_aspiration_adds_two_constraints_per_aspiration_obj(robust_ev_problem, scenario_model):
    """Aspiration classification ('<' or '<=') adds both a cap constraint and a stay-equal constraint."""
    classifications = infer_classifications(
        robust_ev_problem,
        _ASPIRATION_CALL["current_objectives"],
        _ASPIRATION_CALL["reference_point"],
    )
    weights_aug = _scenario_aug_weights(
        robust_ev_problem,
        _ASPIRATION_CALL["reference_point"],
        build_scenario_symbol_maps(robust_ev_problem, scenario_model),
    )

    p_scal, _ = add_cumulonimbus_diff(
        robust_ev_problem,
        "cn_sf",
        classifications,
        _ASPIRATION_CALL["current_objectives"],
        weights_aug=weights_aug,
    )

    new_con_syms = {c.symbol for c in p_scal.constraints} - {c.symbol for c in robust_ev_problem.constraints}

    # Every "<" or "<=" objective adds a cap constraint and a stay-equal constraint.
    # robust_f_3 is classified "<" (rp=0 == ideal=0), so it also contributes two constraints.
    aspiration_objs = [sym for sym, (cls, _) in classifications.items() if cls in ("<", "<=")]
    for sym in aspiration_objs:
        cap_sym = f"{sym}_lt" if classifications[sym][0] == "<" else f"{sym}_lte"
        eq_sym = f"{sym}_eq"
        assert cap_sym in new_con_syms, f"Missing cap constraint {cap_sym}"
        assert eq_sym in new_con_syms, f"Missing stay-equal constraint {eq_sym}"


@pytest.mark.cvxpy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_cumulonimbus_reservation_adds_only_one_constraint_per_reservation_obj(robust_ev_problem, scenario_model):
    """Reservation classification ('>=') adds only the upper-bound constraint, no stay-equal."""
    classifications = infer_classifications(
        robust_ev_problem,
        _RESERVATION_CALL["current_objectives"],
        _RESERVATION_CALL["reference_point"],
    )
    weights_aug = _scenario_aug_weights(
        robust_ev_problem,
        _RESERVATION_CALL["reference_point"],
        build_scenario_symbol_maps(robust_ev_problem, scenario_model),
    )

    p_scal, _ = add_cumulonimbus_diff(
        robust_ev_problem,
        "cn_sf",
        classifications,
        _RESERVATION_CALL["current_objectives"],
        weights_aug=weights_aug,
    )

    new_con_syms = {c.symbol for c in p_scal.constraints} - {c.symbol for c in robust_ev_problem.constraints}

    # E_f_1 is reservation: only the gte constraint, no eq constraint
    assert "E_f_1_gte" in new_con_syms, "Missing reservation constraint E_f_1_gte"
    assert "E_f_1_eq" not in new_con_syms, (
        "Reservation class must NOT add a stay-equal constraint, but E_f_1_eq is present"
    )
    assert "E_f_1_lt" not in new_con_syms
    assert "E_f_1_lte" not in new_con_syms


@pytest.mark.gurobipy
@pytest.mark.scenario
@pytest.mark.slow
@pytest.mark.githubskip(reason="Gurobi license issues")
def test_cumulonimbus_different_rp_solutions_not_dominated(robust_ev_problem, scenario_model):
    """Two CUMULONIMBUS solves with different reference points must not dominate each other."""
    scals = [CumulusScalarization.CUMULONIMBUS]

    # Tighter MIPGap so Gurobi fully optimises the battery scheduling in both calls.
    gurobi_opts = {"OutputFlag": 0, "LogToConsole": 0, "MIPGap": 1e-8}

    r1 = solve_sub_problems(
        problem=robust_ev_problem,
        scenario_model=scenario_model,
        scalarizations=scals,
        solver=GurobipySolver,
        solver_options=gurobi_opts,
        **_ASPIRATION_CALL,
    )[CumulusScalarization.CUMULONIMBUS]

    r2 = solve_sub_problems(
        problem=robust_ev_problem,
        scenario_model=scenario_model,
        scalarizations=scals,
        solver=GurobipySolver,
        solver_options=gurobi_opts,
        **_RESERVATION_CALL,
    )[CumulusScalarization.CUMULONIMBUS]

    assert r1 is not None and r1.success, "Aspiration call did not find a feasible solution"
    assert r2 is not None and r2.success, "Reservation call did not find a feasible solution"

    obj_syms = list(_ASPIRATION_CALL["reference_point"])
    maximize_flags = {obj.symbol: obj.maximize for obj in robust_ev_problem.objectives}

    o1 = r1.optimal_objectives
    o2 = r2.optimal_objectives

    # After the rho and weights_aug fixes both calls find the same optimal scheduling
    # (E_f_1 ≈ 197 EUR with y=1, E=14 kWh, n=0).  The two feasible sets differ only
    # by the E_f_1 aspiration/reservation constraints, which are non-binding at the
    # optimum.  Use atol=1.0 EUR to absorb numerical noise from the MIP solver.
    def dominates(a: dict, b: dict, atol: float = 1.0) -> bool:
        """True if a dominates b beyond numerical noise (atol per objective)."""

        def better_or_equal(sym: str, va, vb) -> bool:
            return va <= vb + atol if not maximize_flags[sym] else va >= vb - atol

        def strictly_better(sym: str, va, vb) -> bool:
            return va < vb - atol if not maximize_flags[sym] else va > vb + atol

        return all(better_or_equal(s, a[s], b[s]) for s in obj_syms) and any(
            strictly_better(s, a[s], b[s]) for s in obj_syms
        )

    assert not dominates(o1, o2), (
        f"Aspiration solution dominates reservation solution by >1 EUR.\n  sol1={o1}\n  sol2={o2}"
    )
    assert not dominates(o2, o1), (
        f"Reservation solution dominates aspiration solution by >1 EUR.\n  sol1={o1}\n  sol2={o2}"
    )
