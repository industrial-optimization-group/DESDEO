"""Tests for the MathJSON parser."""
import copy
import math
import json
from pathlib import Path

import numpy.testing as npt
import polars as pl
import pyomo.environ as pyomo
import pytest

from desdeo.problem.evaluator import GenericEvaluator
from desdeo.problem.infix_parser import InfixExpressionParser
from desdeo.problem.json_parser import FormatEnum, MathParser, replace_str
from desdeo.problem.schema import (
    Constant,
    Constraint,
    ExtraFunction,
    Objective,
    Problem,
    ScalarizationFunction,
    Variable,
)
from desdeo.problem.testproblems import binh_and_korn


@pytest.fixture
def four_bar_truss_problem():
    """Loads the four bar truss problem."""
    with Path("tests/example_problem.json").open("r") as f:
        return json.load(f)


@pytest.fixture
def extra_functions_problem():
    """Defines a problem with extra functions and scalarizations for testing."""
    variables = [
        Variable(name="Test 1", symbol="x_1", variable_type="real", lowerbound=0.0, upperbound=10.0, initial_value=5.0),
        Variable(name="Test 2", symbol="x_2", variable_type="real", lowerbound=0.0, upperbound=10.0, initial_value=5.0),
    ]

    constants = [Constant(name="Constant 1", symbol="c_1", value=3)]

    extras = [
        ExtraFunction(name="Extra 1", symbol="ef_1", func=["Add", "c_1", "x_1"]),
        ExtraFunction(name="Extra 2", symbol="ef_2", func=["Subtract", "x_2", "x_1"]),
    ]

    objectives = [
        Objective(
            name="Objective 1",
            symbol="f_1",
            func=["Add", ["Negate", "x_1"], "ef_1", 2],
            maximize=False,
            ideal=-100,
            nadir=100,
        ),
        Objective(
            name="Objective 2",
            symbol="f_2",
            func=["Add", ["Multiply", 2, "ef_2"], "ef_1"],
            maximize=False,
            ideal=-100,
            nadir=100,
        ),
        Objective(
            name="Objective 3",
            symbol="f_3",
            func=["Add", ["Divide", "ef_1", "ef_2"], "c_1"],
            maximize=False,
            ideal=-100,
            nadir=100,
        ),
    ]

    constraints = [
        Constraint(name="Constraint 1", symbol="con_1", cons_type="<=", func=["Add", ["Negate", "c_1"], "ef_1", -4])
    ]

    scalarizations = [
        ScalarizationFunction(
            name="Scalarization 1",
            symbol="scal_1",
            func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"],
        )
    ]

    return Problem(
        name="Extra functions test problem",
        description="Test problem to test correct parsing and evaluations with extra functions present.",
        constants=constants,
        variables=variables,
        objectives=objectives,
        constraints=constraints,
        extra_funcs=extras,
        scalarizations_funcs=scalarizations,
    )


def test_basic():
    """A basic test to test the parsing of Polish notation to polars expressions."""
    math_parser = MathParser()
    json_expr = [
        "Add",
        ["Divide", ["Multiply", 2, ["Square", "x_1"]], "x_2"],
        ["Multiply", "x_1", "x_3"],
        -180,
    ]

    expr = math_parser.parse(expr=json_expr)

    data = pl.DataFrame({"x_1": [20, 30], "x_2": [5, 8], "x_3": [60, 21]})

    objectives = data.select(expr.alias("Objective 1"))

    assert objectives["Objective 1"][0] == 1180
    assert objectives["Objective 1"][1] == 675


def test_negate():
    """Tests negation."""
    math_parser = MathParser()

    json_expr_1 = [
        "Add",
        ["Negate", ["Power", ["Add", "x_1", ["Negate", 8]], 2]],
        ["Negate", ["Power", ["Add", "x_2", 3], 2]],
        7.7,
    ]
    json_expr_2 = [
        "Add",
        ["Negate", ["Square", ["Subtract", "x_1", 8]]],
        ["Negate", ["Square", ["Add", "x_2", 3]]],
        7.7,
    ]

    expr_1 = math_parser.parse(expr=json_expr_1)
    expr_2 = math_parser.parse(expr=json_expr_2)

    data = pl.DataFrame({"x_1": [1], "x_2": [1]})

    res_1 = data.select(expr_1.alias("res_1"))
    res_2 = data.select(expr_2.alias("res_2"))

    res_1 = res_1["res_1"][0]
    res_2 = res_2["res_2"][0]

    print()


