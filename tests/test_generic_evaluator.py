"""Tests for the generic evaluator."""
import numpy.testing as npt
import polars as pl

from desdeo.problem import GenericEvaluator, river_pollution_problem


def test_generic_with_river():
    problem = river_pollution_problem()

    data = {"x_1": [0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95], "x_2": [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35]}

    df = pl.DataFrame(data)

    evaluator = GenericEvaluator(problem)

    eval_res = evaluator.evaluate(data)

    objective_values = eval_res.objective_values

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

    obj_symbols = [obj.symbol for obj in problem.objectives]

    for symbol in obj_symbols:
        npt.assert_array_almost_equal(
            eval_res.objective_values[symbol], truth_values[symbol], err_msg=f"Failed for objective {symbol}"
        )

    print()
