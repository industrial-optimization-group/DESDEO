"""Tests for desdeo.tools.scenario_designs."""

import os
from pathlib import Path

import pytest

from desdeo.problem.scenario import Scenario, ScenarioModel
from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    ExtraFunction,
    Objective,
    Problem,
    ScalarizationFunction,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)
from desdeo.problem.testproblems import simple_scenario_model, summer_cabin_battery_problem_split_scenario
from desdeo.tools import CVXPYSolver, GurobipySolver
from desdeo.tools.scenario_designs import (
    default_design_variables,
    design_from_values,
    evaluate_design,
    find_design,
    fix_variables,
    from_min_space,
    independent_leaf_groups,
    outcomes_from_combined,
    root_variables,
    same_design,
    to_min_space,
)
from desdeo.tools.scenarios import build_combined_scenario_problem

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


@pytest.fixture(name="mixed_problem")
def mixed_problem_fixture() -> Problem:
    """Return a problem with real, integer, binary, and tensor variables."""
    return Problem(
        name="Mixed",
        description="Variables of every type.",
        variables=[
            Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=10.0),
            Variable(name="k", symbol="k", variable_type=VariableTypeEnum.integer, lowerbound=0, upperbound=5),
            Variable(name="b", symbol="b", variable_type=VariableTypeEnum.binary, lowerbound=0, upperbound=1),
            Variable(name="u", symbol="u", variable_type=VariableTypeEnum.real),
            TensorVariable(
                name="T",
                symbol="T",
                variable_type=VariableTypeEnum.real,
                shape=[2, 2],
                lowerbounds=[[0.0, 0.0], [0.0, 0.0]],
                upperbounds=[[1.0, 2.0], [3.0, 4.0]],
            ),
        ],
        objectives=[_objective("f", "x + k + b")],
        extra_funcs=[ExtraFunction(name="e", symbol="e", func="2*x")],
        scalarization_funcs=[ScalarizationFunction(name="s", symbol="s", func="x + e")],
    )


@pytest.fixture(name="tree_model")
def tree_model_fixture() -> ScenarioModel:
    """Return a small two-stage tree: ROOT shares x, node A shares u between a1 and a2."""
    base = Problem(
        name="Tree",
        description="Small scenario tree.",
        variables=[
            Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0),
            Variable(name="u", symbol="u", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0),
        ],
        objectives=[_objective("f", "x + u")],
    )
    return ScenarioModel(
        scenario_tree={"ROOT": ["A", "B"], "A": ["a1", "a2"], "B": ["b1"]},
        base_problem=base,
        scenarios={"a1": Scenario(), "a2": Scenario(), "b1": Scenario()},
        anticipation_stop={"ROOT": ["x"], "A": ["u"]},
    )


@pytest.fixture(name="conflict_model")
def conflict_model_fixture() -> ScenarioModel:
    """Return a two-leaf model where f1 = y is minimised and f2 = y maximised; x is shared at ROOT."""
    base = Problem(
        name="Conflict",
        description="Two conflicting objectives of the recourse variable y.",
        variables=[
            Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=1.0),
            Variable(name="y", symbol="y", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=10.0),
        ],
        objectives=[
            _objective("f1", "y + 0*x", ideal=0.0, nadir=10.0),
            _objective("f2", "y + 0*x", maximize=True, ideal=10.0, nadir=0.0),
        ],
    )
    return ScenarioModel(
        scenario_tree={"ROOT": ["s1", "s2"]},
        base_problem=base,
        scenarios={"s1": Scenario(), "s2": Scenario()},
        anticipation_stop={"ROOT": ["x"]},
    )


@pytest.fixture(name="pool_variable_model")
def pool_variable_model_fixture() -> ScenarioModel:
    """Return a model whose leaves add the pool-only variable z with leaf-specific lower limits."""
    base = Problem(
        name="Pool variable",
        description="Base problem without the variable the scenarios add.",
        variables=[
            Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=10.0),
        ],
        objectives=[_objective("f", "x", ideal=0.0, nadir=10.0)],
    )
    return ScenarioModel(
        scenario_tree={"ROOT": ["s1", "s2"]},
        base_problem=base,
        variables=[Variable(name="z", symbol="z", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=5.0)],
        constraints=[
            Constraint(name="c (s1)", symbol="c", func="1 - z", cons_type=ConstraintTypeEnum.LTE),
            Constraint(name="c (s2)", symbol="c", func="2 - z", cons_type=ConstraintTypeEnum.LTE),
        ],
        objectives=[_objective("g", "z", ideal=0.0, nadir=5.0)],
        scenarios={
            "s1": Scenario(variables={"z": 0}, constraints={"c": 0}, objectives={"g": 0}),
            "s2": Scenario(variables={"z": 0}, constraints={"c": 1}, objectives={"g": 0}),
        },
        anticipation_stop={"ROOT": ["x"]},
    )


