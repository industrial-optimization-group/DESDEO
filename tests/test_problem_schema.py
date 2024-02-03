"""Tests related to the schemas representing multiobjective optimization problems."""
import numpy.testing as npt
import polars as pl

from desdeo.problem.json_parser import MathParser
from desdeo.problem.schema import Constraint, ExtraFunction, Objective, ScalarizationFunction


def test_objective_from_infix():
    """Test the initialization of an Objective using infix notation."""
    infix = "1 + x_2 - Sin(x_1)"
    json = ["Add", 1, "x_2", ["Negate", ["Sin", "x_1"]]]
    objective = Objective(name="test", symbol="f_1", ideal=0, nadir=0, maximize=False, func=infix)

    parser = MathParser()

    expr_infix = parser.parse(objective.func)
    expr_json = parser.parse(json)

    data = pl.DataFrame({"x_1": [1, 2, 3], "x_2": [4, 5, 6]})

    res_infix = data.select(expr_infix.alias("res"))["res"]
    res_json = data.select(expr_json.alias("res"))["res"]

    npt.assert_array_almost_equal(res_infix, res_json)


def test_constraint_from_infix():
    """Test the initialization of a Constraint using infix notation."""
    infix = "Max(x_1 + 5, 5.0 - x_2)"
    json = ["Max", [["Add", "x_1", 5], ["Add", 5.0, ["Negate", "x_2"]]]]
    constraint = Constraint(name="test", symbol="c_1", func=infix, cons_type="=")

    parser = MathParser()

    expr_infix = parser.parse(constraint.func)
    expr_json = parser.parse(json)

    data = pl.DataFrame({"x_1": [1, 2, 3], "x_2": [4, 5, 6]})

    res_infix = data.select(expr_infix.alias("res"))["res"]
    res_json = data.select(expr_json.alias("res"))["res"]

    npt.assert_array_almost_equal(res_infix, res_json)


def test_scalarization_from_infix():
    """Test the initialization of a ScalarizationFunction using infix notation."""
    infix = "5 + Max(x_1 / x_2, x_1 * x_2, x_1**(2))"
    json = ["Add", 5, ["Max", [["Divide", "x_1", "x_2"], ["Multiply", "x_1", "x_2"], ["Power", "x_1", 2]]]]
    scalarization_func = ScalarizationFunction(name="test", symbol="s_1", func=infix)

    parser = MathParser()

    expr_infix = parser.parse(scalarization_func.func)
    expr_json = parser.parse(json)

    data = pl.DataFrame({"x_1": [-2, 2, 5], "x_2": [-4.2, 5, 6.9]})

    res_infix = data.select(expr_infix.alias("res"))["res"]
    res_json = data.select(expr_json.alias("res"))["res"]

    npt.assert_array_almost_equal(res_infix, res_json)


def test_extra_from_infix():
    """Test the initialization of an ExtraFunction using infix notation."""
    infix = "Floor(10.1 / x_1) + Ceil(x_2 / 6.5)"
    json = ["Add", ["Floor", ["Divide", 10.1, "x_1"]], ["Ceil", ["Divide", "x_2", 6.5]]]
    extra = ExtraFunction(name="test", symbol="s_1", func=infix)

    parser = MathParser()

    expr_infix = parser.parse(extra.func)
    expr_json = parser.parse(json)

    data = pl.DataFrame({"x_1": [-2, 2, 5], "x_2": [-4.2, 5, 6.9]})

    res_infix = data.select(expr_infix.alias("res"))["res"]
    res_json = data.select(expr_json.alias("res"))["res"]

    npt.assert_array_almost_equal(res_infix, res_json)
