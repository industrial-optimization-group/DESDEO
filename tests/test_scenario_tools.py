"""Tests for desdeo.tools.scenarios using simple_scenario_model."""

import pytest

from desdeo.problem.schema import Problem
from desdeo.problem.testproblems import simple_scenario_model
from desdeo.tools.scenarios import build_combined_scenario_problem, build_scenario_problem
from desdeo.tools.stochastic import expected_asf


@pytest.fixture(name="model")
def simple_model_fixture():
    """Return the simple_scenario_model test instance."""
    return simple_scenario_model()


@pytest.fixture(name="combined")
def combined_problem_fixture(model):
    """Return the combined Problem built from the simple_scenario_model."""
    return build_combined_scenario_problem(model)


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
    assert "x_1_s_1" not in symbols
    assert "x_1_s_2" not in symbols
    assert "x_1_s_3" not in symbols


@pytest.mark.scenario
def test_scenario_specific_variable_gets_leaf_suffix(combined):
    """x_2 is not non-anticipative so it is copied once per leaf scenario."""
    symbols = {v.symbol for v in combined.variables}
    assert "x_2_s_1" in symbols
    assert "x_2_s_2" in symbols
    assert "x_2_s_3" in symbols
    assert "x_2" not in symbols


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_scenario_specific_constants_renamed(combined):
    """c_1 has different values per scenario so each gets a per-leaf name."""
    symbols = {c.symbol for c in (combined.constants or [])}
    assert "c_1_s_1" in symbols
    assert "c_1_s_2" in symbols
    assert "c_1_s_3" in symbols
    assert "c_1" not in symbols


@pytest.mark.scenario
def test_scenario_specific_constant_values(combined):
    """Per-scenario c_1 constants carry the correct values from the pool."""
    const_map = {c.symbol: c.value for c in (combined.constants or [])}
    assert const_map["c_1_s_1"] == pytest.approx(1.0)
    assert const_map["c_1_s_2"] == pytest.approx(5.0)
    assert const_map["c_1_s_3"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Objectives
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_combined_objective_count(combined):
    """Each of 3 scenarios contributes 3 objectives → 9 total."""
    assert len(combined.objectives) == 9


@pytest.mark.scenario
def test_all_objectives_have_leaf_suffix(combined):
    """Every objective symbol ends with a leaf suffix since none are shared."""
    suffixes = {"_s_1", "_s_2", "_s_3"}
    for obj in combined.objectives:
        assert any(obj.symbol.endswith(s) for s in suffixes), f"Objective '{obj.symbol}' has no leaf suffix"


@pytest.mark.scenario
def test_objective_variable_references_renamed(combined):
    """Scenario-specific objectives reference the renamed x_2_<leaf> symbol."""
    obj_map = {o.symbol: str(o.func) for o in combined.objectives}
    assert "x_2_s_1" in obj_map["f_3_s_1"]
    assert "x_2_s_2" in obj_map["f_3_s_2"]
    assert "x_2_s_3" in obj_map["f_3_s_3"]


@pytest.mark.scenario
def test_objective_constant_references_renamed(combined):
    """Objectives that use c_1 reference the per-scenario constant name."""
    obj_map = {o.symbol: str(o.func) for o in combined.objectives}
    assert "c_1_s_2" in obj_map["f_1_s_2"]
    assert "c_1_s_3" in obj_map["f_1_s_3"]
    assert "c_1" not in obj_map["f_1_s_1"]


@pytest.mark.scenario
def test_shared_x1_not_renamed_in_objectives(combined):
    """x_1 appears unchanged (no suffix) in all objective func strings."""
    for obj in combined.objectives:
        func_str = str(obj.func)
        assert "x_1" in func_str, f"x_1 missing in {obj.symbol}: {func_str}"
        assert "x_1_s" not in func_str, f"x_1 incorrectly suffixed in {obj.symbol}: {func_str}"


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
    assert "con_3_s_1" in syms
    assert "con_3_s_2" in syms
    assert "con_3_s_3" in syms


@pytest.mark.scenario
def test_con1_only_for_leaves_that_have_it(combined):
    """con_1 is only in s_1 and s_3; s_2 should not get a copy."""
    syms = {c.symbol for c in combined.constraints}
    assert "con_1_s_1" in syms
    assert "con_1_s_3" in syms
    assert "con_1_s_2" not in syms


# ---------------------------------------------------------------------------
# Extra functions
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_extra_funcs_renamed_per_leaf(combined):
    """extra_1 has different funcs in s_1 and s_2, so both get a leaf suffix."""
    syms = {e.symbol for e in (combined.extra_funcs or [])}
    assert "extra_1_s_1" in syms
    assert "extra_1_s_2" in syms
    assert "extra_1" not in syms


@pytest.mark.scenario
def test_extra_func_values_correct(combined):
    """extra_1_s_1 uses '2*x_1' and extra_1_s_2 uses '5*x_1' (stored as MathJSON)."""
    ef_map = {e.symbol: e.func for e in (combined.extra_funcs or [])}
    assert ef_map["extra_1_s_1"] == ["Multiply", 2, "x_1"]
    assert ef_map["extra_1_s_2"] == ["Multiply", 5, "x_1"]


# ---------------------------------------------------------------------------
# Symbol uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.scenario
def test_all_symbols_unique(combined):
    """Every symbol in the combined problem is unique."""
    all_symbols = combined.get_all_symbols()
    assert len(all_symbols) == len(set(all_symbols))


# ---------------------------------------------------------------------------
# expected_asf
# ---------------------------------------------------------------------------

_REF = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}
_IDEAL = {"f_1": -100.0, "f_2": -100.0, "f_3": -100.0}
_NADIR = {"f_1": 100.0, "f_2": 100.0, "f_3": 100.0}


@pytest.fixture(name="asf_result")
def expected_asf_result_fixture(model):
    """Return (problem, symbol) from expected_asf on the simple_scenario_model."""
    return expected_asf(model, "asf", _REF, ideal=_IDEAL, nadir=_NADIR)


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
    assert "asf_s_1" in scal_syms
    assert "asf_s_2" in scal_syms
    assert "asf_s_3" in scal_syms


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
    assert terms["asf_s_1"] == pytest.approx(0.2)
    assert terms["asf_s_2"] == pytest.approx(0.3)
    assert terms["asf_s_3"] == pytest.approx(0.5)
