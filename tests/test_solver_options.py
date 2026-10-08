"""Tests for the solver constructors' handling of `options=None`.

Every solver interface is expected to treat `options=None` as "use the module defaults".
The interactive methods rely on this: they build a solver as
`init_solver(problem, solver_options)` where `solver_options` is `None` whenever the
caller did not supply any, so a solver that dereferences `options` unconditionally
crashes rather than falling back.
"""

import pytest

from desdeo.problem.testproblems import river_pollution_problem
from desdeo.tools import (
    CVXPYSolver,
    NevergradGenericSolver,
    ScipyDeSolver,
    ScipyMinimizeSolver,
)

# Solvers whose constructor accepts `river_pollution_problem`; each is expected to fall
# back to its module defaults when given `options=None`.  Regression test:
# CVXPYSolver, ScipyMinimizeSolver and ScipyDeSolver used to raise AttributeError here,
# which made `solve_intermediate_solutions` crash whenever it was given a solver class
# without matching options.
SOLVERS_ACCEPTING_NONE = [
    pytest.param(CVXPYSolver, marks=pytest.mark.cvxpy, id="CVXPYSolver"),
    pytest.param(ScipyMinimizeSolver, marks=pytest.mark.scipy, id="ScipyMinimizeSolver"),
    pytest.param(ScipyDeSolver, marks=pytest.mark.scipy, id="ScipyDeSolver"),
    pytest.param(NevergradGenericSolver, marks=pytest.mark.nevergrad, id="NevergradGenericSolver"),
]


@pytest.mark.parametrize("solver_class", SOLVERS_ACCEPTING_NONE)
def test_solver_accepts_none_options(solver_class):
    """Passing `options=None` explicitly must behave like omitting the argument."""
    problem = river_pollution_problem()

    assert solver_class(problem, None) is not None


@pytest.mark.parametrize("solver_class", SOLVERS_ACCEPTING_NONE)
def test_solver_none_options_matches_omitted_options(solver_class):
    """`options=None` must fall back to the defaults, not to some other configuration."""
    problem = river_pollution_problem()

    explicit_none = solver_class(problem, None)
    omitted = solver_class(problem)

    # Compare the option-derived attributes the constructors actually set, ignoring the
    # evaluator and problem, which are rebuilt per instance and do not compare equal.
    ignored = {"problem", "evaluator"}
    for attribute, value in vars(omitted).items():
        if attribute in ignored:
            continue
        assert vars(explicit_none)[attribute] == value, f"{attribute} differs"
