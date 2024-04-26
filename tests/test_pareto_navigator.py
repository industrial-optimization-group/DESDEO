"""Tests related to Pareto Navigator."""

import numpy as np
import pytest

from desdeo.mcdm.pareto_navigator import (
    calculate_adjusted_speed,
    calculate_all_solutions,
    calculate_next_solution,
    calculate_search_direction,
    construct_matrix_a,
    get_polyhedral_set
)
from desdeo.problem import (
    pareto_navigator_test_problem,
    objective_dict_to_numpy_array
)


@pytest.mark.pareto_navigator
def test_pareto_navigator_reference_point():
    """Tests Pareto Navigator with preference information given as a reference point."""
    problem = pareto_navigator_test_problem()
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()
    speed = 1
    allowed_speeds = np.array([1, 2, 3, 4, 5])
    adjusted_speed = calculate_adjusted_speed(allowed_speeds, speed)

    assert adjusted_speed == 0.01

    starting_point = {"f_1": 1.38, "f_2": 0.62, "f_3": -35.33}

    preference_info = {
        "reference_point": {"f_1": ideal["f_1"], "f_2": ideal["f_2"], "f_3": nadir["f_3"]}
    }

    num_solutions = 200
    acc = 0.15
    solutions = calculate_all_solutions(problem, starting_point, adjusted_speed, num_solutions, preference_info)
    navigated_point = starting_point

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([0.35, -0.51, -26.26])) < acc):
            navigated_point = solutions[i]
            break

    preference_info = {
        "reference_point": {"f_1": ideal["f_1"], "f_2": nadir["f_2"], "f_3": navigated_point["f_3"]}
    }

    solutions = calculate_all_solutions(problem, navigated_point, adjusted_speed, num_solutions, preference_info)

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([-0.89, 2.91, -24.98])) < acc):
            navigated_point = solutions[i]
            break

    preference_info = {
        "reference_point": {"f_1": nadir["f_1"], "f_2": ideal["f_2"], "f_3": ideal["f_3"]}
    }
    solutions = calculate_all_solutions(problem, navigated_point, adjusted_speed, num_solutions, preference_info)

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([-0.32, 2.33, -27.85])) < acc):
            navigated_point = solutions[i]
            break


@pytest.mark.pareto_navigator
def test_pareto_navigator_classification():
    """Tests Pareto Navigator with preference information given as classification."""
    problem = pareto_navigator_test_problem()
    speed = 1
    allowed_speeds = np.array([1, 2, 3, 4, 5])
    adjusted_speed = calculate_adjusted_speed(allowed_speeds, speed)

    assert adjusted_speed == 0.01

    starting_point = {"f_1": 1.38, "f_2": 0.62, "f_3": -35.33}

    preference_info = {
        "classification": {"f_1": "<", "f_2": "<", "f_3": ">"}
    }

    num_solutions = 200
    acc = 0.15
    solutions = calculate_all_solutions(problem, starting_point, adjusted_speed, num_solutions, preference_info)
    navigated_point = starting_point

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([0.35, -0.51, -26.26])) < acc):
            navigated_point = solutions[i]
            break

    preference_info = {
        "classification": {"f_1": "<", "f_2": ">", "f_3": "="}
    }

    solutions = calculate_all_solutions(problem, navigated_point, adjusted_speed, num_solutions, preference_info)

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([-0.89, 2.91, -24.98])) < acc):
            navigated_point = solutions[i]
            break

    preference_info = {
        "classification": {"f_1": ">", "f_2": "<", "f_3": "<"}
    }
    solutions = calculate_all_solutions(problem, navigated_point, adjusted_speed, num_solutions, preference_info)

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([-0.32, 2.33, -27.85])) < acc):
            navigated_point = solutions[i]
            break


@pytest.mark.pareto_navigator
def test_calculate_next_solution():
    """Test calculating next solution."""
    problem = pareto_navigator_test_problem()
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()
    speed = 1
    allowed_speeds = np.array([1, 2, 3, 4, 5])
    adjusted_speed = calculate_adjusted_speed(allowed_speeds, speed)

    matrix_a, b = get_polyhedral_set(problem)
    matrix_a_new = construct_matrix_a(problem, matrix_a)

    assert adjusted_speed == 0.01

    starting_point = {"f_1": 1.38, "f_2": 0.62, "f_3": -35.33}
    preference_info = {
        "reference_point": {"f_1": ideal["f_1"], "f_2": ideal["f_2"], "f_3": nadir["f_3"]}
    }

    d = calculate_search_direction(problem, preference_info["reference_point"], starting_point)

    next_solution = calculate_next_solution(problem, d, starting_point, adjusted_speed, matrix_a_new, b)

    assert starting_point["f_1"] > next_solution["f_1"]
    assert starting_point["f_2"] > next_solution["f_2"]
    assert starting_point["f_3"] < next_solution["f_3"]
