"""Tests for the MathJSON parser."""

from collections.abc import Iterable
import copy
import json
import math
from pathlib import Path

import gurobipy as gp
import numpy as np
import numpy.testing as npt
import polars as pl
import pyomo.environ as pyomo
import pytest
import sympy as sp

from desdeo.problem import GenericEvaluator, PyomoEvaluator
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
        scalarization_funcs=scalarizations,
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
            scalarization_funcs=[scal_1, scal_2, scal_no_name],
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
            scalarization_funcs=[scal_1, scal_2, scal_no_name],
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
            scalarization_funcs=[scal_1, scal_2, scal_no_name],
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
            scalarization_funcs=[scal_1, scal_2, scal_no_name],
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
            scalarization_funcs=[scal_1, scal_2, scal_no_name],
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
            scalarization_funcs=[scal_1, scal_1, scal_no_name],
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
            scalarization_funcs=[scal_1, scal_2, scal_no_name],
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
            scalarization_funcs=[scal_1, scal_2, scal_no_name],
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
        scalarization_funcs=[scal_1, scal_2, scal_3],
    )

    symbols = [func.symbol for func in problem.scalarization_funcs]
    assert "scal_1" in symbols
    assert "scal_2" in symbols
    assert "S_9" in symbols

    # add more scalarization functions
    scal_new = ScalarizationFunction(
        name="Scalarization 1",
        func=["Add", ["Negate", ["Multiply", "ef_1", "ef_2"]], "c_1", "f_1", "f_2", "f_3"],
    )

    problem_new = problem.add_scalarization(scal_new)
    symbols = [func.symbol for func in problem_new.scalarization_funcs]

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

    assert new_problem.scalarization_funcs[0].symbol == "scal_1"


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
                f"{pyomo_expr.to_string() if isinstance(pyomo_expr, pyomo.Expression) else pyomo_expr}"
            ),
        )


@pytest.mark.pyomo
def test_parse_pyomo_trigonometrics():
    """Test the JSON parser for correctly parsing MathJSON into pyomo expressions, with trigonometric operators."""
    pyomo_model = pyomo.ConcreteModel()

    x = 0.8
    y = 1.4
    garlic = 4.2
    pyomo_model.x = pyomo.Var(domain=pyomo.PositiveReals, initialize=x)
    pyomo_model.y = pyomo.Var(domain=pyomo.PositiveReals, initialize=y)
    pyomo_model.garlic = pyomo.Var(domain=pyomo.PositiveReals, initialize=garlic)

    cosmic = 0.42
    pyomo_model.cosmic = pyomo.Param(domain=pyomo.Reals, default=cosmic)
    potato = 0.22
    pyomo_model.potato = pyomo.Param(domain=pyomo.Reals, default=potato)

    tests = [
        ("Arccos(x)", math.acos(x)),
        ("Arccosh(y)", math.acosh(y)),
        ("Arcsin(x)", math.asin(x)),
        ("Arcsinh(y)", math.asinh(y)),
        ("Arctan(garlic)", math.atan(garlic)),
        ("Arctanh(x)", math.atanh(x)),
        ("Cos(garlic)", math.cos(garlic)),
        ("Cosh(x)", math.cosh(x)),
        ("Sin(garlic)", math.sin(garlic)),
        ("Sinh(x)", math.sinh(x)),
        ("Tan(garlic)", math.tan(garlic)),
        ("Tanh(x)", math.tanh(x)),
        ("Sin(garlic) + Cos(x)", math.sin(garlic) + math.cos(x)),
        ("Tan(Arccos(y / Sqrt(y**2 + 1)))", math.tan(math.acos(y / math.sqrt(y**2 + 1)))),
        ("Sinh(x) * Cos(garlic) - Tanh(x)", math.sinh(x) * math.cos(garlic) - math.tanh(x)),
        ("Arctan(garlic**2) + Arctanh(x / 2)", math.atan(garlic**2) + math.atanh(x / 2)),
        ("Cos(Sin(garlic)) + Tanh(Arccosh(y))", math.cos(math.sin(garlic)) + math.tanh(math.acosh(y))),
        (
            "Arcsinh(y) * Arctan(garlic) - Arccosh(Sqrt(y**2 + 1))",
            math.asinh(y) * math.atan(garlic) - math.acosh(math.sqrt(y**2 + 1)),
        ),
        ("Sin(garlic) * Cos(x) + Tanh(x)", math.sin(garlic) * math.cos(x) + math.tanh(x)),
        ("Sqrt(Sin(garlic)**2 + Cos(x)**2)", math.sqrt(math.sin(garlic) ** 2 + math.cos(x) ** 2)),
        (
            "Cosh(Arctan(garlic)) - Sinh(Arccos(y / Sqrt(y**2 + 1)))",
            math.cosh(math.atan(garlic)) - math.sinh(math.acos(y / math.sqrt(y**2 + 1))),
        ),
        ("Sin(garlic) + Cos(x)", math.sin(garlic) + math.cos(x)),
        ("Tan(Arccos(y / Sqrt(y**2 + 1)))", math.tan(math.acos(y / math.sqrt(y**2 + 1)))),
        ("Sinh(x) * Cos(garlic) - Tanh(x)", math.sinh(x) * math.cos(garlic) - math.tanh(x)),
        ("Arctan(garlic**2) + Arctanh(x / 2)", math.atan(garlic**2) + math.atanh(x / 2)),
        ("Cos(Sin(garlic)) + Tanh(Arccosh(y))", math.cos(math.sin(garlic)) + math.tanh(math.acosh(y))),
        (
            "Arcsinh(y) * Arctan(garlic) - Arccosh(Sqrt(y**2 + 1))",
            math.asinh(y) * math.atan(garlic) - math.acosh(math.sqrt(y**2 + 1)),
        ),
        ("Sin(garlic) * Cos(x) + Tanh(x)", math.sin(garlic) * math.cos(x) + math.tanh(x)),
        ("Sqrt(Sin(garlic)**2 + Cos(x)**2)", math.sqrt(math.sin(garlic) ** 2 + math.cos(x) ** 2)),
        (
            "Cosh(Arctan(garlic)) - Sinh(Arccos(y / Sqrt(y**2 + 1)))",
            math.cosh(math.atan(garlic)) - math.sinh(math.acos(y / math.sqrt(y**2 + 1))),
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
                f"{pyomo_expr.to_string() if isinstance(pyomo_expr, pyomo.Expression) else pyomo_expr}"
            ),
        )


