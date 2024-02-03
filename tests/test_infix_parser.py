"""Tests the infix parser for parsing mathematical expressions in infix format."""
import numpy as np
import numpy.testing as npt
import polars as pl

from desdeo.problem.evaluator import GenericEvaluator
from desdeo.problem.infix_parser import InfixExpressionParser
from desdeo.problem.json_parser import MathParser
from desdeo.problem.schema import Constant, Constraint, Objective, Problem, Variable
from desdeo.problem.testproblems import binh_and_korn


def test_basic_binary_to_json():
    """Test the basic operations and that they convert to JSON correctly."""
    parser = InfixExpressionParser()

    # binary operations
    # Adding
    input_add_1 = "f_1 + 8 + 9.2 + x_55 + (9 + 2)"
    output_add_1 = ["Add", "f_1", 8, 9.2, "x_55", ["Add", 9, 2]]
    input_add_2 = "3 + y_2 + (5.5 + 7 + z_3)"
    output_add_2 = ["Add", 3, "y_2", ["Add", 5.5, 7, "z_3"]]
    assert parser.parse(input_add_1) == output_add_1
    assert parser.parse(input_add_2) == output_add_2

    # Subtracting
    input_subtract_1 = "f_1 - 3 - 2.5 - x_20 - (7 - 3)"
    output_subtract_1 = [
        "Add",
        "f_1",
        ["Negate", 3],
        ["Negate", 2.5],
        ["Negate", "x_20"],
        ["Negate", ["Add", 7, ["Negate", 3]]],
    ]
    input_subtract_2 = "10 - (x_10 - 3.5) - y_4"
    output_subtract_2 = ["Add", 10, ["Negate", ["Add", "x_10", ["Negate", 3.5]]], ["Negate", "y_4"]]
    assert parser.parse(input_subtract_1) == output_subtract_1
    assert parser.parse(input_subtract_2) == output_subtract_2

    # Multiplying
    input_multiply_1 = "f_2 * 4 * 3.3 * x_10 * (5 * 2)"
    output_multiply_1 = ["Multiply", "f_2", 4, 3.3, "x_10", ["Multiply", 5, 2]]
    input_multiply_2 = "7 * (x_7 * 2.2) * y_5"
    output_multiply_2 = ["Multiply", 7, ["Multiply", "x_7", 2.2], "y_5"]
    assert parser.parse(input_multiply_1) == output_multiply_1
    assert parser.parse(input_multiply_2) == output_multiply_2

    # Dividing
    input_divide_1 = "f_3 / 6 / 1.2 / x_15 / (8 / 2)"
    output_divide_1 = ["Divide", "f_3", 6, 1.2, "x_15", ["Divide", 8, 2]]
    input_divide_2 = "(10 / x_30) / 4.5 / y_6"
    output_divide_2 = ["Divide", ["Divide", 10, "x_30"], 4.5, "y_6"]
    assert parser.parse(input_divide_1) == output_divide_1
    assert parser.parse(input_divide_2) == output_divide_2

    # Power
    input_power_1 = "f_4 ** 2 ** 1.5 ** x_25 ** (3 ** 4)"
    output_power_1 = ["Power", "f_4", 2, 1.5, "x_25", ["Power", 3, 4]]
    input_power_2 = "5 ** (x_5 ** 2.0) ** y_7"
    output_power_2 = ["Power", 5, ["Power", "x_5", 2.0], "y_7"]
    assert parser.parse(input_power_1) == output_power_1
    assert parser.parse(input_power_2) == output_power_2

    # Negation
    input_negate_1 = "-1"
    output_negate_1 = ["Negate", 1]
    input_negate_2 = "-x_25"
    output_negate_2 = ["Negate", "x_25"]
    input_negate_3 = "-3.5"
    output_negate_3 = ["Negate", 3.5]
    input_negate_4 = "-(4 + y_3)"
    output_negate_4 = ["Negate", ["Add", 4, "y_3"]]

    assert parser.parse(input_negate_1) == output_negate_1
    assert parser.parse(input_negate_2) == output_negate_2
    assert parser.parse(input_negate_3) == output_negate_3
    assert parser.parse(input_negate_4) == output_negate_4