def test_binh_and_korn():
    """Basic test of the Binh and Korn problem.

    Test replacement of constants in both objectives and constraints.
    Test correct evaluation results of the Binh and Korn problem.
    """
    problem = binh_and_korn()

    c_1 = problem.constants[0]
    c_2 = problem.constants[1]

    f1_expr_raw = problem.objectives[0].func
    f2_expr_raw = problem.objectives[1].func

    con1_expr_raw = problem.constraints[0].func
    con2_expr_raw = problem.constraints[1].func

    # replace constants in objective function expressions
    tmp = replace_str(f1_expr_raw, c_1.symbol, c_1.value)
    f1_expr = replace_str(tmp, c_2.symbol, c_2.value)

    tmp = replace_str(f2_expr_raw, c_1.symbol, c_1.value)
    f2_expr = replace_str(tmp, c_2.symbol, c_2.value)

    # replace constants in constraint expressions
    tmp = replace_str(con1_expr_raw, c_1.symbol, c_1.value)
    con1_expr = replace_str(tmp, c_2.symbol, c_2.value)

    tmp = replace_str(con2_expr_raw, c_1.symbol, c_1.value)
    con2_expr = replace_str(tmp, c_2.symbol, c_2.value)

    # parse the expressions into polars expressions
    parser = MathParser()

    parsed_f1 = parser.parse(f1_expr)
    parsed_f2 = parser.parse(f2_expr)

    parsed_con1 = parser.parse(con1_expr)
    parsed_con2 = parser.parse(con2_expr)

    # some test data to evaluate the expressions
    data = pl.DataFrame({"x_1": [1, 2.5, 4.2], "x_2": [0.5, 1.5, 2.5]})

    result = data.select(
        parsed_f1.alias("f_1"), parsed_f2.alias("f_2"), parsed_con1.alias("g_1"), parsed_con2.alias("g_2")
    )

    truth = data.select(
        (4 * pl.col("x_1") ** 2 + 4 * pl.col("x_2") ** 2).alias("f_1_t"),
        ((pl.col("x_1") - 5) ** 2 + (pl.col("x_2") - 5) ** 2).alias("f_2_t"),
        ((pl.col("x_1") - 5) ** 2 + pl.col("x_2") ** 2 - 25).alias("g_1_t"),
        (-((pl.col("x_1") - 8) ** 2 + (pl.col("x_2") + 3) ** 2) + 7.7).alias("g_2_t"),
    )

    npt.assert_array_almost_equal(result["f_1"], truth["f_1_t"])
    npt.assert_array_almost_equal(result["f_2"], truth["f_2_t"])
    npt.assert_array_almost_equal(result["g_1"], truth["g_1_t"])
    npt.assert_array_almost_equal(result["g_2"], truth["g_2_t"])


def test_binh_and_korn_w_evaluator():
    """Basic test of the Binh and Korn problem with the GenericEvaluator.

    Test replacement of constants in both objectives and constraints.
    Test correct evaluation results of the Binh and Korn problem.
    """
    problem = binh_and_korn()

    original_problem = copy.deepcopy(problem)

    evaluator = GenericEvaluator(problem)

    # some test data to evaluate the expressions
    xs_dict = {"x_1": [1, 2.5, 4.2], "x_2": [0.5, 1.5, 2.5]}

    result = evaluator.evaluate(xs_dict).to_dict(as_series=False)

    data = pl.DataFrame(xs_dict)
    truth = data.select(
        (4 * pl.col("x_1") ** 2 + 4 * pl.col("x_2") ** 2).alias("f_1_t"),
        ((pl.col("x_1") - 5) ** 2 + (pl.col("x_2") - 5) ** 2).alias("f_2_t"),
        ((pl.col("x_1") - 5) ** 2 + pl.col("x_2") ** 2 - 25).alias("g_1_t"),
        (-((pl.col("x_1") - 8) ** 2 + (pl.col("x_2") + 3) ** 2) + 7.7).alias("g_2_t"),
    )

    npt.assert_array_almost_equal(result["f_1"], truth["f_1_t"])
    npt.assert_array_almost_equal(result["f_2"], truth["f_2_t"])
    npt.assert_array_almost_equal(result["g_1"], truth["g_1_t"])
    npt.assert_array_almost_equal(result["g_2"], truth["g_2_t"])
    npt.assert_array_almost_equal(result["x_1"], data["x_1"])
    npt.assert_array_almost_equal(result["x_2"], data["x_2"])

    # should not have been mutated during evaluation
    assert original_problem == problem