@pytest.mark.pyomo
def test_parse_pyomo_rounding():
    """Test the JSON parser for correctly parsing MathJSON into pyomo expressions, with rounding operators."""
    pyomo_model = pyomo.ConcreteModel()

    x = 2.8
    y = -1.4
    garlic = 4.2
    pyomo_model.x = pyomo.Var(domain=pyomo.PositiveReals, initialize=x)
    pyomo_model.y = pyomo.Var(domain=pyomo.NonNegativeReals, initialize=y)
    pyomo_model.garlic = pyomo.Var(domain=pyomo.PositiveReals, initialize=garlic)

    cosmic = -69.42
    pyomo_model.cosmic = pyomo.Param(domain=pyomo.Reals, default=cosmic)
    potato = 99.22
    pyomo_model.potato = pyomo.Param(domain=pyomo.Reals, default=potato)

    tests = [
        ("Abs(y)", abs(y)),
        ("Ceil(potato)", math.ceil(potato)),
        ("Floor(cosmic)", math.floor(cosmic)),
        ("Ceil(x + garlic)", math.ceil(x + garlic)),
        ("Floor(x - cosmic)", math.floor(x - cosmic)),
        ("Abs(cosmic + potato)", abs(cosmic + potato)),
        ("Ceil(Floor(garlic) + Abs(x))", math.ceil(math.floor(garlic) + abs(x))),
        (
            "Abs(Ceil(x) - Floor(y)) + Floor(garlic - Ceil(potato))",
            abs(math.ceil(x) - math.floor(y)) + math.floor(garlic - math.ceil(potato)),
        ),
        ("Ceil(Abs(x) + Abs(cosmic))", math.ceil(abs(x) + abs(cosmic))),
        (
            "Floor(Ceil(x) + Abs(Ceil(y) + Floor(garlic)))",
            math.floor(math.ceil(x) + abs(math.ceil(y) + math.floor(garlic))),
        ),
        (
            "Ceil(Sin(garlic)**2 + Cos(x)**2) + Floor(LogOnePlus(Abs(x)))",
            math.ceil(math.sin(garlic) ** 2 + math.cos(x) ** 2) + math.floor(math.log1p(abs(x))),
        ),
        (
            "Abs(Tanh(x) - Sinh(y)) + Lb(Ceil(Abs(garlic)) + 1) * Sqrt(Abs(Floor(potato)))",
            abs(math.tanh(x) - math.sinh(y))
            + math.log(math.ceil(abs(garlic)) + 1, 2) * math.sqrt(abs(math.floor(potato))),
        ),
        (
            "Floor(Cosh(Abs(x)) + Sin(Arctan(Abs(garlic)))) * Ln(Ceil(Abs(y)) + 1)",
            math.floor(math.cosh(abs(x)) + math.sin(math.atan(abs(garlic)))) * math.log(math.ceil(abs(y)) + 1),
        ),
        (
            "Ln(Ceil(Abs(Sin(garlic) * Tanh(x)) + Floor(Cosh(Abs(y))))) + Sqrt(Abs(Floor(Abs(cosmic))))",
            math.log(math.ceil(abs(math.sin(garlic) * math.tanh(x)) + math.floor(math.cosh(abs(y)))))
            + math.sqrt(abs(math.floor(abs(cosmic)))),
        ),
        (
            "Ceil(Lg(Abs(Cos(x) * Sin(garlic)))) + Arctan(Floor(Abs(Tanh(Abs(potato)))))",
            math.ceil(math.log10(abs(math.cos(x) * math.sin(garlic))))
            + math.atan(math.floor(abs(math.tanh(abs(potato))))),
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
                f"{pyomo_expr.to_string() if isinstance(pyomo_expr, pyomo.Expression) else pyomo_expr}"
            ),
        )