def test_root_and_default_design_variables(model):
    """The simple model has x_1 at ROOT; the summer cabin has scalar y, E, n plus tensors, all defaulted."""
    assert root_variables(model) == ["x_1"]
    assert default_design_variables(model) == ["x_1"]

    cabin = summer_cabin_battery_problem_split_scenario()
    root = ["y", "E", "n", "c_s1", "d_s1", "soc_s1", "buy_s1", "sell_s1"]
    assert root_variables(cabin) == root
    assert default_design_variables(cabin) == root


def test_default_design_variables_without_root(model):
    """A model with no ROOT anticipation_stop has no design variables."""
    with pytest.raises(ValueError, match="ROOT"):
        default_design_variables(model.model_copy(update={"anticipation_stop": {}}))


def test_fix_variables(mixed_problem):
    """Every variable type can be fixed, and integer values are rounded."""
    fixed = fix_variables(mixed_problem, {"x": 2.5, "k": 3.0000001, "b": 1, "T": [[0.5, 1.0], [1.5, 2.0]]})
    variables = {var.symbol: var for var in fixed.variables}

    assert variables["x"].lowerbound == variables["x"].upperbound == variables["x"].initial_value == 2.5
    assert variables["k"].lowerbound == variables["k"].upperbound == 3
    assert isinstance(variables["k"].lowerbound, int)
    assert variables["b"].lowerbound == variables["b"].upperbound == 1
    assert variables["T"].get_lowerbound_values() == [[0.5, 1.0], [1.5, 2.0]]
    assert variables["T"].get_upperbound_values() == [[0.5, 1.0], [1.5, 2.0]]
    assert variables["T"].get_initial_values() == [[0.5, 1.0], [1.5, 2.0]]
    assert variables["u"] == mixed_problem.variables[3]


def test_fix_variables_preserves_other_fields(mixed_problem):
    """Fields other than the fixed variables are unchanged."""
    fixed = fix_variables(mixed_problem, {"x": 1.0})
    assert fixed.model_dump(exclude={"variables"}) == mixed_problem.model_dump(exclude={"variables"})
    assert fixed.constants is None
    assert fixed.variables[1:] == mixed_problem.variables[1:]


@pytest.mark.parametrize(
    "values",
    [{"x": 10.5}, {"k": -1}, {"b": 2}, {"T": [[0.5, 2.5], [1.0, 1.0]]}, {"T": [0.5, 0.5]}],
)
def test_fix_variables_invalid_value(mixed_problem, values):
    """Values outside the bounds or of the wrong shape are rejected."""
    with pytest.raises(ValueError):
        fix_variables(mixed_problem, values)


def test_fix_variables_unknown_symbol(mixed_problem):
    """Fixing an unknown variable raises KeyError."""
    with pytest.raises(KeyError):
        fix_variables(mixed_problem, {"nope": 1.0})


def test_same_design_and_find_design(mixed_problem):
    """Real values match within range-relative tolerance; integers must match exactly."""
    variables = {var.symbol: var for var in mixed_problem.variables}
    a = {"x": 2.0, "k": 3, "T": [[0.5, 1.0], [1.5, 2.0]]}

    assert same_design(a, {**a, "x": 2.0009}, variables)  # 1e-4 * 10 range
    assert not same_design(a, {**a, "x": 2.002}, variables)
    assert same_design(a, {**a, "k": 3.0000001}, variables)
    assert not same_design(a, {**a, "k": 4}, variables)
    assert same_design(a, {**a, "T": [[0.50001, 1.0], [1.5, 2.0]]}, variables)
    assert not same_design(a, {**a, "T": [[0.5, 1.0], [1.5, 2.01]]}, variables)
    assert not same_design(a, {"x": 2.0, "k": 3}, variables)

    # No bounds: only atol applies.
    assert same_design({"u": 1.0}, {"u": 1.0 + 1e-7}, variables)
    assert not same_design({"u": 1.0}, {"u": 1.0 + 1e-5}, variables)

    registry = [{**a, "x": 5.0}, {**a, "k": 4}, {**a, "x": 2.0001}, a]
    assert find_design(registry, a, variables) == 2
    assert find_design(registry, {**a, "x": 9.0}, variables) is None
    assert find_design([], a, variables) is None


