"""Tests various utils found in the desdeo.problem pacakge."""

import numpy.testing as npt
import polars as pl

from desdeo.problem import (
    dtlz2,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
    river_pollution_problem,
    tensor_constant_from_dataframe,
    variable_dict_to_numpy_array,
)


def test_objective_dict_to_numpy_array_and_back():
    """Tests the conversion from an objective dict to a numpy array."""
    problem = river_pollution_problem()

    objective_dict = {objective.symbol: i for i, objective in enumerate(problem.objectives)}

    objective_array = objective_dict_to_numpy_array(problem, objective_dict)

    objective_dict_again = numpy_array_to_objective_dict(problem, objective_array)

    assert all(
        objective_dict[objective.symbol] == objective_dict_again[objective.symbol] for objective in problem.objectives
    )


def test_variable_dict_to_numpy_array():
    """Test the conversion from a variable dict to a numpy array."""
    n_variables = 10
    problem = dtlz2(n_variables, 5)

    var_values = [2.5 * (i + 1) for i in range(n_variables)]

    variable_dict = {f"{variable.symbol}": var_values[i] for (i, variable) in enumerate(problem.variables)}

    numpy_arr = variable_dict_to_numpy_array(problem, variable_dict)

    npt.assert_array_almost_equal(numpy_arr, var_values)


def test_tensor_constant_from_dataframe():
    """Test that a TensorConstant is created properly from a dataframe."""
    df = pl.DataFrame({"A": [1, 2, 3, 4, 5], "B": [10, 20, 30, 40, 50], "C": [100, 200, 300, 400, 500]})

    selected_columns = ["A", "C"]
    n_rows = 3

    tensor = tensor_constant_from_dataframe(df, "test", "T", n_rows, selected_columns)

    assert tensor.name == "test"
    assert tensor.symbol == "T"
    assert tensor.shape == [n_rows, len(selected_columns)]
    assert tensor.get_values() == [df["A"][0:n_rows].to_list(), df["C"][0:n_rows].to_list()]

    selected_columns = ["B", "A"]
    n_rows = 5

    tensor = tensor_constant_from_dataframe(df, "test", "T", n_rows, selected_columns)

    assert tensor.name == "test"
    assert tensor.symbol == "T"
    assert tensor.shape == [n_rows, len(selected_columns)]
    assert tensor.get_values() == [df["B"][0:n_rows].to_list(), df["A"][0:n_rows].to_list()]

    selected_columns = ["A", "B", "C"]
    n_rows = 2

    tensor = tensor_constant_from_dataframe(df, "test", "T", n_rows, selected_columns)

    assert tensor.name == "test"
    assert tensor.symbol == "T"
    assert tensor.shape == [n_rows, len(selected_columns)]
    assert tensor.get_values() == [
        df["A"][0:n_rows].to_list(),
        df["B"][0:n_rows].to_list(),
        df["C"][0:n_rows].to_list(),
    ]

    selected_columns = ["C"]
    n_rows = 3

    tensor = tensor_constant_from_dataframe(df, "test", "T", n_rows, selected_columns)

    assert tensor.name == "test"
    assert tensor.symbol == "T"
    assert tensor.shape == [n_rows, len(selected_columns)]
    assert tensor.get_values() == [
        df["C"][0:n_rows].to_list(),
    ]
