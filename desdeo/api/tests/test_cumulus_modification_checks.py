"""Tests for the feasibility checks run when a CUMULUS problem modification is requested.

A modification may shrink the feasible region.  Two things can go wrong, and they are checked
separately because they cost very different amounts:

- the solution the decision maker is on may fall outside the new region.  Detecting that needs no
  solve, so it happens while the request is being handled;
- the new region may be empty altogether.  Detecting that needs one solve, so it happens in the
  background, and it runs before the payoff table, which needs one solve per objective.
"""

import math

import pytest

from desdeo.api.routers.cumulus import (
    _all_variables_bounded,
    _changed_by_modification,
    _probe_new_problem_feasibility,
    _some_current_solution_satisfies,
)
from desdeo.problem import Constraint, ConstraintTypeEnum, TensorVariable, Variable, VariableTypeEnum
from desdeo.problem.testproblems import dtlz2, simple_test_problem
from desdeo.tools import NevergradGenericSolver, PyomoIpoptSolver, ScipyMinimizeSolver, SolverResults


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


def _solution(variables: dict[str, float], objectives: dict[str, float] | None = None) -> SolverResults:
    return SolverResults(
        optimal_variables=variables,
        optimal_objectives=objectives or {},
        success=True,
        message="test",
    )


class _FakeState:
    """Minimal stand-in for a StateDB whose state carries the given solutions."""

    def __init__(self, *solutions: SolverResults):
        self.state = self
        self.solver_results = list(solutions)

    @property
    def num_solutions(self) -> int:
        return len(self.solver_results)


_X_ONES = _solution({"x_1": 1.0, "x_2": 1.0})


# ---------------------------------------------------------------------------
# _some_current_solution_satisfies
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_current_solution_satisfies_when_within_bound():
    """A current solution inside the new region is reported as still feasible."""
    problem = simple_test_problem()
    # x_1 = 1 and x_2 = 1 give f_1 = x_1 + x_2 = 2, so the bound holds with room to spare.
    added = [_constraint("_c", ["Subtract", "f_1", 10.0])]
    modified = problem.add_constraints(added)

    assert _some_current_solution_satisfies(modified, _FakeState(_X_ONES), added) is True


@pytest.mark.cumulus
def test_current_solution_excluded_by_new_bound():
    """A current solution outside the new region is reported, without any solve."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", -10.0])]
    modified = problem.add_constraints(added)

    assert _some_current_solution_satisfies(modified, _FakeState(_X_ONES), added) is False


@pytest.mark.cumulus
def test_every_current_solution_is_checked():
    """A current solution other than the first can vouch for the bound."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "x_1", 1.5])]
    modified = problem.add_constraints(added)

    state = _FakeState(_solution({"x_1": 2.0, "x_2": 1.0}), _X_ONES)

    assert _some_current_solution_satisfies(modified, state, added) is True


@pytest.mark.cumulus
def test_current_solutions_unknown_without_a_parent_state():
    """With no previous solution nothing can be told, so the background probe has to run."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", -10.0])]
    modified = problem.add_constraints(added)

    assert _some_current_solution_satisfies(modified, None, added) is False


@pytest.mark.cumulus
def test_current_solutions_unknown_for_a_state_without_solutions():
    """A parent state holding no solutions (e.g. a modification state) proves nothing either."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", -10.0])]
    modified = problem.add_constraints(added)

    assert _some_current_solution_satisfies(modified, _FakeState(), added) is False