def test_design_from_values():
    """Design values are picked by symbol."""
    assert design_from_values({"x_1": 1.0, "x_2": 2.0, "_alpha": 0.0}, ["x_1"]) == {"x_1": 1.0}


def test_independent_leaf_groups_simple(model):
    """With the ROOT variable fixed the leaves are independent; otherwise they are all coupled."""
    assert independent_leaf_groups(model, ["x_1"]) == [["s_1"], ["s_2"], ["s_3"]]
    assert independent_leaf_groups(model, []) == [["s_1", "s_2", "s_3"]]


def test_independent_leaf_groups_summer_cabin():
    """Unfixed shared schedules couple the summer cabin leaves."""
    cabin = summer_cabin_battery_problem_split_scenario()
    assert independent_leaf_groups(cabin, ["y", "E", "n"]) == [["S1a", "S1b", "S2a", "S2b"]]
    assert independent_leaf_groups(cabin, root_variables(cabin)) == [["S1a", "S1b"], ["S2a", "S2b"]]


def test_independent_leaf_groups_tree(tree_model):
    """Coupling follows the nodes whose shared variables are not fixed."""
    assert independent_leaf_groups(tree_model, ["x"]) == [["a1", "a2"], ["b1"]]
    assert independent_leaf_groups(tree_model, ["x", "u"]) == [["a1"], ["a2"], ["b1"]]
    assert independent_leaf_groups(tree_model, ["u"]) == [["a1", "a2", "b1"]]


def test_outcomes_from_combined(model):
    """Combined objective values are split per leaf under their original symbols."""
    combined, symbol_maps = build_combined_scenario_problem(model)
    values = {obj.symbol: float(i) for i, obj in enumerate(combined.objectives)}
    outcomes = outcomes_from_combined(values, symbol_maps)

    assert set(outcomes) == {"s_1", "s_2", "s_3"}
    for leaf, objectives in outcomes.items():
        assert set(objectives) == {"f_1", "f_2", "f_3"}
        for sym, value in objectives.items():
            assert value == values[symbol_maps["objectives"][sym][leaf]]


def test_min_space():
    """Maximised objectives are negated, and the conversion is undone by from_min_space."""
    values = {"f_1": 1.0, "f_2": 2.0}
    maximize = {"f_1": True, "f_2": False}
    assert to_min_space(values, maximize) == {"f_1": -1.0, "f_2": 2.0}
    assert from_min_space(to_min_space(values, maximize), maximize) == values


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("design", [{"x_1": 1.0}, {}], ids=["independent", "coupled"])
def test_evaluate_design(model, solver, design):
    """Every leaf is solved, and the design variable is the same in every leaf."""
    reference_point = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}
    outcomes = evaluate_design(model, design, solver, reference_point)

    assert list(outcomes) == ["s_1", "s_2", "s_3"]
    x_1 = {outcome.variables["x_1"] for outcome in outcomes.values()}
    for outcome in outcomes.values():
        assert outcome.status, outcome.message
        assert set(outcome.objectives) == {"f_1", "f_2", "f_3"}
        assert set(outcome.variables) == {"x_1", "x_2"}
    if design:
        assert x_1 == {1.0}
    else:
        assert max(x_1) - min(x_1) < 1e-6