@pytest.mark.pyomo
def test_parse_pyomo_max():
    """Test the JSON parser for correctly parsing MathJSON into pyomo expressions, with the max operator."""
    pyomo_model = pyomo.ConcreteModel()

    x = 2.8
    y = -1.4
    garlic = 4.2
    pyomo_model.x = pyomo.Var(domain=pyomo.PositiveReals, initialize=x)
    pyomo_model.y = pyomo.Var(domain=pyomo.NonNegativeReals, initialize=y)
    pyomo_model.garlic = pyomo.Var(domain=pyomo.PositiveReals, initialize=garlic)

    cosmic = -69.42
    pyomo_model.cosmic = pyomo.Param(domain=pyomo.Reals, default=cosmic)
    potato = 99.22
    pyomo_model.potato = pyomo.Param(domain=pyomo.Reals, default=potato)

    tests = [
        ("Max(x)", max((x,))),
        ("Max(x, y)", max((x, y))),
        ("Max(x, y, potato)", max((x, y, potato))),
        ("Max(Abs(cosmic), x)", max((abs(cosmic), x))),
        ("Max(x + 2, y - 3, garlic)", max((x + 2, y - 3, garlic))),
        ("Max(Abs(x), Abs(y), Abs(cosmic))", max((abs(x), abs(y), abs(cosmic)))),
        ("Max(potato, cosmic, x, y)", max((potato, cosmic, x, y))),
        ("Max(Max(x, y), Max(garlic, cosmic))", max((max((x, y)), max((garlic, cosmic))))),
        ("Max(x * 2 - 3, Abs(cosmic) + 4, y / 2)", max((x * 2 - 3, abs(cosmic) + 4, y / 2))),
        ("Max(x, y, garlic, cosmic, potato)", max((x, y, garlic, cosmic, potato))),
        (
            "Max(Abs(x - y), garlic + 10, cosmic * 2, potato / 2)",
            max((abs(x - y), garlic + 10, cosmic * 2, potato / 2)),
        ),
        (
            "Max(Ceil(Sin(garlic) + Tanh(x)), Floor(Ln(Abs(cosmic)) + 1), x ** 2, Sqrt(potato))",
            max(
                (
                    math.ceil(math.sin(garlic) + math.tanh(x)),
                    math.floor(math.log(abs(cosmic)) + 1),
                    x**2,
                    math.sqrt(potato),
                )
            ),
        ),
        (
            "Max(Ln(x) + Lb(Abs(y)), Ceil(Sqrt(garlic) * 3), (potato ** 2) / 4, Abs(cosmic) + 10)",
            max(
                (math.log(x) + math.log(abs(y), 2), math.ceil(math.sqrt(garlic) * 3), (potato**2) / 4, abs(cosmic) + 10)
            ),
        ),
        (
            "Max(Abs(x - y), Max(Sin(x), Cos(garlic)), Tanh(potato) + 1)",
            max((abs(x - y), max((math.sin(x), math.cos(garlic))), math.tanh(potato) + 1)),
        ),
        (
            "Max(Abs(Max(cosmic, x) + Sin(garlic)), Floor(Abs(y) + Ceil(garlic)))",
            max((abs(max((cosmic, x)) + math.sin(garlic)), math.floor(abs(y) + math.ceil(garlic)))),
        ),
        (
            "Max(Sqrt(Abs(x) + y ** 2), Lg(Max(cosmic, potato)), Ceil(Tanh(x) + Arctan(garlic)))",
            max(
                (
                    math.sqrt(abs(x) + y**2),
                    math.log10(max((cosmic, potato))),
                    math.ceil(math.tanh(x) + math.atan(garlic)),
                )
            ),
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
                f"{pyomo_expr.to_string() if isinstance(pyomo_expr, pyomo.Expression) else pyomo_expr}"
            ),
        )


