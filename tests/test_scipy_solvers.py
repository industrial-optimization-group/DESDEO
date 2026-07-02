"""Tests for the scipy solver interfaces."""

import pytest

from desdeo.problem import Objective, Problem, ScalarizationFunction, Variable
from desdeo.problem.testproblems import binh_and_korn
from desdeo.tools.scipy_solver_interfaces import ScipyDeSolver, ScipyMinimizeSolver, set_initial_guess


@pytest.mark.scipy
def test_scipy_de_with_constraints():
    """Tests the scipy differential evolution solver with constraints."""
    problem = binh_and_korn((False, False))

    target = "first"
    problem = problem.add_scalarization(
        ScalarizationFunction(
            name=target,
            symbol=target,
            func="1*f_2",
            is_linear=problem.is_linear,
            is_convex=problem.is_convex,
            is_twice_differentiable=problem.is_twice_differentiable,
        )
    )

    solver = ScipyDeSolver(problem)

    solver.solve(target)


def _make_mixed_problem() -> Problem:
    """Creates a problem with both a minimize and a maximize objective.

    f_min_obj(x, y) = x + y  (minimize) — optimum at x=0, y=0
    f_max_obj(x, y) = -x - y (maximize) — optimum at x=0, y=0

    Both objectives agree on the optimum (x=0, y=0), so single-objective
    solves for either should find the same point.
    """
    return Problem(
        name="Mixed min/max test",
        description="Two objectives: one to minimize, one to maximize.",
        variables=[
            Variable(
                name="x",
                symbol="x",
                variable_type="real",
                lowerbound=0.0,
                upperbound=10.0,
                initial_value=5.0,
            ),
            Variable(
                name="y",
                symbol="y",
                variable_type="real",
                lowerbound=0.0,
                upperbound=10.0,
                initial_value=5.0,
            ),
        ],
        objectives=[
            Objective(
                name="f_min_obj",
                symbol="f_min_obj",
                func="x + y",
                maximize=False,
            ),
            Objective(
                name="f_max_obj",
                symbol="f_max_obj",
                func="-x - y",
                maximize=True,
            ),
        ],
    )


@pytest.mark.scipy
def test_scipy_minimize_respects_maximize_with_objective_target():
    """Tests that ScipyMinimizeSolver handles both minimize and maximize objectives.

    Solving for f_max_obj (maximize=True, func=-x-y) should find x=0, y=0
    (the point where -x-y is largest, i.e., 0).
    Solving for f_min_obj (maximize=False, func=x+y) should also find x=0, y=0.
    """
    problem = _make_mixed_problem()

    # Solve for the maximize objective
    solver = ScipyMinimizeSolver(problem)
    result = solver.solve("f_max_obj")

    assert result.optimal_variables["x"] == pytest.approx(0.0, abs=0.1), (
        f"Expected x ≈ 0.0 for maximized f_max_obj, got {result.optimal_variables['x']}. "
        "ScipyMinimizeSolver appears to ignore the maximize flag."
    )
    assert result.optimal_variables["y"] == pytest.approx(0.0, abs=0.1), (
        f"Expected y ≈ 0.0 for maximized f_max_obj, got {result.optimal_variables['y']}."
    )

    # Solve for the minimize objective
    result_min = solver.solve("f_min_obj")

    assert result_min.optimal_variables["x"] == pytest.approx(0.0, abs=0.1), (
        f"Expected x ≈ 0.0 for minimized f_min_obj, got {result_min.optimal_variables['x']}."
    )
    assert result_min.optimal_variables["y"] == pytest.approx(0.0, abs=0.1), (
        f"Expected y ≈ 0.0 for minimized f_min_obj, got {result_min.optimal_variables['y']}."
    )


def _make_bounds_problem(lowerbound: float | None, upperbound: float | None) -> Problem:
    """Creates a single-variable problem with the given (possibly missing) bounds and no initial value."""
    return Problem(
        name="Bounds test",
        description="A single variable with configurable bounds and no initial value.",
        variables=[
            Variable(
                name="x",
                symbol="x",
                variable_type="real",
                lowerbound=lowerbound,
                upperbound=upperbound,
            ),
        ],
        objectives=[
            Objective(name="f", symbol="f", func="x", maximize=False),
        ],
    )


@pytest.mark.scipy
def test_set_initial_guess_uses_explicit_initial_value():
    """An explicit initial_value should be used as-is, regardless of bounds."""
    problem = _make_mixed_problem()
    assert set_initial_guess(problem) == [5.0, 5.0]


@pytest.mark.scipy
def test_set_initial_guess_uses_midpoint_when_both_bounds_present():
    """With no initial_value, both bounds present should yield their midpoint."""
    problem = _make_bounds_problem(lowerbound=0.0, upperbound=10.0)
    assert set_initial_guess(problem) == [5.0]


@pytest.mark.scipy
def test_set_initial_guess_uses_lowerbound_when_upperbound_missing():
    """With no initial_value and no upper bound, the lower bound should be used."""
    problem = _make_bounds_problem(lowerbound=3.0, upperbound=None)
    assert set_initial_guess(problem) == [3.0]


@pytest.mark.scipy
def test_set_initial_guess_uses_upperbound_when_lowerbound_missing():
    """With no initial_value and no lower bound, the upper bound should be used."""
    problem = _make_bounds_problem(lowerbound=None, upperbound=7.0)
    assert set_initial_guess(problem) == [7.0]


@pytest.mark.scipy
def test_set_initial_guess_defaults_to_zero_when_both_bounds_missing():
    """With no initial_value and no bounds at all, the initial guess should default to 0."""
    problem = _make_bounds_problem(lowerbound=None, upperbound=None)
    assert set_initial_guess(problem) == [0]


@pytest.mark.scipy
def test_scipy_minimize_respects_maximize_with_scalarization_target():
    """Tests that ScipyMinimizeSolver maximizes correctly when solving via a scalarization function.

    The scalarization uses f_max_obj_min, which the evaluator negates for
    maximize=True objectives. Minimizing the scalarization should find x=0, y=0.
    """
    problem = _make_mixed_problem()
    problem = problem.add_scalarization(
        ScalarizationFunction(
            name="scal",
            symbol="scal",
            func="f_max_obj_min + f_min_obj_min",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
        )
    )

    solver = ScipyMinimizeSolver(problem)
    result = solver.solve("scal")

    assert result.optimal_variables["x"] == pytest.approx(0.0, abs=0.1), (
        f"Expected x ≈ 0.0 when solving scalarization, got {result.optimal_variables['x']}."
    )
    assert result.optimal_variables["y"] == pytest.approx(0.0, abs=0.1), (
        f"Expected y ≈ 0.0 when solving scalarization, got {result.optimal_variables['y']}."
    )


@pytest.mark.scipy
def test_scipy_minimize_still_minimizes_when_maximize_is_false():
    """Tests that objectives with maximize=False are still minimized correctly.

    Solving for f_min_obj (x+y, minimize) should find x=0, y=0.
    Ensures the _min rewriting doesn't break the default minimization behavior.
    """
    problem = _make_mixed_problem()

    solver = ScipyMinimizeSolver(problem)
    result = solver.solve("f_min_obj")

    assert result.optimal_variables["x"] == pytest.approx(0.0, abs=0.1), (
        f"Expected x ≈ 0.0 for a minimized objective, got {result.optimal_variables['x']}."
    )
    assert result.optimal_variables["y"] == pytest.approx(0.0, abs=0.1), (
        f"Expected y ≈ 0.0 for a minimized objective, got {result.optimal_variables['y']}."
    )