def test_extra_functions_problem_w_evaluator(extra_functions_problem):
    """Test the GenericEvaluator with polars that it handles extra functions correctly."""
    problem = extra_functions_problem

    evaluator = GenericEvaluator(problem)

    # to test correct evaluation
    xs_dict = {"x_1": [2.4, -3.0, 5.5], "x_2": [5.2, 1.1, -9.4]}

    result = evaluator.evaluate(xs_dict).to_dict(as_series=False)

    data = pl.DataFrame(xs_dict)
    truth = data.select(
        (pl.col("x_1") + 3 - pl.col("x_1") + 2).alias("f_1"),
        (pl.col("x_1") + 3 + 2 * (pl.col("x_2") - pl.col("x_1"))).alias("f_2"),
        ((pl.col("x_1") + 3) / (pl.col("x_2") - pl.col("x_1")) + 3).alias("f_3"),
        (pl.col("x_1") + 3 - 4 - 3).alias("con_1"),
        (pl.col("x_1") + 3).alias("ef_1"),
        (pl.col("x_2") - pl.col("x_1")).alias("ef_2"),
    )
    truth = truth.hstack(data)
    tmp = truth.select(
        (pl.col("f_1") + pl.col("f_2") + pl.col("f_3") - pl.col("ef_1") * pl.col("ef_2") + 3).alias("scal_1")
    )

    truth = truth.hstack(tmp)

    npt.assert_array_almost_equal(result["f_1"], truth["f_1"])
    npt.assert_array_almost_equal(result["f_2"], truth["f_2"])
    npt.assert_array_almost_equal(result["f_3"], truth["f_3"])

    npt.assert_almost_equal(result["x_1"], truth["x_1"])
    npt.assert_almost_equal(result["x_2"], truth["x_2"])

    npt.assert_almost_equal(result["con_1"], truth["con_1"])

    npt.assert_almost_equal(result["ef_1"], truth["ef_1"])
    npt.assert_almost_equal(result["ef_2"], truth["ef_2"])

    npt.assert_almost_equal(result["scal_1"], truth["scal_1"])


