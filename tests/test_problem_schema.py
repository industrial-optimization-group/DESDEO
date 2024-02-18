"""Tests related to the schemas representing multiobjective optimization problems."""
import numpy.testing as npt
import polars as pl
import pytest  # noqa: F401

from desdeo.problem.json_parser import MathParser
from desdeo.problem.schema import (
    Constraint,
    DiscreteDefinition,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    ScalarizationFunction,
    Variable,
    VariableTypeEnum,
)
from desdeo.problem.evaluator import GenericEvaluator

from desdeo.tools.scalarization import add_scalarization_function

from fixtures import dtlz2_5x_3f_data_based  # noqa: F401


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
        eval_res["f_1"],
    )

    npt.assert_array_almost_equal([2.5 + -1.5, 0.1 + -0.1, 0.5 + 1.5], eval_res["f_2"])


def test_data_problem(dtlz2_5x_3f_data_based):  # noqa: F811
    """Tests the evaluation of a problem with only data objectives."""
    problem = dtlz2_5x_3f_data_based

    evaluator = GenericEvaluator(problem)

    n_input = 10
    xs = {
        "x1": [
            0.5,
            0.5,
            0.058933292079031085,
            0.568627185142172,
            0.3441500730504361,
            0.8545733304617269,
            0.9272411190475092,
            0.007690581519525286,
            0.9090671387118816,
            0.07141463778009649,
        ],
        "x2": [
            0.2,
            0.4,
            0.6045535577489826,
            0.28712096312673085,
            0.0972814234703101,
            0.873533220112079,
            0.7409069506233055,
            0.9579204115062728,
            0.3189706295496102,
            0.5585049750880551,
        ],
        "x3": [
            0.9,
            0.1,
            0.4428645652739157,
            0.14258837293033566,
            0.2941046058668525,
            0.8016906727667247,
            0.28875624463989247,
            0.7180094891313515,
            0.998503216317003,
            0.5830186435374128,
        ],
        "x4": [
            0.1,
            0.9,
            0.2572949575804011,
            0.7390210756613486,
            0.20496408757374118,
            0.5558856047384275,
            0.6167896940614638,
            0.9129284018955703,
            0.18418029533717595,
            0.4069113987248817,
        ],
        "x5": [
            0.4,
            0.6,
            0.37036805441222154,
            0.3695885834483116,
            0.21046481374349546,
            0.1967692836513416,
            0.48666567007484285,
            0.19151606293797985,
            0.37958833949630955,
            0.8321661269747351,
        ],
    }

    res = evaluator.evaluate(xs)

    # all the solutions evaluated should be close to Pareto optimality (we know there is a 0.01 tolerance in the data)
    obj_symbols = [obj.symbol for obj in problem.objectives]
    objective_values = res[obj_symbols].to_dict(as_series=False)
    assert all(
        abs(sum(objective_values[f_key][i] ** 2 for f_key in objective_values) - 1.0) < 0.01 for i in range(n_input)
    )

    # take directly some decision variables values from the data and make sure they evaluate correctly
    xs = {
        "x1": [
            0.1855437858885801,
            0.6444446513948299,
            0.2554487181544489,
            0.5488223224669113,
            0.23903395483341938,
            0.29309453892702203,
            0.18535427573362392,
            0.05751804043598988,
            0.26604387361509446,
            0.8599501462066285,
        ],
        "x2": [
            1.0,
            0.0,
            0.49995462210876557,
            0.0,
            0.2570790391295068,
            0.9208549775240716,
            0.0,
            0.9423839289462318,
            1.0,
            0.7041761798637635,
        ],
        "x3": [
            0.5118155116582402,
            0.4986619397546664,
            0.5275518500926538,
            0.49705952818499866,
            0.49541351977747106,
            0.5010052414967497,
            0.5009613675610162,
            0.5106619098002502,
            0.5056446257711289,
            0.49380369981865385,
        ],
        "x4": [
            0.4986258005390593,
            0.5002335327667501,
            0.4973945846679122,
            0.4983108809186191,
            0.4961462094513439,
            0.5015806399868823,
            0.502678043720949,
            0.5029274410653807,
            0.49681465733421887,
            0.5065886203587019,
        ],
        "x5": [
            0.5003725609145294,
            0.49896694329671415,
            0.4948458502988517,
            0.49934717566813663,
            0.49815692274039775,
            0.5021182769257488,
            0.4980355703334864,
            0.4985254991567869,
            0.5030733421386511,
            0.5028400679565715,
        ],
    }

    expected_fs = {
        "f1": [
            5.865834473169222e-17,
            0.5299205317553395,
            0.651503859176299,
            0.650861366725754,
            0.8555382357060214,
            0.11109046046117708,
            0.957924753610067,
            0.09002218160976368,
            5.596574326667622e-17,
            0.09780084029552562,
        ],
        "f2": [
            0.9579634678755125,
            0.0,
            0.6514109881551711,
            0.0,
            0.36557316386918964,
            0.8889713119473678,
            0.0,
            0.9919687795841546,
            0.9139899488675715,
            0.19509837869899882,
        ],
        "f3": [
            0.28738350919818084,
            0.8480507380637493,
            0.390886159593875,
            0.7592123107542801,
            0.3667276366997508,
            0.44430272141162297,
            0.2870611029438926,
            0.09023748333152137,
            0.4058636264760891,
            0.9759873802583043,
        ],
    }

    res = evaluator.evaluate(xs)

    objective_values = res[obj_symbols].to_dict(as_series=False)

    for obj in objective_values:
        npt.assert_array_almost_equal(objective_values[obj], expected_fs[obj])

    # test adding a scalarization function
    problem, symbol = add_scalarization_function(problem, "f1 + f2 + f3", "simple_sum")

    evaluator = GenericEvaluator(problem)

    res = evaluator.evaluate(xs)

    should_be = [sum(expected_fs[f"f{i}"][j] for i in range(1, len(problem.objectives) + 1)) for j in range(n_input)]

    actual = res[symbol]

    npt.assert_array_almost_equal(should_be, actual)