@pytest.mark.parametrize("solver", SOLVERS)
def test_evaluate_design_agrees_with_coupled(model, solver):
    """Fixing the root variable at the coupled optimum reproduces the coupled ASF values."""
    reference_point = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}
    coupled = evaluate_design(model, {}, solver, reference_point)
    design = {"x_1": coupled["s_1"].variables["x_1"]}
    independent = evaluate_design(model, design, solver, reference_point)

    # Every objective has reference value 0 and weight 200, so the ASF max term is max(f) / 200.
    for leaf, outcome in independent.items():
        assert max(outcome.objectives.values()) == pytest.approx(max(coupled[leaf].objectives.values()), abs=1e-3)


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("design", [{"x_1": 1.0}, {}], ids=["independent", "coupled"])
def test_evaluate_design_sparse_objectives(sparse_model, solver, design):
    """An objective that only one leaf has is reported only for that leaf."""
    reference_point = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0, "f_4": -5.2}
    outcomes = evaluate_design(sparse_model, design, solver, reference_point)

    assert all(outcome.status for outcome in outcomes.values())
    assert set(outcomes["s_2"].objectives) == {"f_1", "f_2", "f_3", "f_4"}
    assert set(outcomes["s_1"].objectives) == {"f_1", "f_2", "f_3"}
    assert set(outcomes["s_3"].objectives) == {"f_1", "f_2", "f_3"}
    assert outcomes["s_2"].objectives["f_4"] == pytest.approx(outcomes["s_2"].variables["x_2"])


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("maximize", [True, False])
def test_evaluate_design_maximize(model, solver, maximize):
    """A maximised objective is pushed towards its aspiration and reported in its original direction."""
    ideal, nadir = (6.1, -5.2) if maximize else (-5.2, 6.1)
    base = model.base_problem.model_copy(
        update={"objectives": [_objective("f_3", "x_2", maximize=maximize, ideal=ideal, nadir=nadir)]}
    )
    outcomes = evaluate_design(model.with_base_problem(base), {"x_1": 1.0}, solver, {"f_3": ideal})

    for outcome in outcomes.values():
        assert outcome.status, outcome.message
        assert outcome.objectives["f_3"] == pytest.approx(outcome.variables["x_2"], abs=1e-6)
        assert outcome.variables["x_2"] == pytest.approx(ideal, abs=1e-4)


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("design", [{"x": 0.5}, {}], ids=["independent", "coupled"])
@pytest.mark.parametrize(
    ("ranges", "expected"),
    [(None, 4.0), ({"f2": (40.0, 10.0)}, 3.0)],
    ids=["equal", "asymmetric"],
)
def test_evaluate_design_ranges(conflict_model, solver, design, ranges, expected):
    """The ranges weight conflicting objectives: max((y - 2) / 10, (6 - y) / r2) is minimised at y."""
    # Equal ranges: y - 2 = 6 - y gives y = 4.  r2 = 30: 3 * (y - 2) = 6 - y gives y = 3.
    outcomes = evaluate_design(conflict_model, design, solver, {"f1": 2.0, "f2": 6.0}, ranges=ranges)

    for outcome in outcomes.values():
        assert outcome.status, outcome.message
        assert outcome.variables["y"] == pytest.approx(expected, abs=1e-4)
        assert outcome.objectives == pytest.approx({"f1": expected, "f2": expected}, abs=1e-4)


@pytest.mark.parametrize("solver", SOLVERS)
def test_evaluate_design_leaf_reference_points(conflict_model, solver):
    """A leaf with its own reference point uses it; the other leaves use the common one."""
    # s2: max(y / 10, (10 - y) / 10) is minimised at y = 5.
    outcomes = evaluate_design(
        conflict_model,
        {"x": 0.5},
        solver,
        {"f1": 2.0, "f2": 6.0},
        leaf_reference_points={"s2": {"f1": 0.0, "f2": 10.0}},
    )

    assert outcomes["s1"].variables["y"] == pytest.approx(4.0, abs=1e-4)
    assert outcomes["s2"].variables["y"] == pytest.approx(5.0, abs=1e-4)


@pytest.mark.parametrize("solver", SOLVERS)
def test_evaluate_design_leaf_ranges(conflict_model, solver):
    """A leaf with its own ranges uses them; the other leaves use the common ranges."""
    # s2 with r2 = 30: 3 * (y - 2) = 6 - y gives y = 3.
    outcomes = evaluate_design(
        conflict_model, {"x": 0.5}, solver, {"f1": 2.0, "f2": 6.0}, leaf_ranges={"s2": {"f2": (40.0, 10.0)}}
    )

    assert outcomes["s1"].variables["y"] == pytest.approx(4.0, abs=1e-4)
    assert outcomes["s2"].variables["y"] == pytest.approx(3.0, abs=1e-4)