def test_basic_unary_to_json():
    """Tests the correct parsing of unary operations to JSON."""
    parser = InfixExpressionParser()

    # Test cases for each unary operator
    unary_operators = [
        "Cos",
        "Sin",
        "Tan",
        "Exp",
        "Ln",
        "Lb",
        "Lg",
        "LogOnePlus",
        "Sqrt",
        "Square",
        "Abs",
        "Ceil",
        "Floor",
        "Arccos",
        "Arccosh",
        "Arcsin",
        "Arcsinh",
        "Arctan",
        "Arctanh",
        "Cosh",
        "Sinh",
        "Tanh",
        "Rational",
    ]

    for op in unary_operators:
        input_expr = f"{op}(x)"
        output_expr = [op, "x"]
        assert parser.parse(input_expr) == output_expr

        # Combining with binary operation and negation
        combined_input = f"{op}(-x + 3)"
        combined_output = [op, ["Add", ["Negate", "x"], 3]]
        assert parser.parse(combined_input) == combined_output

        # More complex expression
        complex_input = f"{op}(2 * x_20 / (3 + y))"
        complex_output = [op, ["Multiply", 2, ["Divide", "x_20", ["Add", 3, "y"]]]]
        assert parser.parse(complex_input) == complex_output


def test_basic_variadic_to_json():
    """Test the correct parsing of variadic functions."""
    parser = InfixExpressionParser()

    # Test case with a single argument
    input_max_1 = "Max(1)"
    output_max_1 = ["Max", 1]
    assert parser.parse(input_max_1) == output_max_1

    # Test case with multiple arguments
    input_max_2 = "Max(1, 2, 3)"
    output_max_2 = ["Max", [1, 2, 3]]
    assert parser.parse(input_max_2) == output_max_2

    # Test case with nested 'Max' function
    input_max_3 = "Max(1, Max(2, 3))"
    output_max_3 = ["Max", [1, ["Max", [2, 3]]]]
    assert parser.parse(input_max_3) == output_max_3

    # Test case with more complex nested structure
    input_max_4 = "Max(x, y, Max(2, z), Max(5, Max(6, 7)))"
    output_max_4 = ["Max", ["x", "y", ["Max", [2, "z"]], ["Max", [5, ["Max", [6, 7]]]]]]
    assert parser.parse(input_max_4) == output_max_4

    # Test case combining 'Max' with other operations
    input_max_5 = "Max(x + 1, 3 * y, Max(2 / z, 4 - w))"
    output_max_5 = [
        "Max",
        [["Add", "x", 1], ["Multiply", 3, "y"], ["Max", [["Divide", 2, "z"], ["Add", 4, ["Negate", "w"]]]]],
    ]
    assert parser.parse(input_max_5) == output_max_5


def test_mixed_operations_to_json():
    """Test mixed operations including binary, unary, negation, and variadic functions."""
    parser = InfixExpressionParser()

    # Mixed test cases
    # Combination of unary, binary, and negation
    input_mixed_1 = "Sin(x_1 + 3) ** 2 - Max(4, Cos(y_2 - 5))"
    output_mixed_1 = [
        "Add",
        ["Power", ["Sin", ["Add", "x_1", 3]], 2],
        ["Negate", ["Max", [4, ["Cos", ["Add", "y_2", ["Negate", 5]]]]]],
    ]
    assert parser.parse(input_mixed_1) == output_mixed_1

    # Complex nested structure with variadic function
    input_mixed_2 = "Max(Sqrt(x_3 ** 2), Abs(-y_4) / 2, Ln(Exp(z_5)))"
    output_mixed_2 = [
        "Max",
        [["Sqrt", ["Power", "x_3", 2]], ["Divide", ["Abs", ["Negate", "y_4"]], 2], ["Ln", ["Exp", "z_5"]]],
    ]
    assert parser.parse(input_mixed_2) == output_mixed_2

    # Combination of unary, binary, negation, and variadic function
    input_mixed_3 = "Arccos(-1 / Max(Sin(2), 3))"
    output_mixed_3 = ["Arccos", ["Divide", ["Negate", 1], ["Max", [["Sin", 2], 3]]]]
    assert parser.parse(input_mixed_3) == output_mixed_3

    # Very complex and nested expression
    input_mixed_4 = "Ceil((x + 3) * Sin(Max(y, Tan(-2 * z)))) - Floor(Exp(Ln(5 / w)))"
    output_mixed_4 = [
        "Add",
        ["Ceil", ["Multiply", ["Add", "x", 3], ["Sin", ["Max", ["y", ["Tan", ["Multiply", ["Negate", 2], "z"]]]]]]],
        ["Negate", ["Floor", ["Exp", ["Ln", ["Divide", 5, "w"]]]]],
    ]
    assert parser.parse(input_mixed_4) == output_mixed_4

    # Another creative expression combining multiple operations
    input_mixed_5 = "2 ** Lg(Abs(-Max(f_6, 4.5))) * Sqrt(Square(x_7) + 9)"
    output_mixed_5 = [
        "Multiply",
        ["Power", 2, ["Lg", ["Abs", ["Negate", ["Max", ["f_6", 4.5]]]]]],
        ["Sqrt", ["Add", ["Square", "x_7"], 9]],
    ]
    assert parser.parse(input_mixed_5) == output_mixed_5


