"""Tests for Lagrange multiplier extraction from solvers via NIMBUS and RPM."""

import pytest

from desdeo.mcdm import rpm_solve_solutions
from desdeo.mcdm.nimbus import generate_starting_point, solve_sub_problems
from desdeo.problem.testproblems import river_pollution_problem
from desdeo.tools import PyomoIpoptSolver, SolverResults


@pytest.mark.nimbus
def test_rpm_solver_returns_multipliers():
    """Test that RPM solutions include Lagrange multipliers when using Ipopt."""
    problem = river_pollution_problem(five_objective_variant=False)
    reference_point = {"f_1": -6, "f_2": -3, "f_3": 7, "f_4": 0.5}

    results = rpm_solve_solutions(problem, reference_point, solver=PyomoIpoptSolver)

    assert len(results) == 5
    assert all(result.success for result in results)

    # At least some results should have multipliers (Ipopt should provide duals)
    has_multipliers = [r.lagrange_multipliers is not None for r in results]
    assert any(has_multipliers), "Expected at least some results to have Lagrange multipliers"


@pytest.mark.nimbus
def test_nimbus_solver_returns_multipliers():
    """Test that NIMBUS sub-problem solutions include Lagrange multipliers."""
    problem = river_pollution_problem(five_objective_variant=False)
    reference_point = {"f_1": -6, "f_2": -3, "f_3": 7, "f_4": 0.5}

    starting_point = generate_starting_point(problem, reference_point=reference_point, solver=PyomoIpoptSolver)
    assert starting_point.success

    num_desired = 3
    results = solve_sub_problems(
        problem=problem,
        current_objectives=starting_point.optimal_objectives,
        reference_point=reference_point,
        num_desired=num_desired,
        solver=PyomoIpoptSolver,
    )

    assert len(results) == num_desired
    assert all(result.success for result in results)

    has_multipliers = [r.lagrange_multipliers is not None for r in results]
    assert any(has_multipliers), "Expected at least some NIMBUS results to have Lagrange multipliers"


@pytest.mark.nimbus
def test_solver_results_multiplier_field_defaults_none():
    """Test that SolverResults without multipliers has lagrange_multipliers=None."""
    result = SolverResults(
        optimal_variables={"x_1": 1.0},
        optimal_objectives={"f_1": 0.5},
        success=True,
        message="Test",
    )
    assert result.lagrange_multipliers is None
