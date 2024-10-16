"""Tests the utils in the desdeo.tools package."""

from fixtures import dtlz2_5x_3f_data_based  # noqa: F401

from desdeo.problem import re21, river_pollution_problem
from desdeo.tools.utils import available_solvers, find_compatible_solvers, guess_best_solver


def test_guess_best_solver(dtlz2_5x_3f_data_based):  # noqa: F811
    """Test that the best solver guesser guesses as expected for different problem types."""
    analytical_problem = river_pollution_problem()
    data_problem = dtlz2_5x_3f_data_based

    analytical_guess = guess_best_solver(analytical_problem)

    assert analytical_guess is available_solvers["nevergrad"]

    data_guess = guess_best_solver(data_problem)

    assert data_guess is available_solvers["proximal"]


def test_find_compatible_solvers():
    """Test that find_compatible_solvers works as intended."""
    problem = re21()

    solvers = find_compatible_solvers(problem)

    correct_solvers = [
        available_solvers["pyomo_ipopt"],
        available_solvers["nevergrad"],
        available_solvers["scipy_minimize"],
        available_solvers["scipy_de"]
    ]

    # check that the solvers found are the correct ones
    assert len(solvers) == 4
    assert all(solver in correct_solvers for solver in solvers) and all(solver in solvers for solver in correct_solvers)