def test_problem_unique_symbols():
    """Test that having non-unique symbols in a Problem model raises an error."""
    var_1 = Variable(
        name="Test 1", symbol="x_1", variable_type="real", lowerbound=0.0, upperbound=10.0, initial_value=5.0
    )
    var_2 = Variable(
        name="Test 2", symbol="x_2", variable_type="real", lowerbound=0.0, upperbound=10.0, initial_value=5.0
    )

    cons_1 = Constant(name="Constant 1", symbol="c_1", value=3)
    cons_2 = Constant(name="Constant 2", symbol="c_2", value=3)

    efun_1 = ExtraFunction(name="Extra 1", symbol="ef_1", func=["Add", "c_1", "x_1"])
    efun_2 = ExtraFunction(name="Extra 2", symbol="ef_2", func=["Subtract", "x_2", "x_1"])

    obj_1 = Objective(
        name="Objective 1",
        symbol="f_1",
        func=["Add", ["Negate", "x_1"], "ef_1", 2],
        maximize=False,
        ideal=-100,
        nadir=100,
    )
    obj_2 = Objective(
        name="Objective 2",
        symbol="f_2",
        func=["Add", ["Multiply", 2, "ef_2"], "ef_1"],
        maximize=False,
        ideal=-100,
        nadir=100,
    )
    obj_3 = Objective(
        name="Objective 3",
        symbol="f_3",
        func=["Add", ["Divide", "ef_1", "ef_2"], "c_1"],
        maximize=False,
        ideal=-100,
        nadir=100,
    )

    constraint_1 = Constraint(
        name="Constraint 1", symbol="con_1", cons_type="<=", func=["Add", ["Negate", "c_1"], "ef_1", -4]
    )
    constraint_2 = Constraint(
        name="Constraint 1", symbol="con_2", cons_type="<=", func=["Add", ["Negate", "c_1"], "ef_1", -4]
    )

    scal_no_name = ScalarizationFunction(
        name="Scalarization 1", func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"]
    )
    scal_1 = ScalarizationFunction(
        name="Scalarization 1",
        func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"],
        symbol="S_1",
    )
    scal_2 = ScalarizationFunction(
        name="Scalarization 1",
        func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"],
        symbol="S_2",
    )

    # Test with same variable symbols, should raise error
    with pytest.raises(ValueError) as e:
        problem = Problem(
            name="Extra functions test problem",
            description="Test problem to test correct parsing and evaluations with extra functions present.",
            constants=[cons_1, cons_2],
            variables=[var_1, var_1],
            objectives=[obj_1, obj_2, obj_3],
            constraints=[constraint_1, constraint_2],
            extra_funcs=[efun_1, efun_2],
            scalarizations_funcs=[scal_1, scal_2, scal_no_name],
        )
    assert "x_1" in str(e.value)

    # Test with same objective symbols, should raise error
    with pytest.raises(ValueError) as e:
        problem = Problem(
            name="Extra functions test problem",
            description="Test problem to test correct parsing and evaluations with extra functions present.",
            constants=[cons_1, cons_2],
            variables=[var_1, var_2],
            objectives=[obj_1, obj_2, obj_2],
            constraints=[constraint_1, constraint_2],
            extra_funcs=[efun_1, efun_2],
            scalarizations_funcs=[scal_1, scal_2, scal_no_name],
        )
    assert "f_2" in str(e.value)

    # Test with same constant symbols, should raise error
    with pytest.raises(ValueError) as e:
        problem = Problem(
            name="Extra functions test problem",
            description="Test problem to test correct parsing and evaluations with extra functions present.",
            constants=[cons_2, cons_2],
            variables=[var_1, var_2],
            objectives=[obj_1, obj_2, obj_3],
            constraints=[constraint_1, constraint_2],
            extra_funcs=[efun_1, efun_2],
            scalarizations_funcs=[scal_1, scal_2, scal_no_name],
        )
    assert "c_2" in str(e.value)

    # Test with same constraints symbols, should raise error
    with pytest.raises(ValueError) as e:
        problem = Problem(
            name="Extra functions test problem",
            description="Test problem to test correct parsing and evaluations with extra functions present.",
            constants=[cons_1, cons_2],
            variables=[var_1, var_2],
            objectives=[obj_1, obj_2, obj_3],
            constraints=[constraint_1, constraint_1],
            extra_funcs=[efun_1, efun_2],
            scalarizations_funcs=[scal_1, scal_2, scal_no_name],
        )
    assert "con_1" in str(e.value)

    # Test with same extra symbols, should raise error
    with pytest.raises(ValueError) as e:
        problem = Problem(
            name="Extra functions test problem",
            description="Test problem to test correct parsing and evaluations with extra functions present.",
            constants=[cons_1, cons_2],
            variables=[var_1, var_2],
            objectives=[obj_1, obj_2, obj_3],
            constraints=[constraint_1, constraint_2],
            extra_funcs=[efun_2, efun_2],
            scalarizations_funcs=[scal_1, scal_2, scal_no_name],
        )
    assert "ef_2" in str(e.value)

    # Test with same scalarization symbols, should raise error
    with pytest.raises(ValueError) as e:
        problem = Problem(
            name="Extra functions test problem",
            description="Test problem to test correct parsing and evaluations with extra functions present.",
            constants=[cons_1, cons_2],
            variables=[var_1, var_2],
            objectives=[obj_1, obj_2, obj_3],
            constraints=[constraint_1, constraint_2],
            extra_funcs=[efun_1, efun_2],
            scalarizations_funcs=[scal_1, scal_1, scal_no_name],
        )
    assert "S_1" in str(e.value)

    # Test mixed case with same symbols, should raise error
    with pytest.raises(ValueError) as e:
        constraint_mixed = Constraint(
            name="Constraint 1", symbol="S_1", cons_type="<=", func=["Add", ["Negate", "c_1"], "ef_1", -4]
        )
        problem = Problem(
            name="Extra functions test problem",
            description="Test problem to test correct parsing and evaluations with extra functions present.",
            constants=[cons_1, cons_2],
            variables=[var_1, var_2],
            objectives=[obj_1, obj_2, obj_3],
            constraints=[constraint_1, constraint_2, constraint_mixed],
            extra_funcs=[efun_1, efun_2],
            scalarizations_funcs=[scal_1, scal_2, scal_no_name],
        )
    assert "S_1" in str(e.value)

    # Test another mixed case with same symbols, should raise error
    with pytest.raises(ValueError) as e:
        obj_mixed = Objective(
            name="Objective 2",
            symbol="x_2",
            func=["Add", ["Multiply", 2, "ef_2"], "ef_1"],
            maximize=False,
            ideal=-100,
            nadir=100,
        )
        problem = Problem(  # noqa: F841
            name="Extra functions test problem",
            description="Test problem to test correct parsing and evaluations with extra functions present.",
            constants=[cons_1, cons_2],
            variables=[var_1, var_2],
            objectives=[obj_1, obj_mixed, obj_3],
            constraints=[constraint_1, constraint_2],
            extra_funcs=[efun_1, efun_2],
            scalarizations_funcs=[scal_1, scal_2, scal_no_name],
        )
    assert "x_2" in str(e.value)