@pytest.mark.pyomo
def test_pyomo_basic_matrix_arithmetics():
    """Check that matrix arithmetics are parsed correctly from MathJSON format to Pyomo expression."""
    pyomo_model = pyomo.ConcreteModel()

    X_dims = (5,)
    Y_dims = (5,)
    X_values = [1, 2, 3, 4, 5]
    Y_values = [-1, 1, 0, 1, -1]

    xmat_dims = (3, 3)
    ymat_dims = (3, 3)
    zmat_dims = (4, 3)
    vmat_dims = (1, 4)
    Xmat_values = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    Ymat_values = [[1, -2, 3.1], [-3.3, 5, -6], [7.1, 4.2, 6.9]]
    Zmat_values = [[1.5, -2.3, 3.8], [-3.7, 5.2, -6.1], [7.4, 4.5, 6.2], [0.1, -0.4, 1.3]]
    Vmat_values = [[1.5, -2.3, 3.8, 0.9]]

    x = 2.8
    c = 0.5

    pyomo_model.X = pyomo.Var(
        pyomo.RangeSet(1, X_dims[0]), domain=pyomo.Reals, initialize=PyomoEvaluator._init_rule(X_values)
    )
    pyomo_model.Y = pyomo.Param(
        pyomo.RangeSet(1, Y_dims[0]), domain=pyomo.Reals, initialize=PyomoEvaluator._init_rule(Y_values)
    )
    pyomo_model.Xmat = pyomo.Var(
        pyomo.RangeSet(1, xmat_dims[0]),
        pyomo.RangeSet(1, xmat_dims[1]),
        domain=pyomo.Reals,
        initialize=PyomoEvaluator._init_rule(Xmat_values),
    )
    pyomo_model.Ymat = pyomo.Param(
        pyomo.RangeSet(1, ymat_dims[0]),
        pyomo.RangeSet(1, ymat_dims[1]),
        domain=pyomo.Reals,
        initialize=PyomoEvaluator._init_rule(Ymat_values),
    )
    pyomo_model.Zmat = pyomo.Var(
        pyomo.RangeSet(1, zmat_dims[0]),
        pyomo.RangeSet(1, zmat_dims[1]),
        domain=pyomo.Reals,
        initialize=PyomoEvaluator._init_rule(Zmat_values),
    )
    pyomo_model.Vmat = pyomo.Param(
        pyomo.RangeSet(1, vmat_dims[0]),
        pyomo.RangeSet(1, vmat_dims[1]),
        domain=pyomo.Reals,
        initialize=PyomoEvaluator._init_rule(Vmat_values),
    )
    pyomo_model.x = pyomo.Var(domain=pyomo.Reals, initialize=x)
    pyomo_model.c = pyomo.Param(domain=pyomo.Reals, default=c)

    tests = [
        ("X@Y", np.dot(X_values, Y_values)),  # dot product
        ("Y@X", np.dot(Y_values, X_values)),
        ("5*Y@X", 5 * np.dot(Y_values, X_values)),
        ("X@Y - 3", np.dot(X_values, Y_values) - 3),  # dot product
        ("X*c", c * np.array(X_values)),  # product by or with constant
        ("c*X", c * np.array(X_values)),
        ("Y*c", c * np.array(Y_values)),
        ("c*Y", c * np.array(Y_values)),
        ("x*X", x * np.array(X_values)),  # product by or with scalar
        ("X*x", x * np.array(X_values)),
        ("x*Y", x * np.array(Y_values)),
        ("Y*x", x * np.array(Y_values)),
        ("X*Y", np.array(X_values) * np.array(Y_values)),  # element-wise multiplication
        ("Y*X", np.array(Y_values) * np.array(X_values)),
        ("Xmat*Ymat", np.array(Xmat_values) * np.array(Ymat_values)),
        ("Ymat*Xmat*4", np.array(Ymat_values) * np.array(Xmat_values) * 4),
        ("Ymat*Xmat*4*Ymat", np.array(Ymat_values) * np.array(Xmat_values) * 4 * np.array(Ymat_values)),
        ("Xmat@Ymat", np.array(Xmat_values) @ np.array(Ymat_values)),  # matrix product
        ("Ymat@Xmat", np.array(Ymat_values) @ np.array(Xmat_values)),
        ("Zmat@Xmat", np.array(Zmat_values) @ np.array(Xmat_values)),
        ("Vmat@Zmat", np.array(Vmat_values) @ np.array(Zmat_values)),
        ("Vmat@Zmat@Xmat", np.array(Vmat_values) @ np.array(Zmat_values) @ np.array(Xmat_values)),
        ("Xmat + Ymat", np.array(Xmat_values) + np.array(Ymat_values)),  # matrix addition
        ("Ymat + Xmat", np.array(Ymat_values) + np.array(Xmat_values)),  # matrix addition
        ("Xmat - Ymat", np.array(Xmat_values) - np.array(Ymat_values)),  # matrix subtraction
        ("Ymat - Xmat", np.array(Ymat_values) - np.array(Xmat_values)),  # matrix subtraction
        ("x*Xmat", x * np.array(Xmat_values)),  # matrix scalar product
        ("c*Xmat", c * np.array(Xmat_values)),
        ("x*Ymat", x * np.array(Ymat_values)),
        ("c*Ymat", c * np.array(Ymat_values)),
        ("Sum(Ymat)", np.sum(np.array(Ymat_values))),  # Summing
        ("Cos(c) * (Ymat + Xmat)", np.cos(c) * (np.array(Ymat_values) + np.array(Xmat_values))),  # advanced expressions
        (
            "Cos(x) * (Ymat + 2*Xmat - Ymat) * Sin(x)",
            np.cos(x) * (np.array(Ymat_values) + 2 * np.array(Xmat_values) - np.array(Ymat_values)) * np.sin(x),
        ),  # advanced expressions
        (
            "Sum(Vmat) * (Zmat @ (Xmat + 3*Ymat) @ -Xmat)",
            np.sum(Vmat_values)
            * (np.array(Zmat_values) @ (np.array(Xmat_values) + 3 * np.array(Ymat_values)) @ -np.array(Xmat_values)),
        ),  # advanced expressions
    ]

    pyomo_parser = MathParser(to_format="pyomo")
    infix_parser = InfixExpressionParser()

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        pyomo_expr = pyomo_parser.parse(json_expr, pyomo_model)

        npt.assert_array_almost_equal(
            [pyomo.value(pyomo_expr[i]) for i in pyomo_expr.index_set()]
            if hasattr(pyomo_expr, "index_set") and pyomo_expr.index_set().dimen == 1
            else [
                [pyomo.value(pyomo_expr[i, j]) for j in pyomo_expr.index_set().set_tuple[1]]
                for i in pyomo_expr.index_set().set_tuple[0]
            ]
            if hasattr(pyomo_expr, "index_set") and pyomo_expr.index_set().dimen == 2
            else pyomo.value(pyomo_expr),
            result,
            err_msg=(
                f"Test failed for {str_expr=}, with "
                f"{str(pyomo_expr) if isinstance(pyomo_expr, pyomo.Expression) else pyomo_expr}"
            ),
        )