@pytest.mark.parametrize("solver", SOLVERS)
def test_evaluate_design_leaf_reference_points_coupled(tree_model, solver):
    """Per-leaf reference points and ranges act inside a group coupled by the unfixed shared u."""
    base = tree_model.base_problem.model_copy(
        update={
            "objectives": [
                _objective("f1", "u + 0*x", ideal=0.0, nadir=1.0),
                _objective("f2", "u + 0*x", maximize=True, ideal=1.0, nadir=0.0),
            ]
        }
    )
    model = tree_model.with_base_problem(base)
    a1_rp, a2_rp = {"f1": 0.1, "f2": 0.5}, {"f1": 0.5, "f2": 0.9}
    group_ranges = {
        "a1": {"f1": (0.0, 0.5), "f2": (0.5, 0.0)},
        "a2": {"f1": (0.0, 0.25), "f2": (1.0, 0.0)},
    }

    def shared_u(leaf_rps):
        outcomes = evaluate_design(
            model, {"x": 0.5}, solver, {"f1": 0.8, "f2": 0.8}, leaf_reference_points=leaf_rps, leaf_ranges=group_ranges
        )
        assert outcomes["a1"].variables["u"] == pytest.approx(outcomes["a2"].variables["u"], abs=1e-6)
        # b1 is solved alone at the common reference point and unit ranges: max(u - 0.8, 0.8 - u).
        assert outcomes["b1"].variables["u"] == pytest.approx(0.8, abs=1e-4)
        return outcomes["a1"].variables["u"]

    # The a1 term max(2 (u - 0.1), 2 (0.5 - u)) has its kink at 0.3 with slopes -2, 2; the a2 term
    # max(4 (u - 0.5), 0.9 - u) has its kink at 0.58 with slopes -1, 4.  Their sum is minimised at 0.3.
    assert shared_u({"a1": a1_rp, "a2": a2_rp}) == pytest.approx(0.3, abs=1e-4)
    # a1's point in both leaves: kinks at 0.3 and 0.18 (slopes -1, 4), minimised at 0.18.
    assert shared_u({"a1": a1_rp, "a2": a1_rp}) == pytest.approx(0.18, abs=1e-4)
    # a2's point in both leaves: kinks at 0.7 (slopes -2, 2) and 0.58, minimised at 0.58.
    assert shared_u({"a1": a2_rp, "a2": a2_rp}) == pytest.approx(0.58, abs=1e-4)


@pytest.mark.gurobipy
def test_evaluate_design_unit_weights_warning(conflict_model):
    """An objective without a usable range gives unit weights for all objectives and a warning."""
    with pytest.warns(UserWarning, match="unit ASF weights"):
        outcomes = evaluate_design(
            conflict_model, {"x": 0.5}, GurobipySolver, {"f1": 2.0, "f2": 6.0}, ranges={"f2": (40.0, 40.0)}
        )
    assert outcomes["s1"].variables["y"] == pytest.approx(4.0, abs=1e-4)


@pytest.mark.parametrize("solver", SOLVERS)
def test_evaluate_design_tree(tree_model, solver):
    """Leaves under node A share the unfixed u; the leaf under B is solved on its own."""
    outcomes = evaluate_design(tree_model, {"x": 0.5}, solver, {"f": 0.0}, ranges={"f": (0.0, 2.0)})

    assert list(outcomes) == ["a1", "a2", "b1"]
    for outcome in outcomes.values():
        assert outcome.status, outcome.message
        assert set(outcome.variables) == {"x", "u"}
        assert outcome.variables["x"] == pytest.approx(0.5)
        assert outcome.variables["u"] == pytest.approx(0.0, abs=1e-6)
        assert outcome.objectives["f"] == pytest.approx(0.5, abs=1e-6)