def test_problem_default_scalarization_names():
    """Test that default scalarization function symbols in a Problem model are assigned correctly."""
    var_1 = Variable(
        name="Test 1", symbol="x_1", variable_type="real", lowerbound=0.0, upperbound=10.0, initial_value=5.0
    )
    var_2 = Variable(
        name="Test 2", symbol="x_2", variable_type="real", lowerbound=0.0, upperbound=10.0, initial_value=5.0
    )

    cons_1 = Constant(name="Constant 1", symbol="c_1", value=3)
    cons_2 = Constant(name="Constant 2", symbol="c_2", value=3)

    efun_1 = ExtraFunction(name="Extra 1", symbol="ef_1", func=["Add", "c_1", "x_1"])
    efun_2 = ExtraFunction(name="Extra 2", symbol="ef_2", func=["Subtract", "x_2", "x_1"])

    obj_1 = Objective(
        name="Objective 1",
        symbol="f_1",
        func=["Add", ["Negate", "x_1"], "ef_1", 2],
        maximize=False,
        ideal=-100,
        nadir=100,
    )
    obj_2 = Objective(
        name="Objective 2",
        symbol="f_2",
        func=["Add", ["Multiply", 2, "ef_2"], "ef_1"],
        maximize=False,
        ideal=-100,
        nadir=100,
    )
    obj_3 = Objective(
        name="Objective 3",
        symbol="f_3",
        func=["Add", ["Divide", "ef_1", "ef_2"], "c_1"],
        maximize=False,
        ideal=-100,
        nadir=100,
    )

    constraint_1 = Constraint(
        name="Constraint 1", symbol="con_1", cons_type="<=", func=["Add", ["Negate", "c_1"], "ef_1", -4]
    )
    constraint_2 = Constraint(
        name="Constraint 1", symbol="con_2", cons_type="<=", func=["Add", ["Negate", "c_1"], "ef_1", -4]
    )

    scal_1 = ScalarizationFunction(
        name="Scalarization 1", func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"]
    )
    scal_2 = ScalarizationFunction(
        name="Scalarization 1",
        func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"],
        symbol="S_9",
    )
    scal_3 = ScalarizationFunction(
        name="Scalarization 1",
        func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"],
    )

    problem = Problem(
        name="Extra functions test problem",
        description="Test problem to test correct parsing and evaluations with extra functions present.",
        constants=[cons_1, cons_2],
        variables=[var_1, var_2],
        objectives=[obj_1, obj_2, obj_3],
        constraints=[constraint_1, constraint_2],
        extra_funcs=[efun_1, efun_2],
        scalarizations_funcs=[scal_1, scal_2, scal_3],
    )

    symbols = [func.symbol for func in problem.scalarizations_funcs]
    assert "scal_1" in symbols
    assert "scal_2" in symbols
    assert "S_9" in symbols

    # add more scalarization functions
    scal_new = ScalarizationFunction(
        name="Scalarization 1",
        func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"],
    )

    problem_new = problem.add_scalarization(scal_new)
    symbols = [func.symbol for func in problem_new.scalarizations_funcs]

    assert "scal_3" in symbols

    # add to problem with no prior scalarization functions
    problem = Problem(
        name="Extra functions test problem",
        description="Test problem to test correct parsing and evaluations with extra functions present.",
        constants=[cons_1, cons_2],
        variables=[var_1, var_2],
        objectives=[obj_1, obj_2, obj_3],
        constraints=[constraint_1, constraint_2],
        extra_funcs=[efun_1, efun_2],
    )

    scal_lonely = ScalarizationFunction(
        name="Scalarization 1",
        func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"],
    )

    new_problem = problem.add_scalarization(scal_lonely)

    assert new_problem.scalarizations_funcs[0].symbol == "scal_1"


