"""Tests related to the schemas representing multiobjective optimization problems."""

import numpy.testing as npt
import polars as pl
import pytest
from fixtures import dtlz2_5x_3f_data_based  # noqa: F401

from desdeo.problem.evaluator import PolarsEvaluator
from desdeo.problem.json_parser import MathParser
from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    Problem,
    ScalarizationFunction,
    Variable,
    VariableDomainTypeEnum,
    VariableTypeEnum,
)
from desdeo.problem.testproblems import (
    momip_ti7,
    nimbus_test_problem,
    river_pollution_problem,
    simple_knapsack,
    simple_scenario_test_problem,
)


@pytest.mark.schema
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


@pytest.mark.schema
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


@pytest.mark.schema
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


@pytest.mark.schema
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


@pytest.mark.schema
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

    data_definition = DiscreteRepresentation(variable_values=var_data, objective_values=obj_data)

    problem = Problem(
        name="data-based problem test",
        description="For testing",
        objectives=[objective_1, objective_2],
        variables=variables,
        discrete_representation=data_definition,
    )

    evaluator = PolarsEvaluator(problem)

    xs = {"x_1": [2.4, 0.05, 0.4], "x_2": [-1.4, -0.05, 1.3]}

    eval_res = evaluator.evaluate(xs)

    # compare eval res, f_1 = "x_1 + x_2**2 - Max(x_1, x_2)", and f_2 = x_1 + x_2

    npt.assert_array_almost_equal(
        [x_1 + x_2**2 - max([x_1, x_2]) for x_1, x_2 in zip(xs["x_1"], xs["x_2"], strict=True)],
        eval_res["f_1"],
    )

    npt.assert_array_almost_equal([2.5 + -1.5, 0.1 + -0.1, 0.5 + 1.5], eval_res["f_2"])


@pytest.mark.schema
def test_data_problem(dtlz2_5x_3f_data_based):  # noqa: F811
    """Tests the evaluation of a problem with only data objectives."""
    problem = dtlz2_5x_3f_data_based

    evaluator = PolarsEvaluator(problem)

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
    symbol = "simple_sum"
    problem = problem.add_scalarization(
        ScalarizationFunction(
            name=symbol,
            symbol=symbol,
            func="f1 + f2 + f3",
            is_linear=problem.is_linear,
            is_convex=problem.is_convex,
            is_twice_differentiable=problem.is_twice_differentiable,
        )
    )

    evaluator = PolarsEvaluator(problem)

    res = evaluator.evaluate(xs)

    should_be = [sum(expected_fs[f"f{i}"][j] for i in range(1, len(problem.objectives) + 1)) for j in range(n_input)]

    actual = res[symbol]

    npt.assert_array_almost_equal(should_be, actual)


@pytest.mark.schema
def test_add_constraints():
    """Test that constraints are added properly."""
    problem = river_pollution_problem()
    assert problem.constraints is None

    cons_1 = Constraint(name="con 1", symbol="g_1", func="x_1 + x_2", is_linear=False, cons_type=ConstraintTypeEnum.EQ)
    cons_2 = Constraint(name="con 2", symbol="g_2", func="x_1 - x_2", is_linear=True, cons_type=ConstraintTypeEnum.LTE)
    cons_3 = Constraint(name="con 3", symbol="g_3", func="x_1 * x_2", is_linear=True, cons_type=ConstraintTypeEnum.EQ)

    constraints = [cons_1, cons_2, cons_3]

    new_problem = problem.add_constraints(constraints)

    assert problem.constraints is None
    assert len(new_problem.constraints) == 3

    assert new_problem.constraints[0].name == "con 1"
    assert new_problem.constraints[0].symbol == "g_1"
    assert new_problem.constraints[0].func == ["Add", "x_1", "x_2"]
    assert not new_problem.constraints[0].is_linear
    assert new_problem.constraints[0].cons_type == ConstraintTypeEnum.EQ

    assert new_problem.constraints[1].name == "con 2"
    assert new_problem.constraints[1].symbol == "g_2"
    assert new_problem.constraints[1].func == ["Add", "x_1", ["Negate", "x_2"]]
    assert new_problem.constraints[1].is_linear
    assert new_problem.constraints[1].cons_type == ConstraintTypeEnum.LTE

    assert new_problem.constraints[2].name == "con 3"
    assert new_problem.constraints[2].symbol == "g_3"
    assert new_problem.constraints[2].func == ["Multiply", "x_1", "x_2"]
    assert new_problem.constraints[2].is_linear
    assert new_problem.constraints[2].cons_type == ConstraintTypeEnum.EQ

    # check that only list is accepted
    with pytest.raises(TypeError):
        new_problem.add_constraints(cons_1)

    # check that we cannot add a constraint with an existing symbol
    with pytest.raises(ValueError):
        new_problem.add_constraints([cons_2])

    # check that symbol duplicate is checked in other fields as well
    with pytest.raises(ValueError):
        cons_x = Constraint(name="con 1", symbol="x_1", func="x_1 + x_2", linear=False, cons_type=ConstraintTypeEnum.EQ)
        new_problem.add_constraints([cons_x])


