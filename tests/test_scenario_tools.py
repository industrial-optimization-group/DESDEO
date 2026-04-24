"""Tests for desdeo.tools.scenarios using simple_scenario_model."""

import pytest

from desdeo.problem.schema import ConstraintTypeEnum, Problem
from desdeo.problem.testproblems import simple_scenario_model
from desdeo.tools.robust import add_min_max_robust
from desdeo.tools.scenarios import build_combined_scenario_problem, build_scenario_problem
from desdeo.tools.stochastic import add_conditional_value_at_risk, add_expected_asf


@pytest.fixture(name="model")
def simple_model_fixture():
    """Return the simple_scenario_model test instance."""
    return simple_scenario_model()


@pytest.fixture(name="combined")
def combined_problem_fixture(model):
    """Return the combined Problem built from the simple_scenario_model."""
    problem, _ = build_combined_scenario_problem(model)
    return problem


@pytest.fixture(name="symbol_maps")
def symbol_maps_fixture(model):
    """Return the symbol_maps from build_combined_scenario_problem."""
    _, maps = build_combined_scenario_problem(model)
    return maps


# ---------------------------------------------------------------------------
# build_scenario_problem
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_build_scenario_problem_returns_scenario_problem(model):
    """build_scenario_problem returns the same result as get_scenario_problem."""
    for name in model.scenarios:
        assert build_scenario_problem(model, name) == model.get_scenario_problem(name)


@pytest.mark.scenario
def test_build_scenario_problem_unknown_raises(model):
    """Unknown scenario name raises a ValueError."""
    with pytest.raises(ValueError, match="not found"):
        build_scenario_problem(model, "nonexistent")


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_combined_variable_count(combined):
    """Combined problem has one shared x_1 plus one x_2 per scenario (4 total)."""
    symbols = {v.symbol for v in combined.variables}
    assert len(symbols) == 4


@pytest.mark.scenario
def test_shared_variable_keeps_original_name(combined):
    """x_1 is in anticipation_stop at ROOT so it keeps its original symbol."""
    symbols = {v.symbol for v in combined.variables}
    assert "x_1" in symbols
    assert "s_1_x_1" not in symbols
    assert "s_2_x_1" not in symbols
    assert "s_3_x_1" not in symbols


@pytest.mark.scenario
def test_scenario_specific_variable_gets_leaf_suffix(combined):
    """x_2 is not non-anticipative so it is copied once per leaf scenario."""
    symbols = {v.symbol for v in combined.variables}
    assert "s_1_x_2" in symbols
    assert "s_2_x_2" in symbols
    assert "s_3_x_2" in symbols
    assert "x_2" not in symbols


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_scenario_specific_constants_renamed(combined):
    """c_1 has different values per scenario so each gets a per-leaf name."""
    symbols = {c.symbol for c in (combined.constants or [])}
    assert "s_1_c_1" in symbols
    assert "s_2_c_1" in symbols
    assert "s_3_c_1" in symbols
    assert "c_1" not in symbols


