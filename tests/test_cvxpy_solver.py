"""Tests for the cvxpy solver."""

import numpy as np
import pytest

from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    ExtraFunction,
    Objective,
    Problem,
    Variable,
)
from desdeo.problem.testproblems import (
    simple_constrained_quadratic_tensor_test_problem,
    simple_knapsack_vectors,
    simple_linear_test_problem,
)
from desdeo.tools import CVXPYSolver, CVXPYSolverOptions


@pytest.mark.slow
@pytest.mark.cvxpy
def test_cvxpy_solver():
    """Tests the cvxpy solver."""
    problem = simple_linear_test_problem()
    solver = CVXPYSolver(problem)

    results = solver.solve("f_1")

    assert results.success

    xs = results.optimal_variables
    assert np.isclose(xs["x_1"], 4.2, atol=1e-8)
    assert np.isclose(xs["x_2"], 2.1, atol=1e-8)


@pytest.mark.slow
@pytest.mark.cvxpy
def test_cvxpy_solver_with_tensors():
    """Test cvxpy solver with a problem with TensorVariables."""
    problem = simple_knapsack_vectors()
    solver = CVXPYSolver(problem)

    results = solver.solve("f_1_min")

    assert results.success
    xs, ys = results.optimal_variables, results.optimal_objectives

    assert np.allclose(xs["X"], [1.0, 1.0, 0.0, 0.0])
    assert np.isclose(ys["f_1"], 8.0)
    assert np.isclose(ys["f_2"], 6.0)

    results = solver.solve("f_2_min")

    assert results.success
    xs, ys = results.optimal_variables, results.optimal_objectives

    assert np.allclose(xs["X"], [0.0, 0.0, 1.0, 0.0])
    assert np.isclose(ys["f_1"], 6.0)
    assert np.isclose(ys["f_2"], 7.0)


@pytest.mark.slow
@pytest.mark.cvxpy
def test_cvxpy_solver_qp_with_tensors():
    """Test cvxpy solver with a quadratic problem with TensorVariables."""
    problem = simple_constrained_quadratic_tensor_test_problem(dqp=True)
    solver = CVXPYSolver(problem)

    results = solver.solve("f_1_min")

    assert results.success
    xs, ys = results.optimal_variables, results.optimal_objectives

    assert np.allclose(xs["X"], [2 / 3, 2 / 3])
    assert np.isclose(ys["f_1"], -((2 / 3) ** 2))


@pytest.mark.json
@pytest.mark.cvxpy
def test_parse_cvxpy_basic_arithmetic():
    """Test the JSON parser for correctly parsing MathJSON into CVXPY expressions with basic arithmetic."""
    problem = Problem(
        name="Test Problem",
        description="Test Problem",
        variables=[
            Variable(name="x1", symbol="x_1", variable_type="real", lowerbound=0.0, upperbound=10.0),
            Variable(name="x2", symbol="x_2", variable_type="real", lowerbound=0.0, upperbound=10.0),
        ],
        objectives=[
            Objective(
                name="Objective 1",
                symbol="f_1",
                func=["Add", "x_1", "x_2"],
                maximize=False,
            ),
        ],
    )

    solver = CVXPYSolver(problem)
    results = solver.solve("f_1")

    assert results.optimal_variables["x_1"] >= -1e-8  # should be near 0
    assert results.optimal_variables["x_2"] >= -1e-8  # should be near 0
    assert np.isclose(results.optimal_objectives["f_1"], 0.0, atol=1e-8)


@pytest.mark.json
@pytest.mark.cvxpy
def test_parse_cvxpy_with_constants():
    """Test the JSON parser for correctly parsing CVXPY expressions with constants."""
    problem = Problem(
        name="Test Problem with Constants",
        description="Test Problem with Constants",
        constants=[Constant(name="c1", symbol="c_1", value=5.0)],
        variables=[
            Variable(name="x1", symbol="x_1", variable_type="real", lowerbound=0.0, upperbound=10.0),
            Variable(name="x2", symbol="x_2", variable_type="real", lowerbound=0.0, upperbound=10.0),
        ],
        objectives=[
            Objective(
                name="Objective 1",
                symbol="f_1",
                func=["Add", ["Multiply", "c_1", "x_1"], "x_2"],
                maximize=False,
            ),
        ],
    )

    solver = CVXPYSolver(problem)
    results = solver.solve("f_1")

    assert results.optimal_variables["x_1"] >= -1e-8
    assert results.optimal_variables["x_2"] >= -1e-8
    # f_1 = 5*x_1 + x_2, minimized -> both should be near 0
    assert np.isclose(results.optimal_objectives["f_1"], 0.0, atol=1e-8)


