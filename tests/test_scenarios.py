"""Tests for the ScenarioModel and Scenario classes."""

import pytest
from pydantic import ValidationError

from desdeo.problem import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    Objective,
    Problem,
    Scenario,
    ScenarioModel,
    Variable,
    VariableTypeEnum,
)
from desdeo.problem.testproblems import simple_scenario_model


@pytest.fixture
def base_problem():
    """Base problem for testing scenario modifications."""
    return Problem(
        name="Base problem",
        description="A simple base problem for scenario tests.",
        constants=[Constant(name="c_1", symbol="c_1", value=3.0)],
        variables=[
            Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=10),
            Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=10),
        ],
        objectives=[
            Objective(name="f_1", symbol="f_1", func="x_1 + x_2", maximize=False),
            Objective(name="f_2", symbol="f_2", func="x_1 - x_2", maximize=False),
        ],
        constraints=[
            Constraint(name="con_1", symbol="con_1", cons_type=ConstraintTypeEnum.LTE, func="x_1 + x_2 - 15"),
        ],
    )


@pytest.fixture
def scenario_model(base_problem):
    """Scenario model for testing."""
    return ScenarioModel(
        scenario_tree={"ROOT": ["s_1", "s_2"], "s_1": [], "s_2": []},
        base_problem=base_problem,
        constants=[Constant(name="c_1 alt", symbol="c_1", value=10.0)],
        variables=[
            Variable(name="x_1 alt", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=-5, upperbound=5),
        ],
        objectives=[
            Objective(name="f_1 alt", symbol="f_1", func="x_1 * x_2", maximize=False),
        ],
        constraints=[
            Constraint(name="con_1 alt", symbol="con_1", cons_type=ConstraintTypeEnum.LTE, func="x_1 + x_2 - 5"),
            Constraint(name="con_2", symbol="con_2", cons_type=ConstraintTypeEnum.LTE, func="x_1 - x_2 - 3"),
        ],
        scenarios={
            "s_1": Scenario(constants=["c_1"], variables=["x_1"], objectives=["f_1"], constraints=["con_1"]),
            "s_2": Scenario(constraints=["con_2"]),
        },
    )


@pytest.mark.schema
def test_scenario_model_construction(scenario_model):
    """ScenarioModel with valid pools and scenarios constructs without error."""
    assert "s_1" in scenario_model.scenarios
    assert "s_2" in scenario_model.scenarios


@pytest.mark.schema
def test_scenario_invalid_scenario_name(base_problem):
    """Referencing a scenario name not in scenario_tree raises a validation error."""
    with pytest.raises(ValidationError):
        ScenarioModel(
            scenario_tree={"ROOT": ["s_1"], "s_1": []},
            base_problem=base_problem,
            constants=[Constant(name="c_1 alt", symbol="c_1", value=10.0)],
            scenarios={"nonexistent": Scenario(constants=["c_1"])},
        )


@pytest.mark.schema
def test_scenario_invalid_pool_symbol(base_problem):
    """Referencing a symbol not present in the pool raises a validation error."""
    with pytest.raises(ValidationError):
        ScenarioModel(
            scenario_tree={"ROOT": ["s_1"], "s_1": []},
            base_problem=base_problem,
            scenarios={"s_1": Scenario(constants=["c_does_not_exist"])},
        )


@pytest.mark.schema
def test_get_scenario_problem_replaces_constant(scenario_model):
    """Constants referenced in a scenario are replaced in the returned problem."""
    problem = scenario_model.get_scenario_problem("s_1")
    constant = next(c for c in problem.constants if c.symbol == "c_1")
    assert constant.value == 10.0


@pytest.mark.schema
def test_get_scenario_problem_replaces_variable(scenario_model):
    """Variables referenced in a scenario are replaced in the returned problem."""
    problem = scenario_model.get_scenario_problem("s_1")
    variable = next(v for v in problem.variables if v.symbol == "x_1")
    assert variable.lowerbound == -5
    assert variable.upperbound == 5


@pytest.mark.schema
def test_get_scenario_problem_replaces_objective(scenario_model):
    """Objectives referenced in a scenario are replaced in the returned problem."""
    base_f1_func = next(o.func for o in scenario_model.base_problem.objectives if o.symbol == "f_1")
    problem = scenario_model.get_scenario_problem("s_1")
    scenario_f1_func = next(o.func for o in problem.objectives if o.symbol == "f_1")
    assert scenario_f1_func != base_f1_func