@pytest.mark.pyomo
def test_parse_pyomo_basic_arithmetics():
    """Test the JSON parser for correctly parsing MathJSON into pyomo expressions."""
    pyomo_model = pyomo.ConcreteModel()

    x_1 = 6.9
    x_2 = 0.1
    x_3 = -11.1
    pyomo_model.x_1 = pyomo.Var(domain=pyomo.Reals, initialize=x_1)
    pyomo_model.x_2 = pyomo.Var(domain=pyomo.Reals, initialize=x_2)
    pyomo_model.x_3 = pyomo.Var(domain=pyomo.Reals, initialize=x_3)

    c_1 = 4.2
    pyomo_model.c_1 = pyomo.Param(domain=pyomo.Reals, default=c_1)
    c_2 = -2.2
    pyomo_model.c_2 = pyomo.Param(domain=pyomo.Reals, default=c_2)

    tests = [
        ("x_1 + x_2 + x_3", x_1 + x_2 + x_3),
        ("x_1 + x_2 + x_3 - c_1 - c_2", x_1 + x_2 + x_3 - c_1 - c_2),
        ("x_1 - x_2 + c_1", x_1 - x_2 + c_1),
        ("x_1 * c_2", x_1 * c_2),
        ("x_2 / c_1", x_2 / c_1),
        ("(x_1 + x_2) * c_1", (x_1 + x_2) * c_1),
        ("((x_1 + x_2) - x_3) / c_1", ((x_1 + x_2) - x_3) / c_1),
        ("x_1 + 2 * x_2 - 3", x_1 + 2 * x_2 - 3),
        ("(x_1 + (x_2 * c_2) / (c_1 - x_3)) * 2", (x_1 + (x_2 * c_2) / (c_1 - x_3)) * 2),
        ("x_3 * c_2 / 2", x_3 * c_2 / 2),
        ("(x_1 + 10) - (c_2 - 5)", (x_1 + 10) - (c_2 - 5)),
        ("((x_1 * 2) + (x_2 / 0.5)) - (c_1 * (x_3 + 3))", ((x_1 * 2) + (x_2 / 0.5)) - (c_1 * (x_3 + 3))),
        ("(x_1 - (x_2 * 2) / (x_3 + 5.5) + c_1) * (c_2 + 4.4)", (x_1 - (x_2 * 2) / (x_3 + 5.5) + c_1) * (c_2 + 4.4)),
        ("x_1 / ((x_2 + 2.1) * (c_1 - 3))", x_1 / ((x_2 + 2.1) * (c_1 - 3))),
        ("(x_1 + (x_2 * (c_1 + 3.3) / (x_3 - 2))) * 1.5", (x_1 + (x_2 * (c_1 + 3.3) / (x_3 - 2))) * 1.5),
        ("(x_1 - (x_2 / (2.5 * c_1))) / (c_2 - (x_3 * 0.5))", (x_1 - (x_2 / (2.5 * c_1))) / (c_2 - (x_3 * 0.5))),
        (
            "((x_1 * c_1) + (x_2 - c_2) / 2.0) * (x_3 + 3.5) / (1 + c_1)",
            ((x_1 * c_1) + (x_2 - c_2) / 2.0) * (x_3 + 3.5) / (1 + c_1),
        ),
        ("(x_1 ** 2 + x_2 ** 2) ** 0.5 - c_1 * 3 + (x_3 / c_2)", (x_1**2 + x_2**2) ** 0.5 - c_1 * 3 + (x_3 / c_2)),
    ]

    infix_parser = InfixExpressionParser()
    pyomo_parser = MathParser(to_format=FormatEnum.pyomo)

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        pyomo_expr = pyomo_parser.parse(json_expr, pyomo_model)

        npt.assert_array_almost_equal(
            pyomo.value(pyomo_expr), result, err_msg=f"Test failed for {str_expr=}, with {pyomo_expr.to_string()=}"
        )