@pytest.mark.parametrize("solver", SOLVERS)
def test_evaluate_design_pool_only_variable_coupled(pool_variable_model, solver):
    """A pool-only variable gets a separate value per leaf when the leaves are solved together."""
    outcomes = evaluate_design(pool_variable_model, {}, solver, {"f": 0.0, "g": 0.0})

    assert outcomes["s1"].status, outcomes["s1"].message
    assert outcomes["s2"].status, outcomes["s2"].message
    assert outcomes["s1"].variables["z"] == pytest.approx(1.0, abs=1e-6)
    assert outcomes["s2"].variables["z"] == pytest.approx(2.0, abs=1e-6)
    assert outcomes["s1"].objectives["g"] == pytest.approx(1.0, abs=1e-6)
    assert outcomes["s2"].objectives["g"] == pytest.approx(2.0, abs=1e-6)
    assert outcomes["s1"].variables["x"] == pytest.approx(outcomes["s2"].variables["x"])


@pytest.mark.parametrize("solver", SOLVERS)
def test_evaluate_design_infeasible(model, solver):
    """An infeasible leaf gets status False instead of raising."""
    # s_2 requires 5*x_1 <= 5.
    outcomes = evaluate_design(model, {"x_1": 2.0}, solver, {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0})

    assert outcomes["s_1"].status
    assert outcomes["s_3"].status
    assert not outcomes["s_2"].status
    assert outcomes["s_2"].objectives == {}


@pytest.mark.gurobipy
def test_evaluate_design_leaves(model):
    """Only the requested leaves are returned."""
    reference_point = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}
    assert list(evaluate_design(model, {"x_1": 1.0}, GurobipySolver, reference_point, leaves=["s_2"])) == ["s_2"]
    assert list(evaluate_design(model, {}, GurobipySolver, reference_point, leaves=["s_3", "s_1"])) == ["s_1", "s_3"]


@pytest.mark.gurobipy
def test_evaluate_design_invalid_arguments(model):
    """Unknown leaves and design variables that a leaf lacks are rejected before solving."""
    reference_point = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}
    with pytest.raises(ValueError, match="nope"):
        evaluate_design(model, {"x_1": 1.0}, GurobipySolver, reference_point, leaves=["s_1", "nope"])
    with pytest.raises(ValueError, match="not variables of leaf"):
        evaluate_design(model, {"x_1": 1.0, "nope": 1.0}, GurobipySolver, reference_point)


@pytest.mark.gurobipy
def test_evaluate_design_reference_point_without_leaf_objectives(sparse_model):
    """A reference point that covers none of a leaf's objectives is rejected."""
    with pytest.raises(ValueError, match="s_1"):
        evaluate_design(sparse_model, {"x_1": 1.0}, GurobipySolver, {"f_4": 0.0})


@pytest.mark.slow
@pytest.mark.gurobipy
@pytest.mark.githubskip
def test_evaluate_design_summer_cabin():
    """The summer cabin investment design can be evaluated in every leaf."""
    cabin = summer_cabin_battery_problem_split_scenario()
    design = {"y": 1, "E": 20.0, "n": 10}
    outcomes = evaluate_design(cabin, design, GurobipySolver, {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0})

    assert list(outcomes) == ["S1a", "S1b", "S2a", "S2b"]
    for outcome in outcomes.values():
        assert outcome.status, outcome.message
        assert {sym: outcome.variables[sym] for sym in design} == pytest.approx(design)


@pytest.mark.slow
@pytest.mark.gurobipy
@pytest.mark.githubskip
@pytest.mark.skipif("DESDEO_DH_DIR" not in os.environ, reason="DESDEO_DH_DIR is not set.")
def test_evaluate_design_dh():
    """The default design of the district heating model can be evaluated in two leaves."""
    model = ScenarioModel.model_validate_json((Path(os.environ["DESDEO_DH_DIR"]) / "dh_p9.json").read_text())
    variables = {var.symbol: var for var in model.base_problem.variables}
    design = {
        sym: (variables[sym].lowerbound + variables[sym].upperbound) / 2 for sym in default_design_variables(model)
    }
    leaves = list(model.leaf_scenarios)[:2]
    reference_point = dict.fromkeys((obj.symbol for obj in model.base_problem.objectives), 0.0)
    outcomes = evaluate_design(model, design, GurobipySolver, reference_point, leaves=leaves)

    assert list(outcomes) == leaves
    for outcome in outcomes.values():
        assert outcome.status
        assert {sym: outcome.variables[sym] for sym in design} == pytest.approx(design)