@pytest.mark.schema
def test_get_scenario_problem_replaces_constraint(scenario_model):
    """Constraints already in the base problem are replaced when referenced in a scenario."""
    problem = scenario_model.get_scenario_problem("s_1")
    constraint = next(c for c in problem.constraints if c.symbol == "con_1")
    base_constraint = next(c for c in scenario_model.base_problem.constraints if c.symbol == "con_1")
    assert constraint.func != base_constraint.func


@pytest.mark.schema
def test_get_scenario_problem_adds_new_constraint(scenario_model):
    """Constraints not present in the base problem are added when referenced in a scenario."""
    base_symbols = {c.symbol for c in scenario_model.base_problem.constraints}
    assert "con_2" not in base_symbols

    problem = scenario_model.get_scenario_problem("s_2")
    scenario_symbols = {c.symbol for c in problem.constraints}
    assert "con_2" in scenario_symbols


@pytest.mark.schema
def test_get_scenario_problem_empty_scenario_unchanged(base_problem):
    """A scenario with no element references returns a problem identical to the base."""
    model = ScenarioModel(
        scenario_tree={"ROOT": ["s_1"], "s_1": []},
        base_problem=base_problem,
        scenarios={"s_1": Scenario()},
    )
    problem = model.get_scenario_problem("s_1")
    assert problem == base_problem


@pytest.mark.schema
def test_get_scenario_problem_unknown_name(scenario_model):
    """Requesting a scenario that does not exist raises a ValueError."""
    with pytest.raises(ValueError, match="not found"):
        scenario_model.get_scenario_problem("nonexistent")


@pytest.mark.schema
def test_pool_element_reused_across_scenarios(base_problem):
    """The same pool element can be referenced in multiple scenarios without duplication."""
    shared_constraint = Constraint(name="shared", symbol="con_1", cons_type=ConstraintTypeEnum.LTE, func="x_1 - 1")
    model = ScenarioModel(
        scenario_tree={"ROOT": ["s_1", "s_2"], "s_1": [], "s_2": []},
        base_problem=base_problem,
        constraints=[shared_constraint],
        scenarios={
            "s_1": Scenario(constraints=["con_1"]),
            "s_2": Scenario(constraints=["con_1"]),
        },
    )
    p1 = model.get_scenario_problem("s_1")
    p2 = model.get_scenario_problem("s_2")
    c1 = next(c for c in p1.constraints if c.symbol == "con_1")
    c2 = next(c for c in p2.constraints if c.symbol == "con_1")
    assert c1.func == c2.func == shared_constraint.func


@pytest.mark.schema
def test_scenario_tree_list_coercion(base_problem):
    """Providing a list for scenario_tree is coerced to {'ROOT': [...], 's_1': [], 's_2': []}."""
    model = ScenarioModel(
        scenario_tree=["s_1", "s_2"],
        base_problem=base_problem,
        scenarios={"s_1": Scenario(), "s_2": Scenario()},
    )
    assert model.scenario_tree == {"ROOT": ["s_1", "s_2"], "s_1": [], "s_2": []}


@pytest.mark.schema
def test_simple_scenario_model_s1():
    """Scenario s_1 contains the correct objectives, constraints, and no extra functions."""
    model = simple_scenario_model()
    problem = model.get_scenario_problem("s_1")

    symbols = problem.get_all_symbols()

    assert len(problem.objectives) == 3
    assert len(problem.constraints) == 3
    assert problem.extra_funcs is None or len(problem.extra_funcs) == 0

    assert "f_1" in symbols
    assert "f_2" in symbols
    assert "f_3" in symbols
    assert "f_4" not in symbols
    assert "f_5" not in symbols

    assert "con_1" in symbols
    assert "con_2" not in symbols
    assert "con_3" in symbols
    assert "con_4" in symbols

    assert "extra_1" not in symbols
    assert "x_1" in symbols
    assert "x_2" in symbols
    assert "c_1" in symbols


@pytest.mark.schema
def test_simple_scenario_model_s2():
    """Scenario s_2 contains the correct objectives, constraints, and extra function."""
    model = simple_scenario_model()
    problem = model.get_scenario_problem("s_2")

    symbols = problem.get_all_symbols()

    assert len(problem.objectives) == 4
    assert len(problem.constraints) == 3
    assert len(problem.extra_funcs) == 1

    assert "f_1" not in symbols
    assert "f_2" in symbols
    assert "f_3" in symbols
    assert "f_4" in symbols
    assert "f_5" in symbols

    assert "con_1" not in symbols
    assert "con_2" in symbols
    assert "con_3" in symbols
    assert "con_4" in symbols

    assert "extra_1" in symbols
    assert "x_1" in symbols
    assert "x_2" in symbols
    assert "c_1" in symbols
