"""Tests various utils found in the desdeo.problem pacakge."""

import numpy.testing as npt

from desdeo.problem import (
    dtlz2,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
    river_pollution_problem,
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
