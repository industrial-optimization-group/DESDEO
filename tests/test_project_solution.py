"""Tests for the project_solution.py module."""

from desdeo.problem.testproblems.dtlz_problems import dtlz2
from desdeo.tools.project_solution import project_solution


def test_project_solution():
    """Test the project_solution function with a simple DTLZ2 problem."""
    problem = dtlz2(3, 2)
    objective_vector = {"f_1": 0.5, "f_2": 0.5}
    decision_vector = {"x_1": 0.5, "x_2": 0.5, "x_3": 0.5}
    ideal = {"f_1": 0.0, "f_2": 0.0}
    nadir = {"f_1": 1.0, "f_2": 1.0}
    tolerance = 1e-4

    # Test with decision vector
    is_optimal, results = project_solution(
        problem,
        objective_vector,
        tolerance,
        ideal,
        nadir,
        decision_vector,
    )

    assert is_optimal, "The solution should be optimal."
    assert results.success, "The solver should succeed."
    assert results.optimal_variables == decision_vector, (
        "The optimal variables should match the provided decision vector."
    )

    # Test with no decision vector
    is_optimal, results = project_solution(
        problem,
        objective_vector,
        tolerance,
        ideal,
        nadir,
    )
    assert is_optimal, "The solution should be optimal."
    assert results.success, "The solver should succeed."
    # The optimal values are not guaranteed to match.

    # Test with a non-optimal solution
    non_optimal_objective_vector = {"f_1": 0.8, "f_2": 0.8}
    is_optimal, results = project_solution(
        problem,
        non_optimal_objective_vector,
        tolerance,
        ideal,
        nadir,
    )
    assert not is_optimal, "The solution should not be optimal."
    assert results.scalarization_values["ref_point"] < -tolerance, (
        "The scalarization value should be less than the negative tolerance for a non-optimal solution."
    )
