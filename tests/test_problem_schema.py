"""Tests related to the schemas representing multiobjective optimization problems."""
import numpy.testing as npt
import polars as pl

from desdeo.problem.json_parser import MathParser
from desdeo.problem.schema import (
    Constraint,
    DiscreteDefinition,
    ExtraFunction,
    Objective,
    Problem,
    ScalarizationFunction,
    Variable,
)
from desdeo.problem.evaluator import GenericEvaluator


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


def test_data_objective():
    """Tests a problem with a data objective."""
    variables = [
        Variable(
            name=f"x_{i}", symbol=f"x_{i}", variable_type="real", lowerbound=-5.2, upperbound=4.8, initial_value=0.5
        )
        for i in range(1, 3)
    ]
    f1_expr = "x_1 + x_2**2 - Max(x_1, x_2)"

    objective_1 = Objective(name="f_1", symbol="f_1", func=f1_expr, maximize=False)

    objective_2 = Objective(name="f_2", symbol="f_2", func=None, objective_type="data_based", maximize=True)

    var_data = {
        "x_1": [0.5, 2.5, -3.5, 0.1],
        "x_2": [1.5, -1.5, 1.5, -0.1],
    }
    obj_data = {"f_2": [x_1 + x_2 for x_1, x_2 in zip(var_data["x_1"], var_data["x_2"], strict=True)]}

    data_definition = DiscreteDefinition(variable_values=var_data, objective_values=obj_data)

    problem = Problem(
        name="data-based problem test",
        description="For testing",
        objectives=[objective_1, objective_2],
        variables=variables,
        discrete_definition=data_definition,
    )

    evaluator = GenericEvaluator(problem)

    xs = {"x_1": [2.4, 0.05, 0.4], "x_2": [-1.4, -0.05, 1.3]}

    eval_res = evaluator.evaluate(xs)

    # compare eval res, f_1 = "x_1 + x_2**2 - Max(x_1, x_2)", and f_2 = x_1 + x_2

    npt.assert_array_almost_equal(
        [x_1 + x_2**2 - max([x_1, x_2]) for x_1, x_2 in zip(xs["x_1"], xs["x_2"], strict=True)],
        eval_res.objective_values["f_1"],
    )

    npt.assert_array_almost_equal([2.5 + -1.5, 0.1 + -0.1, 0.5 + 1.5], eval_res.objective_values["f_2"])
