"""Tests various utils found in the desdeo.problem package."""

import numpy.testing as npt
import polars as pl
import pytest

from desdeo.problem import (
    flatten_variable_dict,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
    tensor_constant_from_dataframe,
    unflatten_variable_array,
)
from desdeo.problem.testproblems import mixed_variable_dimensions_problem, river_pollution_problem


@pytest.mark.utils
def test_objective_dict_to_numpy_array_and_back():
    """Tests the conversion from an objective dict to a numpy array."""
    problem = river_pollution_problem()

    objective_dict = {objective.symbol: i for i, objective in enumerate(problem.objectives)}

    objective_array = objective_dict_to_numpy_array(problem, objective_dict)

    objective_dict_again = numpy_array_to_objective_dict(problem, objective_array)

    assert all(
        objective_dict[objective.symbol] == objective_dict_again[objective.symbol] for objective in problem.objectives
    )


@pytest.mark.utils
def test_flatten_unflatten_variable_dict():
    """Test that variable dictionaries are flattened correctly, and that variable array are unflattened correctly."""
    problem = mixed_variable_dimensions_problem()

    flat_values = [1.0, 1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 7, 7, 7, 7, 1, 4, 9, 4, 7, 8, 9, 7]

    var_dict = {
        "x": 1.0,
        "Y": [1, 2, 3, 4, 5],
        "Z": [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]],
        "A": [[[7, 7], [7, 7], [1, 4]], [[9, 4], [7, 8], [9, 7]]],
    }

    # flatten
    res = flatten_variable_dict(problem, var_dict)
    npt.assert_almost_equal(res, flat_values)

    # unflatten
    res_unflatten = unflatten_variable_array(problem, res)
    assert res_unflatten == var_dict

    var_dict_all_flat = {
        "x": 1.0,
        "Y_1": 1,
        "Y_2": 2,
        "Y_3": 3,
        "Y_4": 4,
        "Y_5": 5,
        "Z_1_1": 1,
        "Z_1_2": 2,
        "Z_2_1": 3,
        "Z_2_2": 4,
        "Z_3_1": 5,
        "Z_3_2": 6,
        "Z_4_1": 7,
        "Z_4_2": 8,
        "Z_5_1": 9,
        "Z_5_2": 10,
        "A_1_1_1": 7,
        "A_1_1_2": 7,
        "A_1_2_1": 7,
        "A_1_2_2": 7,
        "A_1_3_1": 1,
        "A_1_3_2": 4,
        "A_2_1_1": 9,
        "A_2_1_2": 4,
        "A_2_2_1": 7,
        "A_2_2_2": 8,
        "A_2_3_1": 9,
        "A_2_3_2": 7,
    }

    # flatten
    res_flat = flatten_variable_dict(problem, var_dict_all_flat)
    npt.assert_almost_equal(res_flat, flat_values)

    # unflatten
    res_flat_unflatten = unflatten_variable_array(problem, res_flat)
    assert res_flat_unflatten == var_dict

    var_dict_mix = {
        "x": 1.0,
        "Y": [1, 2, 3, 4, 5],
        "Z_1_1": 1,
        "Z_1_2": 2,
        "Z_2_1": 3,
        "Z_2_2": 4,
        "Z_3_1": 5,
        "Z_3_2": 6,
        "Z_4_1": 7,
        "Z_4_2": 8,
        "Z_5_1": 9,
        "Z_5_2": 10,
        "A": [[[7, 7], [7, 7], [1, 4]], [[9, 4], [7, 8], [9, 7]]],
    }

    # flatten
    res_mix = flatten_variable_dict(problem, var_dict_mix)
    npt.assert_almost_equal(res_mix, flat_values)

    # unflatten
    res_mix_unflatten = unflatten_variable_array(problem, res_mix)
    assert res_mix_unflatten == var_dict


@pytest.mark.utils
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
