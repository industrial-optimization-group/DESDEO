"""Tests the utils in the desdeo.tools package."""

import shutil

import pytest
from fixtures import dtlz2_5x_3f_data_based  # noqa: F401

from desdeo.problem import Objective, Problem, Variable, VariableTypeEnum
from desdeo.problem.testproblems import (
    dtlz2,
    re21,
    river_pollution_problem,
    simple_constrained_quadratic_tensor_test_problem,
)
from desdeo.tools import NevergradGenericSolver, PyomoIpoptSolver, ScipyDeSolver, ScipyMinimizeSolver
from desdeo.tools.utils import (
    available_solvers,
    find_compatible_solvers,
    guess_best_solver,
    is_heuristic_solver,
    payoff_table_method,
)


@pytest.mark.utils
def test_guess_best_solver(dtlz2_5x_3f_data_based):  # noqa: F811
    """Test that the best solver guesser guesses as expected for different problem types."""
    analytical_problem = river_pollution_problem()
    data_problem = dtlz2_5x_3f_data_based

    analytical_guess = guess_best_solver(analytical_problem)

    assert analytical_guess is available_solvers["nevergrad"]["constructor"]

    data_guess = guess_best_solver(data_problem)

    assert data_guess is available_solvers["proximal"]["constructor"]


@pytest.mark.utils
def test_find_compatible_solvers():
    """Test that find_compatible_solvers works as intended."""
    problem = re21()

    solvers = find_compatible_solvers(problem)

    correct_solvers = [
        available_solvers["pyomo_ipopt"]["constructor"],
        available_solvers["nevergrad"]["constructor"],
        available_solvers["scipy_minimize"]["constructor"],
        available_solvers["scipy_de"]["constructor"],
    ]

    # check that the solvers found are the correct ones
    if shutil.which("ipopt"):
        assert len(solvers) == 4
        assert all(solver in correct_solvers for solver in solvers) and all(
            solver in solvers for solver in correct_solvers
        )
    else:
        assert len(solvers) == 3

    problem = simple_constrained_quadratic_tensor_test_problem(dqp=True)

    solvers = find_compatible_solvers(problem)

    correct_solvers = [
        available_solvers["pyomo_ipopt"]["constructor"],
        available_solvers["cvxpy"]["constructor"],
    ]

    # check that the solvers found are the correct ones
    if shutil.which("ipopt"):
        assert len(solvers) == 2
        assert all(solver in correct_solvers for solver in solvers) and all(
            solver in solvers for solver in correct_solvers
        )
    else:
        assert len(solvers) == 1


@pytest.mark.utils
def test_payoff_dtlz2():
    """Tests the payoff-table method with the dtlz2 problem."""
    problem = dtlz2(6, 4)

    ideal, nadir = payoff_table_method(problem)  # noqa: RUF059


@pytest.mark.utils
@pytest.mark.parametrize("solver", [None, PyomoIpoptSolver, ScipyMinimizeSolver])
def test_payoff_require_success_rejects_an_unbounded_objective(solver):
    """Without `require_success` an unbounded objective yields made-up ideal and nadir values."""
    linear = {"is_linear": True, "is_convex": True, "is_twice_differentiable": True}
    problem = Problem(
        name="unbounded",
        description="f_1 has no lower bound.",
        variables=[
            Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real, initial_value=0.0),
            Variable(
                name="y", symbol="y", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=1, initial_value=0.5
            ),
        ],
        objectives=[
            Objective(name="f_1", symbol="f_1", func="x + y", **linear),
            Objective(name="f_2", symbol="f_2", func="y - x", **linear),
        ],
    )

    with pytest.raises(ValueError, match="f_1"):
        payoff_table_method(problem, solver, require_success=True)


@pytest.mark.utils
def test_is_heuristic_solver():
    """Stochastic solvers, and subclasses of them, are heuristic; the others and non-classes are not."""

    class _CustomNevergrad(NevergradGenericSolver):
        pass

    assert is_heuristic_solver(NevergradGenericSolver)
    assert is_heuristic_solver(ScipyDeSolver)
    assert is_heuristic_solver(_CustomNevergrad)
    assert not is_heuristic_solver(PyomoIpoptSolver)
    assert not is_heuristic_solver(ScipyMinimizeSolver)
    assert not is_heuristic_solver(None)