@pytest.mark.scenario
def test_scenario_specific_constant_values(combined):
    """Per-scenario c_1 constants carry the correct values from the pool."""
    const_map = {c.symbol: c.value for c in (combined.constants or [])}
    assert const_map["s_1_c_1"] == pytest.approx(1.0)
    assert const_map["s_2_c_1"] == pytest.approx(5.0)
    assert const_map["s_3_c_1"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Objectives
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_combined_objective_count(combined):
    """Each of 3 scenarios contributes 3 objectives → 9 total."""
    assert len(combined.objectives) == 9


@pytest.mark.scenario
def test_all_objectives_have_leaf_suffix(combined):
    """Every objective symbol starts with a leaf prefix since none are shared."""
    prefixes = {"s_1_", "s_2_", "s_3_"}
    for obj in combined.objectives:
        assert any(obj.symbol.startswith(s) for s in prefixes), f"Objective '{obj.symbol}' has no leaf prefix"


@pytest.mark.scenario
def test_objective_variable_references_renamed(combined):
    """Scenario-specific objectives reference the renamed x_2_<leaf> symbol."""
    obj_map = {o.symbol: str(o.func) for o in combined.objectives}
    assert "s_1_x_2" in obj_map["s_1_f_3"]
    assert "s_2_x_2" in obj_map["s_2_f_3"]
    assert "s_3_x_2" in obj_map["s_3_f_3"]


@pytest.mark.scenario
def test_objective_constant_references_renamed(combined):
    """Objectives that use c_1 reference the per-scenario constant name."""
    obj_map = {o.symbol: str(o.func) for o in combined.objectives}
    assert "s_2_c_1" in obj_map["s_2_f_1"]
    assert "s_3_c_1" in obj_map["s_3_f_1"]
    assert "s_1_c_1" not in obj_map["s_1_f_1"]


@pytest.mark.scenario
def test_shared_x1_not_renamed_in_objectives(combined):
    """x_1 appears unchanged (no suffix) in all objective func strings."""
    for obj in combined.objectives:
        func_str = str(obj.func)
        assert "x_1" in func_str, f"x_1 missing in {obj.symbol}: {func_str}"
        assert "_x_1" not in func_str, f"x_1 incorrectly suffixed in {obj.symbol}: {func_str}"


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_combined_constraint_count(combined):
    """9 total constraints: 2x con_1, 2x con_2, 3x con_3, 2x con_4."""
    assert len(combined.constraints) == 9


@pytest.mark.scenario
def test_con3_duplicated_per_leaf(combined):
    """con_3 uses x_2 which differs per leaf, so it gets three copies."""
    syms = {c.symbol for c in combined.constraints}
    assert "s_1_con_3" in syms
    assert "s_2_con_3" in syms
    assert "s_3_con_3" in syms


@pytest.mark.scenario
def test_con1_only_for_leaves_that_have_it(combined):
    """con_1 is only in s_1 and s_3; s_2 should not get a copy."""
    syms = {c.symbol for c in combined.constraints}
    assert "s_1_con_1" in syms
    assert "s_3_con_1" in syms
    assert "s_2_con_1" not in syms


# ---------------------------------------------------------------------------
# Extra functions
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_extra_funcs_renamed_per_leaf(combined):
    """extra_1 has different funcs in s_1 and s_2, so both get a leaf prefix."""
    syms = {e.symbol for e in (combined.extra_funcs or [])}
    assert "s_1_extra_1" in syms
    assert "s_2_extra_1" in syms
    assert "extra_1" not in syms


@pytest.mark.scenario
def test_extra_func_values_correct(combined):
    """s_1_extra_1 uses '2*x_1' and s_2_extra_1 uses '5*x_1' (stored as MathJSON)."""
    ef_map = {e.symbol: e.func for e in (combined.extra_funcs or [])}
    assert ef_map["s_1_extra_1"] == ["Multiply", 2, "x_1"]
    assert ef_map["s_2_extra_1"] == ["Multiply", 5, "x_1"]


# ---------------------------------------------------------------------------
# Symbol uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_all_symbols_unique(combined):
    """Every symbol in the combined problem is unique."""
    all_symbols = combined.get_all_symbols()
    assert len(all_symbols) == len(set(all_symbols))


# ---------------------------------------------------------------------------
# Symbol maps — variables
# ---------------------------------------------------------------------------


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_shared_variable_keeps_original(symbol_maps):
    """x_1 is non-anticipative at ROOT so every leaf maps to the original symbol."""
    vm = symbol_maps["variables"]["x_1"]
    assert vm == {"s_1": "x_1", "s_2": "x_1", "s_3": "x_1"}


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_scenario_variable_renamed_per_leaf(symbol_maps):
    """x_2 is scenario-specific so each leaf gets its own symbol."""
    vm = symbol_maps["variables"]["x_2"]
    assert vm == {"s_1": "s_1_x_2", "s_2": "s_2_x_2", "s_3": "s_3_x_2"}


# ---------------------------------------------------------------------------
# Symbol maps — constants
# ---------------------------------------------------------------------------


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_constant_renamed_per_leaf(symbol_maps):
    """c_1 has a different value in every scenario so each leaf gets its own symbol."""
    cm = symbol_maps["constants"]["c_1"]
    assert cm == {"s_1": "s_1_c_1", "s_2": "s_2_c_1", "s_3": "s_3_c_1"}


# ---------------------------------------------------------------------------
# Symbol maps — objectives
# ---------------------------------------------------------------------------


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_objectives_all_per_leaf(symbol_maps):
    """All three objectives differ across leaves so every leaf gets its own symbol."""
    for obj_sym in ("f_1", "f_2", "f_3"):
        om = symbol_maps["objectives"][obj_sym]
        assert om == {
            "s_1": f"s_1_{obj_sym}",
            "s_2": f"s_2_{obj_sym}",
            "s_3": f"s_3_{obj_sym}",
        }, f"Unexpected map for {obj_sym}: {om}"


# ---------------------------------------------------------------------------
# Symbol maps — constraints
# ---------------------------------------------------------------------------


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_con3_per_leaf(symbol_maps):
    """con_3 uses x_2 which is renamed per leaf, so every leaf gets its own symbol."""
    cm = symbol_maps["constraints"]["con_3"]
    assert cm == {"s_1": "s_1_con_3", "s_2": "s_2_con_3", "s_3": "s_3_con_3"}


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_con1_missing_leaf_keeps_original(symbol_maps):
    """con_1 is absent from s_2, so s_2 retains the original symbol."""
    cm = symbol_maps["constraints"]["con_1"]
    assert cm["s_1"] == "s_1_con_1"
    assert cm["s_2"] == "con_1"
    assert cm["s_3"] == "s_3_con_1"


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_con2_missing_leaf_keeps_original(symbol_maps):
    """con_2 is absent from s_1, so s_1 retains the original symbol."""
    cm = symbol_maps["constraints"]["con_2"]
    assert cm["s_1"] == "con_2"
    assert cm["s_2"] == "s_2_con_2"
    assert cm["s_3"] == "s_3_con_2"


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_con4_missing_leaf_keeps_original(symbol_maps):
    """con_4 is absent from s_3, so s_3 retains the original symbol."""
    cm = symbol_maps["constraints"]["con_4"]
    assert cm["s_1"] == "s_1_con_4"
    assert cm["s_2"] == "s_2_con_4"
    assert cm["s_3"] == "con_4"


# ---------------------------------------------------------------------------
# Symbol maps — extra functions
# ---------------------------------------------------------------------------


@pytest.mark.schema
@pytest.mark.scenario
def test_symbol_map_extra_func_missing_leaf_keeps_original(symbol_maps):
    """extra_1 is absent from s_3, so s_3 retains the original symbol."""
    em = symbol_maps["extra_funcs"]["extra_1"]
    assert em["s_1"] == "s_1_extra_1"
    assert em["s_2"] == "s_2_extra_1"
    assert em["s_3"] == "extra_1"


# ---------------------------------------------------------------------------
# expected_asf
# ---------------------------------------------------------------------------

_REF = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}
_IDEAL = {"f_1": -100.0, "f_2": -100.0, "f_3": -100.0}
_NADIR = {"f_1": 100.0, "f_2": 100.0, "f_3": 100.0}


