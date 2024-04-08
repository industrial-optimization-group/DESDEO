"""Tests related to the Synchronous NIMBUS method."""

from desdeo.mcdm import solve_intermediate_solutions
from desdeo.problem import nimbus_test_problem


def test_solve_intermediate_solutions():
    """Tests that intermediate solutions are generated as expected."""
    problem = nimbus_test_problem()
    solution_1 = {"x_1": 1.5, "x_2": 2.5}
    solution_2 = {"x_1": 2.0, "x_2": 1.0}

    solve_intermediate_solutions(problem, solution_1, solution_2, 5)