@pytest.mark.pyomo
def test_parse_pyomo_exponentation_and_logarithms():
    """Test the JSON parser for correctly parsing MathJSON into pyomo expressions, with exponentation and logarithms."""
    pyomo_model = pyomo.ConcreteModel()

    x = -6.9
    y = 1
    garlic = 11.1
    pyomo_model.x = pyomo.Var(domain=pyomo.Reals, initialize=x)
    pyomo_model.y = pyomo.Var(domain=pyomo.Integers, initialize=y)
    pyomo_model.garlic = pyomo.Var(domain=pyomo.Reals, initialize=garlic)

    cosmic = 4.2
    pyomo_model.cosmic = pyomo.Param(domain=pyomo.Reals, default=cosmic)
    potato = -2
    pyomo_model.potato = pyomo.Param(domain=pyomo.Integers, default=potato)

    tests = [
        ("garlic**2", garlic**2),
        ("Ln(cosmic)", math.log(cosmic)),
        ("Lb(garlic)", math.log(garlic, 2)),
        ("Lg(cosmic)", math.log10(cosmic)),
        ("LogOnePlus(y)", math.log1p(y)),
        ("Sqrt(garlic)", math.sqrt(garlic)),
        ("Square(x)", x**2),
        ("garlic**potato", garlic**potato),
        ("(garlic**2 + Ln(cosmic))", garlic**2 + math.log(cosmic)),
        ("Lb(garlic) * Lg(cosmic) - y", math.log(garlic, 2) * math.log10(cosmic) - y),
        ("Ln(cosmic + garlic**potato)", math.log(cosmic + garlic**potato)),
        ("Sqrt(garlic) * Ln(cosmic)", math.sqrt(garlic) * math.log(cosmic)),
        ("garlic**y + LogOnePlus(cosmic)", garlic**y + math.log1p(cosmic)),
        ("(Sqrt(garlic) + Square(x)) / Lg(cosmic)", (math.sqrt(garlic) + x**2) / math.log10(cosmic)),
        ("Ln(cosmic**2) + garlic**(Lb(cosmic))", math.log(cosmic**2) + garlic ** (math.log(cosmic, 2))),
        ("Lb(garlic**2) * (Lg(cosmic) + Sqrt(y))", math.log(garlic**2, 2) * (math.log10(cosmic) + math.sqrt(y))),
        ("Square(x) - Sqrt(y) + Ln(garlic + 1)", x**2 - math.sqrt(y) + math.log(garlic + 1)),
        (
            "Ln((garlic**2 + cosmic) / (1 + Lg(-x))) * (Sqrt(-potato + Square(y)))",
            math.log((garlic**2 + cosmic) / (1 + math.log10(-x))) * math.sqrt(-potato + y**2),
        ),
        (
            "((garlic**3 - 2**Lb(cosmic)) + Ln(x**2 + 1)) / (Sqrt(Square(y) + LogOnePlus(potato + 3.1)))",
            ((garlic**3 - 2 ** math.log(cosmic, 2)) + math.log(x**2 + 1)) / math.sqrt(y**2 + math.log1p(potato + 3.1)),
        ),
        (
            "Square(Ln(cosmic) + garlic**2) - (Lb(garlic) * Lg(-x) / Sqrt(y + 3))",
            (math.log(cosmic) + garlic**2) ** 2 - (math.log(garlic, 2) * math.log10(-x) / math.sqrt(y + 3)),
        ),
        (
            "Lg(cosmic**2 + Lb(garlic * -x)) * (Sqrt(Square(potato) + y) - LogOnePlus(garlic))",
            math.log10(cosmic**2 + math.log(garlic * -x, 2)) * (math.sqrt(potato**2 + y) - math.log1p(garlic)),
        ),
        (
            "(Ln(Lg(cosmic**2) + Sqrt(garlic)) ** 2) / (garlic**(-potato) + 3**y)",
            (math.log(math.log10(cosmic**2) + math.sqrt(garlic)) ** 2) / (garlic ** (-potato) + 3**y),
        ),
        (
            "(Lb(garlic + Lg(cosmic + Square(x))) - Sqrt(LogOnePlus(y))) * (x**2 + garlic**Lg(cosmic))",
            (math.log(garlic + math.log10(cosmic + x**2), 2) - math.sqrt(math.log1p(y)))
            * (x**2 + garlic ** math.log10(cosmic)),
        ),
    ]

    infix_parser = InfixExpressionParser()
    pyomo_parser = MathParser(to_format=FormatEnum.pyomo)

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        pyomo_expr = pyomo_parser.parse(json_expr, pyomo_model)

        npt.assert_array_almost_equal(
            pyomo.value(pyomo_expr),
            result,
            err_msg=(
                f"Test failed for {str_expr=}, with "
                f"{(pyomo_expr.to_string() if isinstance(pyomo_expr, pyomo.Expression) else pyomo_expr)=}"
            ),
        )