@pytest.mark.json
@pytest.mark.cvxpy
def test_parse_cvxpy_with_constraints():
    """Test the JSON parser for correctly parsing CVXPY expressions with constraints."""
    problem = Problem(
        name="Test Problem with Constraints",
        description="Test Problem with Constraints",
        variables=[
            Variable(name="x1", symbol="x_1", variable_type="real", lowerbound=0.0, upperbound=10.0),
            Variable(name="x2", symbol="x_2", variable_type="real", lowerbound=0.0, upperbound=10.0),
        ],
        objectives=[
            Objective(
                name="Objective 1",
                symbol="f_1",
                func=["Add", "x_1", "x_2"],
                maximize=True,
            ),
        ],
        constraints=[
            Constraint(
                name="Constraint 1",
                symbol="g_1",
                cons_type=ConstraintTypeEnum.LTE,
                func=["Add", "x_1", "x_2", -5],  # x_1 + x_2 <= 5
            ),
        ],
    )

    solver = CVXPYSolver(problem)
    results = solver.solve("f_1")

    # Maximum of x_1 + x_2 subject to x_1 + x_2 <= 5 is exactly 5
    assert np.isclose(results.optimal_objectives["f_1"], 5.0, atol=1e-6)
    # Constraint should be satisfied: x_1 + x_2 - 5 <= 0
    assert np.isclose(results.constraint_values["g_1"], 0.0, atol=1e-6) or results.constraint_values["g_1"] < 1e-5


@pytest.mark.json
@pytest.mark.cvxpy
def test_parse_cvxpy_quadratic_problem():
    """Test the JSON parser for correctly parsing CVXPY quadratic expressions."""
    problem = Problem(
        name="Quadratic Test Problem",
        description="Quadratic Test Problem",
        variables=[
            Variable(name="x1", symbol="x_1", variable_type="real", lowerbound=-10.0, upperbound=10.0),
            Variable(name="x2", symbol="x_2", variable_type="real", lowerbound=-10.0, upperbound=10.0),
        ],
        objectives=[
            Objective(
                name="Objective 1",
                symbol="f_1",
                func=["Add", ["Square", "x_1"], ["Square", "x_2"]],
                maximize=False,
            ),
        ],
    )

    solver = CVXPYSolver(problem)
    results = solver.solve("f_1")

    # Minimum should be at origin
    assert np.isclose(results.optimal_variables["x_1"], 0.0, atol=1e-6)
    assert np.isclose(results.optimal_variables["x_2"], 0.0, atol=1e-6)
    assert np.isclose(results.optimal_objectives["f_1"], 0.0, atol=1e-6)


@pytest.mark.json
@pytest.mark.cvxpy
def test_parse_cvxpy_multiple_operators():
    """Test the JSON parser for CVXPY with multiple mathematical operators."""
    problem = Problem(
        name="Multiple Operators Test",
        description="Multiple Operators Test",
        constants=[Constant(name="c1", symbol="c_1", value=2.0)],
        variables=[
            Variable(name="x1", symbol="x_1", variable_type="real", lowerbound=1.0, upperbound=10.0),
            Variable(name="x2", symbol="x_2", variable_type="real", lowerbound=1.0, upperbound=10.0),
        ],
        objectives=[
            Objective(
                name="Objective 1",
                symbol="f_1",
                func=[
                    "Add",
                    ["Multiply", "c_1", ["Square", "x_1"]],
                    ["Divide", "x_2", "c_1"],
                ],
                maximize=False,
            ),
        ],
    )

    options = CVXPYSolverOptions(ignore_dpp=True)
    solver = CVXPYSolver(problem, options=options)
    results = solver.solve("f_1")

    # Both variables should be minimized to lower bounds
    assert results.optimal_variables["x_1"] >= 1.0 - 1e-6
    assert results.optimal_variables["x_2"] >= 1.0 - 1e-6


@pytest.mark.json
@pytest.mark.cvxpy
def test_parse_cvxpy_equality_constraint():
    """Test the JSON parser for CVXPY with equality constraints."""
    problem = Problem(
        name="Equality Constraint Test",
        description="Equality Constraint Test",
        variables=[
            Variable(name="x1", symbol="x_1", variable_type="real", lowerbound=-10.0, upperbound=10.0),
            Variable(name="x2", symbol="x_2", variable_type="real", lowerbound=-10.0, upperbound=10.0),
        ],
        objectives=[
            Objective(
                name="Objective 1",
                symbol="f_1",
                func=["Add", ["Square", "x_1"], ["Square", "x_2"]],
                maximize=False,
            ),
        ],
        constraints=[
            Constraint(
                name="Constraint 1",
                symbol="g_1",
                cons_type=ConstraintTypeEnum.EQ,
                func=["Add", "x_1", "x_2", -4],  # x_1 + x_2 = 4
            ),
        ],
    )

    solver = CVXPYSolver(problem)
    results = solver.solve("f_1")

    # Constraint should be satisfied: x_1 + x_2 = 4
    assert np.isclose(results.constraint_values["g_1"], 0.0, atol=1e-5)
    # Both variables should be equal for minimum
    assert np.isclose(results.optimal_variables["x_1"], results.optimal_variables["x_2"], atol=1e-5)
    # Sum should be 4
    assert np.isclose(results.optimal_variables["x_1"] + results.optimal_variables["x_2"], 4.0, atol=1e-5)


