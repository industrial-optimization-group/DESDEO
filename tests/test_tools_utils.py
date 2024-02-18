"""Tests the utils in the desdeo.tools package."""
from desdeo.problem import river_pollution_problem, simple_data_problem
from desdeo.tools.utils import guess_best_solver, available_solvers


def test_guess_best_solver():
    """Test that the best solver guesser guesses as expected for different problem types."""
    analytical_problem = river_pollution_problem()
    data_problem = simple_data_problem()

    analytical_guess = guess_best_solver(analytical_problem)

    assert analytical_guess is available_solvers["scipy_de"]

    data_guess = guess_best_solver(data_problem)

    assert data_guess is available_solvers["proximal"]
