"""Tests related to the Synchronous NIMBUS method."""

from desdeo.mcdm import solve_intermediate_solutions
from desdeo.problem import dtlz2, nimbus_test_problem


def test_solve_intermediate_solutions():
    """Tests that intermediate solutions are generated as expected."""
    # x_3 and x_4 must be 0.5
    problem = dtlz2(4, 2)
    solution_1 = {"x_1": 0.0, "x_2": 1.0, "x_3": 0.5, "x_4": 0.5}
    solution_2 = {"x_1": 1.0, "x_2": 0.0, "x_3": 0.5, "x_4": 0.5}

    results = solve_intermediate_solutions(problem, solution_1, solution_2, 5)