@pytest.mark.schema
def test_add_variables():
    """Test that new variables are added to a problem model correctly."""
    problem = river_pollution_problem()
    assert len(problem.variables) == 2

    var_1 = Variable(
        name="y_1", symbol="y_1", variable_type=VariableTypeEnum.integer, lowerbound=0, upperbound=10, initial_value=5
    )
    var_2 = Variable(
        name="y_2", symbol="y_2", variable_type=VariableTypeEnum.real, lowerbound=1.1, upperbound=2.2, initial_value=1.5
    )
    var_3 = Variable(
        name="y_3", symbol="y_3", variable_type=VariableTypeEnum.binary, lowerbound=0, upperbound=1, initial_value=1
    )

    variables = [var_1, var_2, var_3]

    new_problem = problem.add_variables(variables)

    assert len(problem.variables) == 2
    assert len(new_problem.variables) == 5

    assert new_problem.variables[2].name == "y_1"
    assert new_problem.variables[2].symbol == "y_1"
    assert new_problem.variables[2].variable_type == VariableTypeEnum.integer
    assert new_problem.variables[2].lowerbound == 0
    assert new_problem.variables[2].upperbound == 10
    assert new_problem.variables[2].initial_value == 5

    assert new_problem.variables[3].name == "y_2"
    assert new_problem.variables[3].symbol == "y_2"
    assert new_problem.variables[3].variable_type == VariableTypeEnum.real
    assert new_problem.variables[3].lowerbound == 1.1
    assert new_problem.variables[3].upperbound == 2.2
    assert new_problem.variables[3].initial_value == 1.5

    assert new_problem.variables[4].name == "y_3"
    assert new_problem.variables[4].symbol == "y_3"
    assert new_problem.variables[4].variable_type == VariableTypeEnum.binary
    assert new_problem.variables[4].lowerbound == 0
    assert new_problem.variables[4].upperbound == 1
    assert new_problem.variables[4].initial_value == 1

    # check that only list is accepted
    with pytest.raises(TypeError):
        problem.add_variables(var_1)

    # check that we cannot add a variable with an existing symbol
    with pytest.raises(ValueError):
        new_problem.add_variables([var_1])

    # check that symbol duplicate is checked in other fields as well
    with pytest.raises(ValueError):
        var_x = Variable(
            name="var 1",
            symbol="f_1",
            variable_type=VariableTypeEnum.real,
            lowerbound=0.0,
            upperbound=1.1,
            initial_value=0.5,
        )
        new_problem.add_variables([var_x])


@pytest.mark.schema
def test_get_ideal_point():
    """Test that the ideal point is returned correctly."""
    problem = nimbus_test_problem()
    ideal_point = problem.get_ideal_point()

    for obj in problem.objectives:
        npt.assert_almost_equal(obj.ideal, ideal_point[obj.symbol])


@pytest.mark.schema
def test_get_nadir_point():
    """Test that the nadir point is returned correctly."""
    problem = nimbus_test_problem()
    nadir_point = problem.get_nadir_point()

    for obj in problem.objectives:
        npt.assert_almost_equal(obj.nadir, nadir_point[obj.symbol])


@pytest.mark.schema
def test_variable_domain():
    """Test that the variable domain of a problem is inferred correctly."""
    problem_continuous = river_pollution_problem()

    assert problem_continuous.variable_domain == VariableDomainTypeEnum.continuous

    problem_mixed = momip_ti7()

    assert problem_mixed.variable_domain == VariableDomainTypeEnum.mixed

    integer_problem = simple_knapsack()

    assert integer_problem.variable_domain == VariableDomainTypeEnum.integer