@pytest.fixture(name="asf_result")
def expected_asf_result_fixture(model):
    """Return (problem, symbol) from add_expected_asf on the simple_scenario_model."""
    return add_expected_asf(model, "asf", _REF, ideal=_IDEAL, nadir=_NADIR)


@pytest.mark.schema
@pytest.mark.scenario
def test_expected_asf_returns_problem_and_symbol(asf_result):
    """expected_asf returns a Problem and a string symbol."""
    problem, symbol = asf_result
    assert isinstance(problem, Problem)
    assert isinstance(symbol, str)


@pytest.mark.schema
@pytest.mark.scenario
def test_expected_asf_symbol_is_e_prefixed(asf_result):
    """The returned symbol is E_{input_symbol}."""
    _, symbol = asf_result
    assert symbol == "E_asf"


@pytest.mark.schema
@pytest.mark.scenario
def test_expected_asf_per_leaf_scalarizations_present(asf_result):
    """The combined problem contains one ASF scalarization per leaf scenario."""
    problem, _ = asf_result
    scal_syms = {s.symbol for s in (problem.scalarization_funcs or [])}
    assert "s_1_asf" in scal_syms
    assert "s_2_asf" in scal_syms
    assert "s_3_asf" in scal_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_expected_asf_expected_symbol_in_problem(asf_result):
    """The expected ASF symbol is present as a scalarization function."""
    problem, symbol = asf_result
    scal_syms = {s.symbol for s in (problem.scalarization_funcs or [])}
    assert symbol in scal_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_expected_asf_uses_scenario_probabilities(asf_result):
    """The expected ASF is a weighted sum using the scenario probabilities."""
    problem, _ = asf_result
    ef = next(s for s in (problem.scalarization_funcs or []) if s.symbol == "E_asf")
    func = ef.func
    assert func[0] == "Add"
    terms = {term[2]: term[1] for term in func[1:]}
    assert terms["s_1_asf"] == pytest.approx(0.2)
    assert terms["s_2_asf"] == pytest.approx(0.3)
    assert terms["s_3_asf"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# add_conditional_value_at_risk
# ---------------------------------------------------------------------------

_ALPHA = 0.95
_SCALE = 1.0 / (1.0 - _ALPHA)


@pytest.fixture(name="cvar_result")
def cvar_result_fixture(model):
    """Return (problem, added_symbols) from add_conditional_value_at_risk on f_1, f_2, f_3."""
    combined, symbol_maps = build_combined_scenario_problem(model)
    return add_conditional_value_at_risk(
        model, ["f_1", "f_2", "f_3"], alpha=_ALPHA, combined=combined, symbol_maps=symbol_maps
    )


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_returns_problem_and_dict(cvar_result):
    """add_conditional_value_at_risk returns a Problem and a symbol mapping dict."""
    problem, added = cvar_result
    assert isinstance(problem, Problem)
    assert isinstance(added, dict)


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_added_symbols_have_cvar_prefix(cvar_result):
    """Each original symbol maps to CVAR_{sym}."""
    _, added = cvar_result
    for orig, cvar_sym in added.items():
        assert cvar_sym == f"CVAR_{orig}"


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_threshold_variable_present(cvar_result):
    """A VAR_{sym} threshold variable is added for each requested symbol."""
    problem, _ = cvar_result
    var_syms = {v.symbol for v in problem.variables}
    assert "VAR_f_1" in var_syms
    assert "VAR_f_2" in var_syms
    assert "VAR_f_3" in var_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_auxiliary_variables_per_leaf(cvar_result):
    """Per-leaf auxiliary z_s variables are added for each symbol and leaf."""
    problem, _ = cvar_result
    var_syms = {v.symbol for v in problem.variables}
    for f in ("f_1", "f_2", "f_3"):
        for s in ("s_1", "s_2", "s_3"):
            assert f"{s}_VAR_{f}" in var_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_auxiliary_variable_has_zero_lower_bound(cvar_result):
    """Auxiliary z_s variables have lowerbound=0 to enforce z_s >= 0."""
    problem, _ = cvar_result
    for v in problem.variables:
        if v.symbol.endswith("_VAR_f_1") and v.symbol.startswith("s_"):
            assert v.lowerbound == pytest.approx(0.0)


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_threshold_variable_is_unbounded(cvar_result):
    """The VaR threshold variable has no finite bounds."""
    problem, _ = cvar_result
    var = next(v for v in problem.variables if v.symbol == "VAR_f_1")
    assert var.lowerbound == -float("Inf")
    assert var.upperbound == float("Inf")


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_constraints_per_leaf(cvar_result):
    """One LTE constraint per leaf per symbol is added."""
    problem, _ = cvar_result
    con_syms = {c.symbol for c in (problem.constraints or [])}
    for f in ("f_1", "f_2", "f_3"):
        for s in ("s_1", "s_2", "s_3"):
            assert f"{s}_VAR_{f}_con" in con_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_constraints_are_lte(cvar_result):
    """CVaR auxiliary constraints have LTE type (sym_s - eta - z_s <= 0)."""
    problem, _ = cvar_result
    for con in (problem.constraints or []):
        if con.symbol == "s_1_VAR_f_1_con":
            assert con.cons_type == ConstraintTypeEnum.LTE


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_result_added_as_objective(cvar_result):
    """CVAR elements are added as objectives when the originals are objectives."""
    problem, added = cvar_result
    obj_syms = {o.symbol for o in (problem.objectives or [])}
    for cvar_sym in added.values():
        assert cvar_sym in obj_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_expression_uses_correct_scale(cvar_result):
    """CVaR expression multiplies the weighted sum by 1/(1-alpha)."""
    problem, _ = cvar_result
    obj = next(o for o in (problem.objectives or []) if o.symbol == "CVAR_f_1")
    func = obj.func
    assert func[0] == "Add"
    assert func[1] == "VAR_f_1"
    multiply = func[2]
    assert multiply[0] == "Multiply"
    assert multiply[1] == pytest.approx(_SCALE)


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_expression_uses_scenario_probabilities(cvar_result):
    """CVaR weighted sum uses scenario probabilities as leaf weights."""
    problem, _ = cvar_result
    obj = next(o for o in (problem.objectives or []) if o.symbol == "CVAR_f_1")
    sum_z = obj.func[2][2]
    assert sum_z[0] == "Add"
    terms = {term[2]: term[1] for term in sum_z[1:]}
    assert terms["s_1_VAR_f_1"] == pytest.approx(0.2)
    assert terms["s_2_VAR_f_1"] == pytest.approx(0.3)
    assert terms["s_3_VAR_f_1"] == pytest.approx(0.5)


@pytest.mark.schema
@pytest.mark.scenario
def test_cvar_custom_prefixes(model):
    """var_prefix and cvar_prefix arguments are respected."""
    combined, symbol_maps = build_combined_scenario_problem(model)
    problem, added = add_conditional_value_at_risk(
        model, ["f_1"], alpha=_ALPHA, var_prefix="ETA_", cvar_prefix="RISK_",
        combined=combined, symbol_maps=symbol_maps,
    )
    var_syms = {v.symbol for v in problem.variables}
    assert "ETA_f_1" in var_syms
    assert "s_1_ETA_f_1" in var_syms
    assert added["f_1"] == "RISK_f_1"
    assert any(o.symbol == "RISK_f_1" for o in (problem.objectives or []))


# ---------------------------------------------------------------------------
# add_min_max_robust — schema tests
# ---------------------------------------------------------------------------


@pytest.fixture(name="robust_result")
def robust_result_fixture(model):
    """Return (problem, added_symbols) from add_min_max_robust on f_1, f_2, f_3."""
    combined, symbol_maps = build_combined_scenario_problem(model)
    return add_min_max_robust(model, ["f_1", "f_2", "f_3"], combined=combined, symbol_maps=symbol_maps)


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_returns_problem_and_dict(robust_result):
    """add_min_max_robust returns a Problem and a symbol mapping dict."""
    problem, added = robust_result
    assert isinstance(problem, Problem)
    assert isinstance(added, dict)


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_added_symbols_have_default_prefix(robust_result):
    """Each original symbol maps to robust_{sym} with the default prefix."""
    _, added = robust_result
    for orig, robust_sym in added.items():
        assert robust_sym == f"robust_{orig}"


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_result_added_as_objective(robust_result):
    """Robust elements for objectives are added as objectives."""
    problem, added = robust_result
    obj_syms = {o.symbol for o in (problem.objectives or [])}
    for robust_sym in added.values():
        assert robust_sym in obj_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_objective_is_minimization(robust_result):
    """Robust objectives are always minimization (maximize=False)."""
    problem, added = robust_result
    for robust_sym in added.values():
        obj = next(o for o in (problem.objectives or []) if o.symbol == robust_sym)
        assert obj.maximize is False


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_epigraph_variable_added(robust_result):
    """An epigraph variable _t_robust_{sym} is added for each requested symbol."""
    problem, _ = robust_result
    var_syms = {v.symbol for v in problem.variables}
    assert "_t_robust_f_1" in var_syms
    assert "_t_robust_f_2" in var_syms
    assert "_t_robust_f_3" in var_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_epigraph_variable_is_unbounded(robust_result):
    """The epigraph variable has no finite bounds."""
    problem, _ = robust_result
    t_var = next(v for v in problem.variables if v.symbol == "_t_robust_f_1")
    assert t_var.lowerbound == -float("Inf")
    assert t_var.upperbound == float("Inf")


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_upper_bound_constraints_per_leaf(robust_result):
    """A per-leaf LTE constraint f_s - t <= 0 is added for each symbol and leaf."""
    problem, _ = robust_result
    con_syms = {c.symbol for c in (problem.constraints or [])}
    for f in ("f_1", "f_2", "f_3"):
        for s in ("s_1", "s_2", "s_3"):
            assert f"{s}_robust_{f}_con" in con_syms


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_constraints_are_lte(robust_result):
    """The per-leaf robust constraints have LTE type."""
    problem, _ = robust_result
    for con in (problem.constraints or []):
        if con.symbol.endswith("_robust_f_1_con"):
            assert con.cons_type == ConstraintTypeEnum.LTE


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_element_func_references_epigraph_variable(robust_result):
    """The robust objective's func references the epigraph variable."""
    problem, added = robust_result
    obj = next(o for o in (problem.objectives or []) if o.symbol == added["f_1"])
    assert "_t_robust_f_1" in str(obj.func)


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_element_is_linear(robust_result):
    """The robust objective is linear, convex, and twice differentiable."""
    problem, added = robust_result
    obj = next(o for o in (problem.objectives or []) if o.symbol == added["f_1"])
    assert obj.is_linear
    assert obj.is_convex
    assert obj.is_twice_differentiable


@pytest.mark.schema
@pytest.mark.scenario
def test_robust_custom_prefix(model):
    """The prefix argument is respected."""
    combined, symbol_maps = build_combined_scenario_problem(model)
    problem, added = add_min_max_robust(model, ["f_1"], prefix="wc_", combined=combined, symbol_maps=symbol_maps)
    assert added["f_1"] == "wc_f_1"
    assert any(o.symbol == "wc_f_1" for o in (problem.objectives or []))