@pytest.mark.sympy
def test_parse_sympy_basic_arithmetics():
    """Check that the JSON parser correctly parses MathJSON to sympy expressions."""
    x_1 = 4.2
    x_2 = 6
    x_3 = -9.9
    variables = [x_1, x_2, x_3]
    variable_symbols = ["x_1", "x_2", "x_3"]

    c_1 = 1.9
    c_2 = -9.2
    constants = [c_1, c_2]
    constant_symbols = ["c_1", "c_2"]

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
    sympy_parser = MathParser(to_format=FormatEnum.sympy)

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        sympy_expr = sympy_parser.parse(json_expr)

        f = sp.lambdify([*variable_symbols, *constant_symbols], sympy_expr)

        npt.assert_almost_equal(
            f(*variables, *constants), result, err_msg=(f"Test failed for {str_expr=}, with " f"{sympy_expr=}.")
        )


@pytest.mark.gurobipy
def test_parse_gurobipy_basic_arithmetics():
    """Test the JSON parser for correctly parsing MathJSON into gurobipy expressions."""
    gp_model = gp.Model("Test model")

    x_1 = 6.9
    x_2 = 0.1
    x_3 = 11.1
    gp_model.addConstr(gp_model.addVar(name="x_1", obj=1) >= x_1)
    gp_model.addConstr(gp_model.addVar(name="x_2", obj=1) >= x_2)
    gp_model.addConstr(gp_model.addVar(name="x_3", obj=1) >= x_3)

    constants = {}
    c_1 = 4.2
    constants["c_1"] = 4.2
    c_2 = 2.2
    constants["c_2"] = 2.2
    gp_model.update()
    gp_model.optimize()

    def callback(name: str):
        expression = gp_model.getVarByName(name)
        if expression is None:  # noqa: SIM102
            if name in constants:
                expression = constants[name]
        return expression

    tests = [
        ("x_1 + x_2 + x_3", x_1 + x_2 + x_3),
        ("x_1 + x_2 + x_3 - c_1 - c_2", x_1 + x_2 + x_3 - c_1 - c_2),
        ("x_1 - x_2 + c_1", x_1 - x_2 + c_1),
        ("x_1 * c_2", x_1 * c_2),
        ("x_2 / 4.2", x_2 / 4.2),
        ("(x_1 + x_2) * c_1", (x_1 + x_2) * c_1),
        ("((x_1 + x_2) - x_3) / 4.2", ((x_1 + x_2) - x_3) / 4.2),
        ("x_1 + 2 * x_2 - 3", x_1 + 2 * x_2 - 3),
        ("(x_1 + (x_2 * c_2) / (4.2 - 11.1)) * 2", (x_1 + (x_2 * c_2) / (4.2 - 11.1)) * 2),
        ("x_3 * c_2 / 2", x_3 * c_2 / 2),
        ("(x_1 + 10) - (c_2 - 5)", (x_1 + 10) - (c_2 - 5)),
        ("((x_1 * 2) + (x_2 / 0.5)) - (c_1 * (x_3 + 3))", ((x_1 * 2) + (x_2 / 0.5)) - (c_1 * (x_3 + 3))),
        ("(x_1 - (x_2 * 2) + (11.1 + 5.5) + c_1) + (c_2 + 4.4)", (x_1 - (x_2 * 2) + (11.1 + 5.5) + c_1) + (c_2 + 4.4)),
        ("x_1 - ((x_2 + 2.1) * (c_1 - 3))", x_1 - ((x_2 + 2.1) * (c_1 - 3))),
        ("(x_1 + (x_2 * (c_1 + 3.3) + (x_3 - 2))) * 1.5", (x_1 + (x_2 * (c_1 + 3.3) + (x_3 - 2))) * 1.5),
        ("(x_1 - (x_2 + (2.5 * c_1))) - (c_2 - (x_3 * 0.5))", (x_1 - (x_2 + (2.5 * c_1))) - (c_2 - (x_3 * 0.5))),
        (
            "((x_1 * c_1) + (x_2 - c_2) / 2.0) + (x_3 + 3.5) * (1 + c_1)",
            ((x_1 * c_1) + (x_2 - c_2) / 2.0) + (x_3 + 3.5) * (1 + c_1),
        ),
        ("(x_1 ** 2 + x_2 ** 2) - c_1 * 3 + (x_3 - c_2)", (x_1**2 + x_2**2) - c_1 * 3 + (x_3 - c_2)),
    ]

    infix_parser = InfixExpressionParser()
    gurobipy_parser = MathParser(to_format=FormatEnum.gurobipy)

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        gurobipy_expr = gurobipy_parser.parse(json_expr, callback)
        # print(str_expr)

        npt.assert_array_almost_equal(
            gurobipy_expr.getValue(), result, err_msg=f"Test failed for {str_expr}, with {gurobipy_expr}"
        )


