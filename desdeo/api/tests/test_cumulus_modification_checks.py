"""Tests for the feasibility checks run when a CUMULUS problem modification is requested.

A modification may shrink the feasible region.  Two things can go wrong, and they are checked
separately because they cost very different amounts:

- the solution the decision maker is on may fall outside the new region.  Detecting that needs no
  solve, so it happens while the request is being handled;
- the new region may be empty altogether.  Detecting that needs one solve, so it happens in the
  background, and it runs before the payoff table, which needs one solve per objective.
"""

import pytest

from desdeo.api.routers.cumulus import (
    _current_solution_satisfies,
    _probe_new_problem_feasibility,
)
from desdeo.problem import Constraint, ConstraintTypeEnum
from desdeo.problem.testproblems import simple_test_problem
from desdeo.tools import ScipyMinimizeSolver, SolverResults


def _constraint(symbol: str, func) -> Constraint:
    """An `func <= 0` constraint."""
    return Constraint(
        name=symbol,
        symbol=symbol,
        cons_type=ConstraintTypeEnum.LTE,
        func=func,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )


class _FakeState:
    """Minimal stand-in for a StateDB whose state carries one solution."""

    def __init__(self, variables: dict[str, float], objectives: dict[str, float] | None = None):
        self.state = self
        self.solver_results = SolverResults(
            optimal_variables=variables,
            optimal_objectives=objectives or {},
            success=True,
            message="test",
        )


# ---------------------------------------------------------------------------
# _current_solution_satisfies
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_current_solution_satisfies_when_within_bound():
    """A current solution inside the new region is reported as still feasible."""
    problem = simple_test_problem()
    # x_1 = 1 and x_2 = 1 give f_1 = x_1 + x_2 = 2, so the bound holds with room to spare.
    added = [_constraint("_c", ["Subtract", "f_1", 10.0])]
    modified = problem.add_constraints(added)

    assert _current_solution_satisfies(modified, _FakeState({"x_1": 1.0, "x_2": 1.0}), added) is True


@pytest.mark.cumulus
def test_current_solution_excluded_by_new_bound():
    """A current solution outside the new region is reported, without any solve."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", -10.0])]
    modified = problem.add_constraints(added)

    assert _current_solution_satisfies(modified, _FakeState({"x_1": 1.0, "x_2": 1.0}), added) is False


@pytest.mark.cumulus
def test_current_solution_satisfies_without_a_parent_state():
    """With no previous solution there is nothing a modification could invalidate."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", -10.0])]
    modified = problem.add_constraints(added)

    assert _current_solution_satisfies(modified, None, added) is True


@pytest.mark.cumulus
def test_current_solution_checked_from_reported_objectives():
    """A bound is checked against the reported objective values, not only the decision vector.

    This is the case that matters for a combined scenario problem: its tensor constants defeat
    the evaluator, so re-evaluating at the decision vector cannot answer the question at all,
    and anything that leans on it reports every bound as satisfied.  The solver already reported
    `f_1`, which is all the bound needs.
    """
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", 1.0])]
    modified = problem.add_constraints(added)

    # No decision variables at all, so only the reported objective values can settle it.
    state = _FakeState({}, objectives={"f_1": 2.0})

    assert _current_solution_satisfies(modified, state, added) is False


@pytest.mark.cumulus
def test_current_solution_prefers_reported_values_over_reevaluation():
    """Reported values win: they describe the solution as the solver actually found it."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", 10.0])]
    modified = problem.add_constraints(added)

    # The decision vector would give f_1 = 2 (inside the bound); the reported f_1 is outside it.
    state = _FakeState({"x_1": 1.0, "x_2": 1.0}, objectives={"f_1": 50.0})

    assert _current_solution_satisfies(modified, state, added) is False


@pytest.mark.cumulus
def test_current_solution_ignores_constraints_the_modification_did_not_add():
    """Only the added constraints are checked; the rest held before the modification."""
    problem = simple_test_problem()
    violated = _constraint("_already_there", ["Subtract", "f_1", -10.0])
    added = [_constraint("_c", ["Subtract", "f_1", 10.0])]
    modified = problem.add_constraints([violated, *added])

    # `_already_there` is violated by this solution, but it is not part of this modification.
    assert _current_solution_satisfies(modified, _FakeState({"x_1": 1.0, "x_2": 1.0}), added) is True


@pytest.mark.cumulus
def test_current_solution_satisfies_when_nothing_was_added():
    """Nothing to check when the modification added no constraints."""
    problem = simple_test_problem()

    assert _current_solution_satisfies(problem, _FakeState({"x_1": 1.0, "x_2": 1.0}), []) is True


# ---------------------------------------------------------------------------
# _probe_new_problem_feasibility
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
@pytest.mark.scipy
def test_probe_reports_feasible_for_an_attainable_constraint():
    """A constraint that some solution satisfies leaves zero violation."""
    problem = simple_test_problem()

    feasible, violation, error = _probe_new_problem_feasibility(
        problem, [_constraint("_c", ["Subtract", "f_1", 10.0])], ScipyMinimizeSolver
    )

    assert feasible is True
    assert violation == pytest.approx(0.0, abs=1e-6)
    assert error is None


@pytest.mark.cumulus
@pytest.mark.scipy
def test_probe_reports_infeasible_and_says_by_how_much():
    """An unattainable constraint is reported with the smallest violation achievable.

    The number matters: it tells the decision maker how far out of reach their requirement is,
    rather than only that it cannot be met.
    """
    problem = simple_test_problem()

    feasible, violation, error = _probe_new_problem_feasibility(
        problem, [_constraint("_c", ["Subtract", "f_1", -1.0e6])], ScipyMinimizeSolver
    )

    assert feasible is False
    assert violation > 0.0
    assert error is not None
    assert "_c" in error, "the message must name the constraints that could not be met"
    assert "discarded" in error


@pytest.mark.cumulus
@pytest.mark.scipy
def test_probe_handles_a_constraint_over_several_objectives():
    """Constraints combining objectives are covered too.

    This is why violation is minimised rather than a reference point projected: a bound such as
    `f_1 + f_2 <= c` has no reference-point equivalent, but slack variables handle it like any
    other constraint.
    """
    problem = simple_test_problem()

    feasible, _, _ = _probe_new_problem_feasibility(
        problem, [_constraint("_c", ["Subtract", ["Add", "f_1", "f_2"], 1.0e6])], ScipyMinimizeSolver
    )
    assert feasible is True

    infeasible, violation, error = _probe_new_problem_feasibility(
        problem, [_constraint("_c", ["Subtract", ["Add", "f_1", "f_2"], -1.0e6])], ScipyMinimizeSolver
    )
    assert infeasible is False
    assert violation > 0.0
    assert error is not None


@pytest.mark.cumulus
def test_probe_with_no_added_constraints_is_feasible_without_solving():
    """A modification that adds no constraints cannot shrink the feasible region."""
    problem = simple_test_problem()

    # No solver is passed: reaching one would mean the probe solved something it need not.
    feasible, violation, error = _probe_new_problem_feasibility(problem, [], solver_class=None)

    assert feasible is True
    assert violation == 0.0
    assert error is None