def test_infix_binh_and_korn_to_json():
    """Tests whether the Binh and Korn problem evaluates correctly from infix notation."""
    parser = InfixExpressionParser()

    # Infix expressions
    infix_obj_1 = "c_1 * (x_1 ** 2) + c_1 * (x_2 ** 2)"
    infix_obj_2 = "(x_1 - c_2) ** 2 + (x_2 - c_2) ** 2"
    infix_cons_1 = "(x_1 - c_2) ** 2 + x_2 ** 2 - 25"
    infix_cons_2 = "-(x_1 - 8) ** 2 - (x_2 + 3) ** 2 + 7.7"
    # -(x_1 - 8) ** 2 - (x_2 + 3) ** 2 + 7.7
    # ["Add", ["Negate", ["Square", ["Subtract", "x_1", 8]]], ["Negate", ["Square", ["Add", "x_2", 3]]], 7.7]

    # Parsing expressions
    parsed_obj_1 = parser.parse(infix_obj_1)
    assert parsed_obj_1 == ["Add", ["Multiply", "c_1", ["Power", "x_1", 2]], ["Multiply", "c_1", ["Power", "x_2", 2]]]

    parsed_obj_2 = parser.parse(infix_obj_2)
    assert parsed_obj_2 == [
        "Add",
        ["Power", ["Add", "x_1", ["Negate", "c_2"]], 2],
        ["Power", ["Add", "x_2", ["Negate", "c_2"]], 2],
    ]

    parsed_cons_1 = parser.parse(infix_cons_1)
    assert parsed_cons_1 == [
        "Add",
        ["Power", ["Add", "x_1", ["Negate", "c_2"]], 2],
        ["Add", ["Power", "x_2", 2], ["Negate", 25]],
    ]

    parsed_cons_2 = parser.parse(infix_cons_2)
    assert parsed_cons_2 == [
        "Add",
        ["Negate", ["Power", ["Add", "x_1", ["Negate", 8]], 2]],
        ["Negate", ["Power", ["Add", "x_2", 3], 2]],
        7.7,
    ]

    constant_1 = Constant(name="Four", symbol="c_1", value=4)
    constant_2 = Constant(name="Five", symbol="c_2", value=5)

    variable_1 = Variable(
        name="The first variable", symbol="x_1", variable_type="real", lowerbound=0, upperbound=5, initial_value=2.5
    )
    variable_2 = Variable(
        name="The second variable", symbol="x_2", variable_type="real", lowerbound=0, upperbound=3, initial_value=1.5
    )

    objective_1 = Objective(
        name="Objective 1",
        symbol="f_1",
        func=parsed_obj_1,
        maximize=False,
        ideal=None,
        nadir=None,
    )
    objective_2 = Objective(
        name="Objective 2",
        symbol="f_2",
        func=parsed_obj_2,
        maximize=False,
    )

    constraint_1 = Constraint(name="Constraint 1", symbol="g_1", cons_type="<=", func=parsed_cons_1)

    constraint_2 = Constraint(name="Constraint 2", symbol="g_2", cons_type="<=", func=parsed_cons_2)

    infix_problem = Problem(
        name="The Binh and Korn function",
        description="The two-objective problem used in the paper by Binh and Korn.",
        constants=[constant_1, constant_2],
        variables=[variable_1, variable_2],
        objectives=[objective_1, objective_2],
        constraints=[constraint_1, constraint_2],
    )

    truth_problem = binh_and_korn()

    infix_evaluator = GenericEvaluator(infix_problem, "polars")
    truth_evaluator = GenericEvaluator(truth_problem, "polars")

    # some test data to evaluate the expressions
    xs_dict = {"x_1": [1, 2.5, 4.2], "x_2": [0.5, 1.5, 2.5]}

    infix_result = infix_evaluator.evaluate(xs_dict)
    truth_result = truth_evaluator.evaluate(xs_dict)

    npt.assert_array_almost_equal(infix_result.objective_values["f_1"], truth_result.objective_values["f_1"])
    npt.assert_array_almost_equal(infix_result.objective_values["f_2"], truth_result.objective_values["f_2"])
    npt.assert_array_almost_equal(infix_result.constraint_values["g_1"], truth_result.constraint_values["g_1"])
    npt.assert_array_almost_equal(infix_result.constraint_values["g_2"], truth_result.constraint_values["g_2"])