@pytest.mark.sympy
def test_parse_sympy_exponentation_and_logarithms():
    """Test the JSON parser for correctly parsing MathJSON into sympy expressions, with exponentation and logarithms."""
    x = -6.9
    y = 1
    garlic = 11.1
    variables = [x, y, garlic]
    variable_symbols = ["x", "y", "garlic"]

    cosmic = 4.2
    potato = -2
    constants = [cosmic, potato]
    constant_symbols = ["cosmic", "potato"]

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
    sympy_parser = MathParser(to_format=FormatEnum.sympy)

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        sympy_expr = sympy_parser.parse(json_expr)

        f = sp.lambdify([*variable_symbols, *constant_symbols], sympy_expr)

        npt.assert_almost_equal(
            f(*variables, *constants), result, err_msg=(f"Test failed for {str_expr=}, with " f"{sympy_expr=}.")
        )


@pytest.mark.sympy
def test_parse_sympy_trigonometrics():
    """Test the JSON parser for correctly parsing MathJSON into sympy expressions, with trigonometric operators."""
    x = 0.8
    y = 1.4
    garlic = 4.2
    variables = [x, y, garlic]
    variable_symbols = ["x", "y", "garlic"]

    cosmic = 0.42
    potato = 0.22
    constants = [cosmic, potato]
    constant_symbols = ["cosmic", "potato"]

    tests = [
        ("Arccos(x)", math.acos(x)),
        ("Arccosh(y)", math.acosh(y)),
        ("Arcsin(x)", math.asin(x)),
        ("Arcsinh(y)", math.asinh(y)),
        ("Arctan(garlic)", math.atan(garlic)),
        ("Arctanh(x)", math.atanh(x)),
        ("Cos(garlic)", math.cos(garlic)),
        ("Cosh(x)", math.cosh(x)),
        ("Sin(garlic)", math.sin(garlic)),
        ("Sinh(x)", math.sinh(x)),
        ("Tan(garlic)", math.tan(garlic)),
        ("Tanh(x)", math.tanh(x)),
        ("Sin(garlic) + Cos(x)", math.sin(garlic) + math.cos(x)),
        ("Tan(Arccos(y / Sqrt(y**2 + 1)))", math.tan(math.acos(y / math.sqrt(y**2 + 1)))),
        ("Sinh(x) * Cos(garlic) - Tanh(x)", math.sinh(x) * math.cos(garlic) - math.tanh(x)),
        ("Arctan(garlic**2) + Arctanh(x / 2)", math.atan(garlic**2) + math.atanh(x / 2)),
        ("Cos(Sin(garlic)) + Tanh(Arccosh(y))", math.cos(math.sin(garlic)) + math.tanh(math.acosh(y))),
        (
            "Arcsinh(y) * Arctan(garlic) - Arccosh(Sqrt(y**2 + 1))",
            math.asinh(y) * math.atan(garlic) - math.acosh(math.sqrt(y**2 + 1)),
        ),
        ("Sin(garlic) * Cos(x) + Tanh(x)", math.sin(garlic) * math.cos(x) + math.tanh(x)),
        ("Sqrt(Sin(garlic)**2 + Cos(x)**2)", math.sqrt(math.sin(garlic) ** 2 + math.cos(x) ** 2)),
        (
            "Cosh(Arctan(garlic)) - Sinh(Arccos(y / Sqrt(y**2 + 1)))",
            math.cosh(math.atan(garlic)) - math.sinh(math.acos(y / math.sqrt(y**2 + 1))),
        ),
        ("Sin(garlic) + Cos(x)", math.sin(garlic) + math.cos(x)),
        ("Tan(Arccos(y / Sqrt(y**2 + 1)))", math.tan(math.acos(y / math.sqrt(y**2 + 1)))),
        ("Sinh(x) * Cos(garlic) - Tanh(x)", math.sinh(x) * math.cos(garlic) - math.tanh(x)),
        ("Arctan(garlic**2) + Arctanh(x / 2)", math.atan(garlic**2) + math.atanh(x / 2)),
        ("Cos(Sin(garlic)) + Tanh(Arccosh(y))", math.cos(math.sin(garlic)) + math.tanh(math.acosh(y))),
        (
            "Arcsinh(y) * Arctan(garlic) - Arccosh(Sqrt(y**2 + 1))",
            math.asinh(y) * math.atan(garlic) - math.acosh(math.sqrt(y**2 + 1)),
        ),
        ("Sin(garlic) * Cos(x) + Tanh(x)", math.sin(garlic) * math.cos(x) + math.tanh(x)),
        ("Sqrt(Sin(garlic)**2 + Cos(x)**2)", math.sqrt(math.sin(garlic) ** 2 + math.cos(x) ** 2)),
        (
            "Cosh(Arctan(garlic)) - Sinh(Arccos(y / Sqrt(y**2 + 1)))",
            math.cosh(math.atan(garlic)) - math.sinh(math.acos(y / math.sqrt(y**2 + 1))),
        ),
    ]

    infix_parser = InfixExpressionParser()
    sympy_parser = MathParser(to_format=FormatEnum.sympy)

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        sympy_expr = sympy_parser.parse(json_expr)

        f = sp.lambdify([*variable_symbols, *constant_symbols], sympy_expr)

        npt.assert_almost_equal(
            f(*variables, *constants), result, err_msg=(f"Test failed for {str_expr=}, with " f"{sympy_expr=}.")
        )


