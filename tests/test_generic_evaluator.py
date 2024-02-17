"""Tests for the generic evaluator."""
import numpy.testing as npt
import polars as pl

from desdeo.problem import GenericEvaluator, river_pollution_problem, simple_test_problem
from desdeo.problem.evaluator import find_closest_points


def test_generic_with_river():
    """Tests the generic evaluator with the river pollution problem."""
    problem = river_pollution_problem()

    data = {"x_1": [0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95], "x_2": [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35]}

    df = pl.DataFrame(data)

    evaluator = GenericEvaluator(problem)

    eval_res = evaluator.evaluate(data)

    obj_symbols = [obj.symbol for obj in problem.objectives]

    objective_values = eval_res[obj_symbols].to_dict(as_series=False)

    # f_1 = "-4.07 - 2.27 * x_1"
    # f_2 = "-2.60 - 0.03 * x_1 - 0.02 * x_2 - 0.01 / (1.39 - x_1**2) - 0.30 / (1.39 - x_2**2)"
    # f_3 = "-8.21 + 0.71 / (1.09 - x_1**2)"
    # f_4 = "-0.96 + 0.96 / (1.09 - x_2**2)"
    # f_5 = "Max(Abs(x_1 - 0.65), Abs(x_2 - 0.65))"

    truth_values = df.select(
        (-4.07 - 2.27 * pl.col("x_1")).alias("f_1"),
        (
            -2.60
            - 0.03 * pl.col("x_1")
            - 0.02 * pl.col("x_2")
            - 0.01 / (1.39 - pl.col("x_1") ** 2)
            - 0.30 / (1.39 - pl.col("x_2") ** 2)
        ).alias("f_2"),
        (-8.21 + 0.71 / (1.09 - pl.col("x_1") ** 2)).alias("f_3"),
        (-0.96 + 0.96 / (1.09 - pl.col("x_2") ** 2)).alias("f_4"),
        (pl.max_horizontal(pl.Expr.abs(pl.col("x_1") - 0.65), pl.Expr.abs(pl.col("x_2") - 0.65))).alias("f_5"),
    )

    for symbol in obj_symbols:
        npt.assert_array_almost_equal(
            objective_values[symbol], truth_values[symbol], err_msg=f"Failed for objective {symbol}"
        )


def test_generic_w_mins_and_max():
    """Tests the generic evaluator with problems with both min and max objectives."""
    problem = simple_test_problem()

    data = {"x_1": [1, 2, 3, 4, 5, 6, 7, 8, 9], "x_2": [9, 8, 7, 6, 5, 4, 3, 2, 1]}

    df = pl.DataFrame(data)

    evaluator = GenericEvaluator(problem)

    eval_res = evaluator.evaluate(data)

    obj_symbols = [obj.symbol for obj in problem.objectives]

    objective_values = eval_res[obj_symbols].to_dict(as_series=False)

    truth_values = df.select(
        (pl.col("x_1") + pl.col("x_2")).alias("f_1"),
        (pl.col("x_2") ** 3).alias("f_2"),
        (pl.col("x_1") + pl.col("x_2")).alias("f_3"),
        (pl.max_horizontal(pl.Expr.abs(pl.col("x_1") - pl.col("x_2")), 4.2)).alias("f_4"),
        (-pl.col("x_1") * -pl.col("x_2")).alias("f_5"),
    )

    for symbol in obj_symbols:
        npt.assert_array_almost_equal(
            objective_values[symbol], truth_values[symbol], err_msg=f"Failed for objective {symbol}"
        )


def test_find_closest_points():
    """Test the 'find_closest_points' function."""
    # simple data
    xs_basic = pl.DataFrame({"x_1": [3.1, 2.5, 1.05], "x_2": [4.35, -2.1, -0.9]})
    discrete_df_basic = pl.DataFrame({"x_1": [1.1, 2.6, 3.2], "x_2": [-1.1, -2.2, 4.2], "f_2": [42, 69, 420]})
    variable_symbols_basic = ["x_1", "x_2"]
    objective_symbol_basic = "f_2"
    expected_basic = [420, 69, 42]

    closest_points_df_basic = find_closest_points(
        xs_basic, discrete_df_basic, variable_symbols_basic, objective_symbol_basic
    )
    npt.assert_array_almost_equal(closest_points_df_basic[objective_symbol_basic].to_numpy(), expected_basic)

    # more complex data
    xs_complex = pl.DataFrame({"x_1": [0, 2.5, 3.5, -1.5], "x_2": [-1, 2, -2, 0], "x_3": [1.5, -0.5, 2.5, -3]})
    discrete_df_complex = pl.DataFrame(
        {
            "x_1": [0.5, 2, 3, -2, 1],
            "x_2": [-0.5, 2.5, -1.5, 0.5, -1],
            "x_3": [1, -1, 3, -2.5, 2],
            "f_2": [100, 200, 300, 400, 500],
        }
    )
    variable_symbols_complex = ["x_1", "x_2", "x_3"]
    objective_symbol_complex = "f_2"
    # Define expected values for the complex test based on your function's logic
    expected_complex = [100, 200, 300, 400]  # These should be updated according to actual expected results

    closest_points_df_complex = find_closest_points(
        xs_complex, discrete_df_complex, variable_symbols_complex, objective_symbol_complex
    )
    npt.assert_array_almost_equal(closest_points_df_complex[objective_symbol_complex].to_numpy(), expected_complex)

    # just one variable
    xs_single_var = pl.DataFrame({"x_1": [3.5, 2.5, -1.5, 0.1]})
    discrete_df_single_var = pl.DataFrame({"x_1": [0, 2, -2, 0.5], "f_2": [10, 20, 30, 40]})
    variable_symbols_single_var = ["x_1"]  # Only one variable symbol
    objective_symbol_single_var = "f_2"
    # Expected values should match the closest 'f_2' values in 'discrete_df_single_var' based on 'x_1' distances
    expected_single_var = [20, 20, 30, 10]  # Update these expected values based on your function's logic

    closest_points_df_single_var = find_closest_points(
        xs_single_var, discrete_df_single_var, variable_symbols_single_var, objective_symbol_single_var
    )
    npt.assert_array_almost_equal(
        closest_points_df_single_var[objective_symbol_single_var].to_numpy(), expected_single_var
    )