def evaluate_expression_helper(infix_expression, data):
    """Evaluate an infix expression using the given data and return the result."""
    infix_parser = InfixExpressionParser(target="MathJSON")
    math_parser = MathParser()

    parsed_expression = infix_parser.parse(infix_expression)
    expr = math_parser.parse(parsed_expression)
    return data.select(expr.alias("result"))["result"][0]


def test_infix_evaluated_basics():
    """Tests the infix parser for basic arithmetic operations by checking the evaluated result's correctness."""
    data = pl.DataFrame({"x_1": [5.2], "x_2": [-4.2], "bignumber": [10], "smallnum": [0.5]})

    # Retrieve values from the DataFrame for computation
    x_1 = data["x_1"][0]
    x_2 = data["x_2"][0]
    bignumber = data["bignumber"][0]
    smallnum = data["smallnum"][0]

    # Test cases (infix expression, numpy computation for expected result)
    tests = [
        ("1+2+x_1+bignumber", 1 + 2 + x_1 + bignumber),
        ("1+2-x_1+bignumber-x_2", 1 + 2 - x_1 + bignumber - x_2),
        ("x_1 - x_2 + bignumber - smallnum", x_1 - x_2 + bignumber - smallnum),
        ("x_1 * smallnum * bignumber", x_1 * smallnum * bignumber),
        ("bignumber / smallnum / x_1", bignumber / smallnum / x_1),
        ("smallnum ** x_1", smallnum**x_1),
        ("(x_1 + bignumber) * smallnum - x_2 / smallnum", (x_1 + bignumber) * smallnum - x_2 / smallnum),
        ("bignumber * (smallnum + x_1) - x_2 ** 2", bignumber * (smallnum + x_1) - x_2**2),
        ("x_1 + x_2", x_1 + x_2),
        ("bignumber - smallnum", bignumber - smallnum),
        ("((x_1 + 2) * (x_2 - 2)) / smallnum", ((x_1 + 2) * (x_2 - 2)) / smallnum),
        ("(bignumber ** 2 - smallnum) / (x_1 + 1)", (bignumber**2 - smallnum) / (x_1 + 1)),
        ("x_1 * (x_2 / (smallnum + bignumber))", x_1 * (x_2 / (smallnum + bignumber))),
        ("(x_1 - x_2) * (bignumber + smallnum)", (x_1 - x_2) * (bignumber + smallnum)),
        ("((x_1 ** 2) + (bignumber * smallnum) - x_2)", ((x_1**2) + (bignumber * smallnum) - x_2)),
        ("(x_1 + bignumber) * (x_2 - smallnum) / x_1", (x_1 + bignumber) * (x_2 - smallnum) / x_1),
        ("1+2+3", 1 + 2 + 3),
        ("1+2-3*5/2", 1 + 2 - 3 * 5 / 2),
    ]

    for infix_expression, expected in tests:
        result = evaluate_expression_helper(infix_expression, data)
        npt.assert_almost_equal(result, expected, decimal=5, err_msg=f"Failed for expression: {infix_expression}")