@pytest.mark.sympy
def test_parse_sympy_rounding():
    """Test the JSON parser for correctly parsing MathJSON into sympy expressions, with rounding operators."""
    x = 2.8
    y = -1.4
    garlic = 4.2
    variables = [x, y, garlic]
    variable_symbols = ["x", "y", "garlic"]

    cosmic = -69.42
    potato = 99.22
    constants = [cosmic, potato]
    constant_symbols = ["cosmic", "potato"]

    tests = [
        ("Abs(y)", abs(y)),
        ("Ceil(potato)", math.ceil(potato)),
        ("Floor(cosmic)", math.floor(cosmic)),
        ("Ceil(x + garlic)", math.ceil(x + garlic)),
        ("Floor(x - cosmic)", math.floor(x - cosmic)),
        ("Abs(cosmic + potato)", abs(cosmic + potato)),
        ("Ceil(Floor(garlic) + Abs(x))", math.ceil(math.floor(garlic) + abs(x))),
        (
            "Abs(Ceil(x) - Floor(y)) + Floor(garlic - Ceil(potato))",
            abs(math.ceil(x) - math.floor(y)) + math.floor(garlic - math.ceil(potato)),
        ),
        ("Ceil(Abs(x) + Abs(cosmic))", math.ceil(abs(x) + abs(cosmic))),
        (
            "Floor(Ceil(x) + Abs(Ceil(y) + Floor(garlic)))",
            math.floor(math.ceil(x) + abs(math.ceil(y) + math.floor(garlic))),
        ),
        (
            "Ceil(Sin(garlic)**2 + Cos(x)**2) + Floor(LogOnePlus(Abs(x)))",
            math.ceil(math.sin(garlic) ** 2 + math.cos(x) ** 2) + math.floor(math.log1p(abs(x))),
        ),
        (
            "Abs(Tanh(x) - Sinh(y)) + Lb(Ceil(Abs(garlic)) + 1) * Sqrt(Abs(Floor(potato)))",
            abs(math.tanh(x) - math.sinh(y))
            + math.log(math.ceil(abs(garlic)) + 1, 2) * math.sqrt(abs(math.floor(potato))),
        ),
        (
            "Floor(Cosh(Abs(x)) + Sin(Arctan(Abs(garlic)))) * Ln(Ceil(Abs(y)) + 1)",
            math.floor(math.cosh(abs(x)) + math.sin(math.atan(abs(garlic)))) * math.log(math.ceil(abs(y)) + 1),
        ),
        (
            "Ln(Ceil(Abs(Sin(garlic) * Tanh(x)) + Floor(Cosh(Abs(y))))) + Sqrt(Abs(Floor(Abs(cosmic))))",
            math.log(math.ceil(abs(math.sin(garlic) * math.tanh(x)) + math.floor(math.cosh(abs(y)))))
            + math.sqrt(abs(math.floor(abs(cosmic)))),
        ),
        (
            "Ceil(Lg(Abs(Cos(x) * Sin(garlic)))) + Arctan(Floor(Abs(Tanh(Abs(potato)))))",
            math.ceil(math.log10(abs(math.cos(x) * math.sin(garlic))))
            + math.atan(math.floor(abs(math.tanh(abs(potato))))),
        ),
    ]

    infix_parser = InfixExpressionParser()
    sympy_parser = MathParser(to_format=FormatEnum.sympy)

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        sympy_expr = sympy_parser.parse(json_expr)

        f = sp.lambdify([*variable_symbols, *constant_symbols], sympy_expr)

        npt.assert_almost_equal(
            f(*variables, *constants), result, err_msg=(f"Test failed for {str_expr=}, with " f"{sympy_expr=}.")
        )