@pytest.mark.schema
def test_is_convex():
    """Test whether the convexity of a problem is inferred correctly."""
    problem_convex = simple_knapsack()

    assert problem_convex.is_convex

    problem_non_convex = river_pollution_problem()

    assert not problem_non_convex.is_convex


@pytest.mark.schema
def test_is_linear():
    """Test whether the linearity of a problem is inferred correctly."""
    problem_linear = simple_knapsack()

    assert problem_linear.is_linear

    problem_nonlinear = river_pollution_problem()

    assert not problem_nonlinear.is_linear


@pytest.mark.schema
def test_is_twice_diff():
    """Test whether the twice differentiability of a problem is inferred correctly."""
    problem_diff = simple_knapsack()

    assert problem_diff.is_twice_differentiable

    problem_nondiff = river_pollution_problem()

    assert not problem_nondiff.is_twice_differentiable


@pytest.mark.schema
def test_scenario_problem():
    """Tests that scenario problems are handled correctly."""
    problem = simple_scenario_test_problem()

    assert len(problem.scenario_keys) == 2

    # get scenario 1
    problem_s1 = problem.get_scenario_problem("s_1")

    assert len(problem_s1.objectives) == 3
    assert len(problem_s1.constraints) == 3
    assert len(problem_s1.extra_funcs) == 0

    symbols_s1 = problem_s1.get_all_symbols()

    assert "f_1" in symbols_s1
    assert "f_2" in symbols_s1
    assert "f_3" in symbols_s1
    assert "f_4" not in symbols_s1

    assert "con_1" in symbols_s1
    assert "con_2" not in symbols_s1
    assert "con_3" in symbols_s1
    assert "con_4" in symbols_s1

    assert "extra_1" not in symbols_s1

    assert "x_1" in symbols_s1
    assert "x_2" in symbols_s1
    assert "c_1" in symbols_s1

    # get scenario 2
    problem_s2 = problem.get_scenario_problem("s_2")

    assert len(problem_s2.objectives) == 4
    assert len(problem_s2.constraints) == 3
    assert len(problem_s2.extra_funcs) == 1

    symbols_s2 = problem_s2.get_all_symbols()

    assert "f_1" not in symbols_s2
    assert "f_2" in symbols_s2
    assert "f_3" in symbols_s2
    assert "f_4" in symbols_s2

    assert "con_1" not in symbols_s2
    assert "con_2" in symbols_s2
    assert "con_3" in symbols_s2
    assert "con_4" in symbols_s2

    assert "extra_1" in symbols_s2

    assert "x_1" in symbols_s2
    assert "x_2" in symbols_s2
    assert "c_1" in symbols_s2

    # get all scenarios
    problem_all = problem.get_scenario_problem(["s_1", "s_2"])

    assert len(problem_all.objectives) == 5
    assert len(problem_all.constraints) == 4
    assert len(problem_all.extra_funcs) == 1


@pytest.mark.schema
def test_update_ideal_and_nadir():
    """Test that the method update_ideal_and_nadir works correctly."""
    problem = simple_knapsack()

    orig_ideal = problem.get_ideal_point()
    orig_nadir = problem.get_nadir_point()

    new_ideal = {"f_1": -100, "f_2": -25.0, "f_3": 41.0}
    new_nadir = {"f_1": 153.0, "f_2": 255.0, "f_3": 137.0}

    # update just ideal
    problem_w_new_ideal = problem.update_ideal_and_nadir(new_ideal=new_ideal)

    assert problem_w_new_ideal.get_ideal_point() == new_ideal
    assert problem_w_new_ideal.get_nadir_point() == orig_nadir

    # update just nadir
    problem_w_new_nadir = problem.update_ideal_and_nadir(new_nadir=new_nadir)

    assert problem_w_new_nadir.get_nadir_point() == new_nadir
    assert problem_w_new_nadir.get_ideal_point() == orig_ideal

    # update both
    problem_w_new_ideal_and_nadir = problem.update_ideal_and_nadir(new_ideal=new_ideal, new_nadir=new_nadir)

    assert problem_w_new_ideal_and_nadir.get_ideal_point() == new_ideal
    assert problem_w_new_ideal_and_nadir.get_nadir_point() == new_nadir

    # original problem unchanged
    assert problem.get_ideal_point() == orig_ideal
    assert problem.get_nadir_point() == orig_nadir