def test_unary_operators_with_nested_expressions_evaluation():
    """Test parsing and evaluation of complex expressions with unary operators and mixed arithmetic."""
    data = pl.DataFrame(
        {
            "x": [5.5],
            "y": [2.0],
            "z": [-1.0],
        }
    )
    x = data["x"][0]
    y = data["y"][0]
    z = data["z"][0]

    # Test cases (infix expression, expected result)
    tests = [
        ("Sin(x + y)", np.sin(x + y)),
        ("Exp(x) * Cos(y - x)", np.exp(x) * np.cos(y - x)),
        ("Lb(x)", np.log2(x)),
        ("Lg(x)", np.log10(x)),
        ("LogOnePlus(x)", np.log1p(x)),
        ("Sqrt(x)", np.sqrt(x)),
        ("Square(x)", np.square(x)),
        ("Abs(z)", np.abs(z)),
        ("Ceil(x)", np.ceil(x)),
        ("Floor(x)", np.floor(x)),
        ("Arccos(Cos(y))", np.arccos(np.cos(y))),
        ("Arccosh(Cosh(x))", np.arccosh(np.cosh(x))),
        ("Arcsin(Sin(y))", np.arcsin(np.sin(y))),
        ("Arcsinh(Sinh(x))", np.arcsinh(np.sinh(x))),
        ("Arctan(Tan(y))", np.arctan(np.tan(y))),
        ("Arctanh(Tanh(x))", np.arctanh(np.tanh(x))),
        ("Cosh(x)", np.cosh(x)),
        ("Sinh(x)", np.sinh(x)),
        ("Tanh(x)", np.tanh(x)),
        ("Exp(Ln(x)) + Sqrt(Square(y))", np.exp(np.log(x)) + np.sqrt(np.square(y))),
        ("Ceil(Sin(x)) + Floor(Cos(y))", np.ceil(np.sin(x)) + np.floor(np.cos(y))),
        ("Abs(z) * Tanh(x)", np.abs(z) * np.tanh(x)),
        ("Square(2)", np.square(2)),
    ]

    for infix_expression, expected in tests:
        result = evaluate_expression_helper(infix_expression, data)
        npt.assert_almost_equal(result, expected, decimal=5, err_msg=f"Failed for expression: {infix_expression}")


def test_variadic_max_evaluation():
    """Test parsing and evaluation of expressions with the variadic 'Max' operator."""
    data = pl.DataFrame(
        {
            "a": [1],
            "b": [2],
            "c": [3],
            "d": [4],
        }
    )
    a = data["a"][0]
    b = data["b"][0]
    c = data["c"][0]
    d = data["d"][0]

    # Test cases (infix expression, expected result)
    tests = [
        ("Max(a)", np.max([a])),
        ("Max(a, b)", np.max([a, b])),
        ("Max(a, b, c)", np.max([a, b, c])),
        ("Max(a, b, c, d)", np.max([a, b, c, d])),
        ("Max(a + b, c)", np.max([a + b, c])),
        ("Max(a, b * c)", np.max([a, b * c])),
        ("Max((a + b), (c * d), (d - a))", np.max([a + b, c * d, d - a])),
        ("Max(a, Max(b, c))", np.max([a, np.max([b, c])])),
        ("Max(Max(a, b), Max(c, d))", np.max([np.max([a, b]), np.max([c, d])])),
        ("Max(a + b, c - d, d / a, b * d)", np.max([a + b, c - d, d / a, b * d])),
        ("Max(1,2,3)", np.max([1, 2, 3])),
        ("Max(a + 3, b - 8, a*c, Sin(d))", np.max([a + 3, b - 8, a * c, np.sin(d)])),
        ("Max(-1)", -1),
    ]

    for infix_expression, expected in tests:
        result = evaluate_expression_helper(infix_expression, data)
        npt.assert_almost_equal(result, expected, decimal=5, err_msg=f"Failed for expression: {infix_expression}")