@pytest.mark.sympy
def test_parse_sympy_max():
    """Test the JSON parser for correctly parsing MathJSON into sympy expressions, with the max operator."""
    x = 2.8
    y = -1.4
    garlic = 4.2
    variables = [x, y, garlic]
    variable_symbols = ["x", "y", "garlic"]

    cosmic = -69.42
    potato = 99.22
    constants = [cosmic, potato]
    constant_symbols = ["cosmic", "potato"]

    tests = [
        ("Max(x)", max((x,))),
        ("Max(x, y)", max((x, y))),
        ("Max(x, y, potato)", max((x, y, potato))),
        ("Max(Abs(cosmic), x)", max((abs(cosmic), x))),
        ("Max(x + 2, y - 3, garlic)", max((x + 2, y - 3, garlic))),
        ("Max(Abs(x), Abs(y), Abs(cosmic))", max((abs(x), abs(y), abs(cosmic)))),
        ("Max(potato, cosmic, x, y)", max((potato, cosmic, x, y))),
        ("Max(Max(x, y), Max(garlic, cosmic))", max((max((x, y)), max((garlic, cosmic))))),
        ("Max(x * 2 - 3, Abs(cosmic) + 4, y / 2)", max((x * 2 - 3, abs(cosmic) + 4, y / 2))),
        ("Max(x, y, garlic, cosmic, potato)", max((x, y, garlic, cosmic, potato))),
        (
            "Max(Abs(x - y), garlic + 10, cosmic * 2, potato / 2)",
            max((abs(x - y), garlic + 10, cosmic * 2, potato / 2)),
        ),
        (
            "Max(Ceil(Sin(garlic) + Tanh(x)), Floor(Ln(Abs(cosmic)) + 1), x ** 2, Sqrt(potato))",
            max(
                (
                    math.ceil(math.sin(garlic) + math.tanh(x)),
                    math.floor(math.log(abs(cosmic)) + 1),
                    x**2,
                    math.sqrt(potato),
                )
            ),
        ),
        (
            "Max(Ln(x) + Lb(Abs(y)), Ceil(Sqrt(garlic) * 3), (potato ** 2) / 4, Abs(cosmic) + 10)",
            max(
                (math.log(x) + math.log(abs(y), 2), math.ceil(math.sqrt(garlic) * 3), (potato**2) / 4, abs(cosmic) + 10)
            ),
        ),
        (
            "Max(Abs(x - y), Max(Sin(x), Cos(garlic)), Tanh(potato) + 1)",
            max((abs(x - y), max((math.sin(x), math.cos(garlic))), math.tanh(potato) + 1)),
        ),
        (
            "Max(Abs(Max(cosmic, x) + Sin(garlic)), Floor(Abs(y) + Ceil(garlic)))",
            max((abs(max((cosmic, x)) + math.sin(garlic)), math.floor(abs(y) + math.ceil(garlic)))),
        ),
        (
            "Max(Sqrt(Abs(x) + y ** 2), Lg(Max(cosmic, potato)), Ceil(Tanh(x) + Arctan(garlic)))",
            max(
                (
                    math.sqrt(abs(x) + y**2),
                    math.log10(max((cosmic, potato))),
                    math.ceil(math.tanh(x) + math.atan(garlic)),
                )
            ),
        ),
    ]

    infix_parser = InfixExpressionParser()
    sympy_parser = MathParser(to_format=FormatEnum.sympy)

    for str_expr, result in tests:
        json_expr = infix_parser.parse(str_expr)
        sympy_expr = sympy_parser.parse(json_expr)

        f = sp.lambdify([*variable_symbols, *constant_symbols], sympy_expr)

        npt.assert_almost_equal(
            f(*variables, *constants), result, err_msg=(f"Test failed for {str_expr=}, with " f"{sympy_expr=}.")
        )
