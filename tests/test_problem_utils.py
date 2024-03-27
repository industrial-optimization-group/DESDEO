"""Tests various utils found in the desdeo.problem pacakge."""
from desdeo.problem import (
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
    river_pollution_problem,
)


def test_objective_dict_to_numpy_array_and_back():
    """Tests the conceversion from an objective dict to a numpy array."""
    problem = river_pollution_problem()

    objective_dict = {objective.symbol: i for i, objective in enumerate(problem.objectives)}

    objective_array = objective_dict_to_numpy_array(problem, objective_dict)

    objective_dict_again = numpy_array_to_objective_dict(problem, objective_array)

    assert all(
        objective_dict[objective.symbol] == objective_dict_again[objective.symbol] for objective in problem.objectives
    )