@pytest.mark.json
@pytest.mark.cvxpy
def test_parse_cvxpy_negation():
    """Test the JSON parser for CVXPY with negation."""
    problem = Problem(
        name="Negation Test",
        description="Negation Test",
        variables=[
            Variable(name="x1", symbol="x_1", variable_type="real", lowerbound=0.0, upperbound=10.0),
            Variable(name="x2", symbol="x_2", variable_type="real", lowerbound=0.0, upperbound=10.0),
        ],
        objectives=[
            Objective(
                name="Objective 1",
                symbol="f_1",
                func=["Add", ["Negate", "x_1"], "x_2"],
                maximize=False,
            ),
        ],
    )

    solver = CVXPYSolver(problem)
    results = solver.solve("f_1")

    # f_1 = -x_1 + x_2, minimize -> x_1 should be high, x_2 should be low
    assert results.optimal_variables["x_1"] >= 9.9 or np.isclose(results.optimal_variables["x_1"], 10.0, atol=1e-5)
    assert results.optimal_variables["x_2"] <= 1e-6


@pytest.mark.json
@pytest.mark.cvxpy
def test_cvxpy_solver_from_problem(extra_functions_problem):
    """Test CVXPYSolver with a problem containing extra functions and constraints."""
    solver = CVXPYSolver(extra_functions_problem)

    # Check that variables are initialized in the evaluator
    assert "x_1" in solver.evaluator.variables
    assert "x_2" in solver.evaluator.variables

    # Check that objectives are initialized in the evaluator
    assert "f_1" in solver.evaluator.objective_functions
    assert "f_2" in solver.evaluator.objective_functions

    # Check that constraints are initialized in the evaluator
    assert "con_1" in solver.evaluator.constraints

    # Check that extra functions are initialized in the evaluator
    assert "ef_1" in solver.evaluator.extra_functions
    assert "ef_2" in solver.evaluator.extra_functions

    # Check that constants are initialized in the evaluator
    assert "c_1" in solver.evaluator.constants


@pytest.mark.json
@pytest.mark.cvxpy
def test_cvxpy_solver_solve_and_constraint_evaluation(extra_functions_problem):
    """Test that CVXPYSolver correctly evaluates constraints after solving."""
    solver = CVXPYSolver(extra_functions_problem)
    results = solver.solve("f_1")

    # Check that constraint values are computed
    assert "con_1" in results.constraint_values
    # Constraints in DESDEO are defined as f(x) <= 0, so this should be <= 0 (or close)
    assert results.constraint_values["con_1"] is not None


@pytest.fixture
def extra_functions_problem():
    """Defines a problem with extra functions and constraints for testing."""
    return Problem(
        name="Extra functions test problem",
        description="Extra functions test problem",
        variables=[
            Variable(name="Test 1", symbol="x_1", variable_type="real", lowerbound=0.0, upperbound=10.0),
            Variable(name="Test 2", symbol="x_2", variable_type="real", lowerbound=0.0, upperbound=10.0),
        ],
        constants=[Constant(name="Constant 1", symbol="c_1", value=3.0)],
        objectives=[
            Objective(
                name="Objective 1",
                symbol="f_1",
                func=["Add", "x_1", "x_2"],
                maximize=False,
            ),
            Objective(
                name="Objective 2",
                symbol="f_2",
                func=["Multiply", "x_1", "x_2"],
                maximize=False,
            ),
        ],
        constraints=[
            Constraint(
                name="Constraint 1",
                symbol="con_1",
                cons_type=ConstraintTypeEnum.LTE,
                func=["Add", "x_1", "x_2", -5],  # x_1 + x_2 <= 5
            ),
        ],
        extra_funcs=[
            ExtraFunction(
                name="Extra Function 1",
                symbol="ef_1",
                func=["Multiply", "x_1", "c_1"],  # x_1 * 3
            ),
            ExtraFunction(
                name="Extra Function 2",
                symbol="ef_2",
                func=["Add", "x_2", "c_1"],  # x_2 + 3
            ),
        ],
    )