@pytest.mark.cumulus
def test_current_solution_undecided_when_values_are_missing():
    """A solution that carries nothing the constraint refers to is undecided, not satisfied."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "x_1", 1.5])]
    modified = problem.add_constraints(added)

    assert _some_current_solution_satisfies(modified, _FakeState(_solution({})), added) is False


@pytest.mark.cumulus
def test_current_solution_checked_from_reported_objectives():
    """A bound is checked against the reported objective values, not only the decision vector.

    This is the case that matters for a combined scenario problem: its tensor constants defeat
    the evaluator, so re-evaluating at the decision vector cannot answer the question at all.
    The solver already reported `f_1`, which is all the bound needs.
    """
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", 1.0])]
    modified = problem.add_constraints(added)

    # No decision variables at all, so only the reported objective values can settle it.
    state = _FakeState(_solution({}, objectives={"f_1": 2.0}))

    assert _some_current_solution_satisfies(modified, state, added) is False


@pytest.mark.cumulus
def test_current_solution_prefers_reported_values_over_reevaluation():
    """Reported values win: they describe the solution as the solver actually found it."""
    problem = simple_test_problem()
    added = [_constraint("_c", ["Subtract", "f_1", 10.0])]
    modified = problem.add_constraints(added)

    # The decision vector would give f_1 = 2 (inside the bound); the reported f_1 is outside it.
    state = _FakeState(_solution({"x_1": 1.0, "x_2": 1.0}, objectives={"f_1": 50.0}))

    assert _some_current_solution_satisfies(modified, state, added) is False


@pytest.mark.cumulus
def test_current_solution_ignores_constraints_the_modification_did_not_add():
    """Only the added constraints are checked; the rest held before the modification."""
    problem = simple_test_problem()
    violated = _constraint("_already_there", ["Subtract", "f_1", -10.0])
    added = [_constraint("_c", ["Subtract", "f_1", 10.0])]
    modified = problem.add_constraints([violated, *added])

    # `_already_there` is violated by this solution, but it is not part of this modification.
    assert _some_current_solution_satisfies(modified, _FakeState(_X_ONES), added) is True


@pytest.mark.cumulus
def test_current_solution_satisfies_when_nothing_was_added():
    """Nothing to check when the modification added no constraints."""
    problem = simple_test_problem()

    assert _some_current_solution_satisfies(problem, _FakeState(_X_ONES), []) is True


@pytest.mark.cumulus
def test_current_solution_undecided_for_a_constraint_without_a_function():
    """A simulator constraint cannot be evaluated at a stored solution, so it is never passed as met."""
    problem = simple_test_problem()
    simulated = Constraint(
        name="_sim", symbol="_sim", cons_type=ConstraintTypeEnum.LTE, func=None, simulator_path="sim.py"
    )
    added = [_constraint("_c", ["Subtract", "f_1", 10.0]), simulated]

    state = _FakeState(_X_ONES, _solution({"x_1": 2.0, "x_2": 1.0}))

    assert _some_current_solution_satisfies(problem, state, added) is False


# ---------------------------------------------------------------------------
# _changed_by_modification
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_changed_constraints_are_the_added_and_replaced_ones():
    """Added and replaced constraints are reported; one left as it was is not."""
    kept = _constraint("_kept", ["Subtract", "x_1", 10.0])
    replaced = _constraint("_replaced", ["Subtract", "x_1", 10.0])
    old = simple_test_problem().add_constraints([kept, replaced])

    tightened = replaced.model_copy(update={"func": ["Subtract", "x_1", 1.0]})
    added = _constraint("_added", ["Subtract", "x_2", 1.0])
    new = old.model_copy(update={"constraints": [kept, tightened, added]})

    changed, only_constraints = _changed_by_modification(old, new)

    assert only_constraints is True
    assert sorted(c.symbol for c in changed) == ["_added", "_replaced"]


@pytest.mark.cumulus
def test_changed_variable_bounds_put_every_constraint_in_question():
    """Once a variable changes, constraints that held before may not any more."""
    old = simple_test_problem().add_constraints([_constraint("_kept", ["Subtract", "x_1", 10.0])])
    variables = [
        v.model_copy(update={"lowerbound": 20.0, "upperbound": 30.0}) if v.symbol == "x_1" else v for v in old.variables
    ]
    new = old.model_copy(update={"variables": variables})

    changed, only_constraints = _changed_by_modification(old, new)

    assert only_constraints is False
    assert [c.symbol for c in changed] == ["_kept"]


@pytest.mark.cumulus
def test_nothing_changed_by_removing_a_constraint():
    """Removing a constraint only enlarges the feasible region."""
    old = simple_test_problem().add_constraints([_constraint("_gone", ["Subtract", "x_1", 10.0])])
    new = old.model_copy(update={"constraints": None})

    assert _changed_by_modification(old, new) == ([], True)


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


@pytest.mark.cumulus
def test_probe_reports_undetermined_when_the_solve_fails():
    """A failed solve leaves feasibility undetermined; it does not refute it."""
    problem = simple_test_problem()

    class _BrokenSolver:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    feasible, violation, error = _probe_new_problem_feasibility(
        problem, [_constraint("_c", ["Subtract", "f_1", 10.0])], _BrokenSolver
    )

    assert feasible is None
    assert math.isnan(violation)
    assert error is not None
    assert "Could not determine" in error
    assert "discarded" in error


@pytest.mark.cumulus
@pytest.mark.pyomo
def test_probe_works_with_a_solver_that_needs_derivatives():
    """The violation problem stays twice differentiable, so a gradient-based solver accepts it.

    The probe is handed the solver chosen for the modified problem, typically Ipopt for a smooth
    one; a relaxation that lost the flag would make every probe fail and every bound be refused.
    """
    problem = dtlz2(5, 3)
    bound = _constraint("_c", ["Subtract", "f_1", 10.0]).model_copy(update={"is_linear": False, "is_convex": False})
    unreachable = _constraint("_c", ["Add", "f_1", 1.0]).model_copy(update={"is_linear": False, "is_convex": False})

    feasible, _, _ = _probe_new_problem_feasibility(problem, [bound], PyomoIpoptSolver)
    assert feasible is True

    # DTLZ2 objectives are non-negative, so f_1 <= -1 is out of reach.
    infeasible, violation, _ = _probe_new_problem_feasibility(problem, [unreachable], PyomoIpoptSolver)
    assert infeasible is False
    assert violation > 0.0


@pytest.mark.cumulus
def test_probe_with_a_heuristic_solver_reports_undetermined():
    """A positive violation from a stochastic solver does not prove the constraints unsatisfiable."""
    problem = simple_test_problem()

    class _NoisySolver(NevergradGenericSolver):
        def __init__(self, problem, *args, **kwargs):
            self.problem = problem

        def solve(self, target):
            return SolverResults(
                optimal_variables={}, optimal_objectives={target: 0.0125}, success=True, message="noisy"
            )

    feasible, violation, error = _probe_new_problem_feasibility(
        problem, [_constraint("_c", ["Subtract", "f_1", 10.0])], _NoisySolver
    )

    assert feasible is None
    assert violation == pytest.approx(0.0125)
    assert "heuristic" in error
    assert "discarded" in error


@pytest.mark.cumulus
def test_probe_reports_undetermined_for_a_constraint_without_a_function():
    """The probe cannot soften a simulator constraint, so it cannot vouch for it either."""
    problem = simple_test_problem()
    simulated = Constraint(
        name="_sim", symbol="_sim", cons_type=ConstraintTypeEnum.LTE, func=None, simulator_path="sim.py"
    )

    feasible, _, error = _probe_new_problem_feasibility(problem, [simulated], ScipyMinimizeSolver)

    assert feasible is None
    assert "discarded" in error


# ---------------------------------------------------------------------------
# _all_variables_bounded
# ---------------------------------------------------------------------------


@pytest.mark.cumulus
def test_all_variables_bounded():
    """Every variable, and every element of a tensor variable, needs finite bounds on both sides."""
    problem = simple_test_problem()
    assert _all_variables_bounded(problem) is True

    half_open = Variable(name="z", symbol="z", variable_type=VariableTypeEnum.real, lowerbound=0.0)
    assert _all_variables_bounded(problem.model_copy(update={"variables": [*problem.variables, half_open]})) is False

    def tensor(upperbounds) -> TensorVariable:
        return TensorVariable(
            name="X",
            symbol="X",
            variable_type=VariableTypeEnum.real,
            shape=[2],
            lowerbounds=[0.0, 0.0],
            upperbounds=upperbounds,
        )

    boxed = problem.model_copy(update={"variables": [*problem.variables, tensor([1.0, 2.0])]})
    assert _all_variables_bounded(boxed) is True
    gap = problem.model_copy(update={"variables": [*problem.variables, tensor([1.0, None])]})
    assert _all_variables_bounded(gap) is False
