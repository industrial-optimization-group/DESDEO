"""Tests for the gurobipy solver."""

import pytest

import gurobipy as gp
import numpy as np

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ScalarizationFunction,
    simple_linear_test_problem,
    simple_knapsack_vectors,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools import GurobipySolver, PersistentGurobipySolver


@pytest.mark.slow
@pytest.mark.gurobipy
def test_gurobipy_solver():
    """Tests the bonmin solver."""
    problem = simple_linear_test_problem()
    solver = GurobipySolver(problem)

    results = solver.solve("f_1")

    assert results.success

    xs = results.optimal_variables
    assert np.isclose(xs["x_1"], 4.2, atol=1e-8)
    assert np.isclose(xs["x_2"], 2.1, atol=1e-8)


@pytest.mark.slow
@pytest.mark.gurobipy
def test_gurobipy_persistent_solver():
    """Tests the bonmin solver."""
    problem = simple_linear_test_problem()
    solver = PersistentGurobipySolver(problem)

    results = solver.solve("f_1")

    assert results.success

    xs = results.optimal_variables
    assert np.isclose(xs["x_1"], 4.2, atol=1e-8)
    assert np.isclose(xs["x_2"], 2.1, atol=1e-8)

    testvar = Variable(name="test_y", symbol="y", variable_type=VariableTypeEnum.integer, lowerbound=-20, upperbound=30)
    solver.add_variable(testvar)
    assert isinstance(solver.evaluator.get_expression_by_name("y"), gp.Var)

    testconstr = Constraint(
        name="testconstraint", symbol="c_test", cons_type=ConstraintTypeEnum.EQ, func=["Add", "x_1", "x_2", "y", -20]
    )
    solver.add_constraint(testconstr)
    assert solver.evaluator.model.getConstrByName("c_test") is not None

    testobjective = Objective(name="testobjective", symbol="f_test", func=["Add", "y"])
    solver.add_objective(testobjective)
    assert isinstance(solver.evaluator.get_expression_by_name("f_test"), gp.Var)

    testscal = ScalarizationFunction(name="test scalarization function", symbol="scal", func=["Add", "f_test", "f_1"])
    solver.evaluator.add_scalarization_function(testscal)
    assert isinstance(solver.evaluator.get_expression_by_name("scal"), gp.LinExpr)

    solver.solve("scal")
    assert np.isclose(solver.evaluator.get_expression_by_name("scal").getValue(), 20)

    solver.remove_constraint("c_test")
    assert solver.evaluator.model.getConstrByName("c_test") is None

    solver.remove_variable("y")
    assert solver.evaluator.get_expression_by_name("y") is None

    # Check that the solver can still solve the original problem
    # after removing the added variables and constraints
    results = solver.solve("f_1")

    assert results.success

    xs = results.optimal_variables
    assert np.isclose(xs["x_1"], 4.2, atol=1e-8)
    assert np.isclose(xs["x_2"], 2.1, atol=1e-8)

    testvar = TensorVariable(
        name="test_y",
        symbol="y",
        variable_type=VariableTypeEnum.integer,
        shape=(2,2),
        lowerbound=[[-20, -20], [-20, -20]],
        upperbound=[[30, 30], [30, 30]]
    )
    solver.add_variable(testvar)
    assert isinstance(solver.evaluator.get_expression_by_name("y"), gp.MVar)

    solver.remove_variable("y")
    assert solver.evaluator.get_expression_by_name("y") is None


@pytest.mark.slow
@pytest.mark.gurobipy
def test_gurobipy_solver_with_tensors():
    """Test gurobipy solver with a problem with TensorVariables."""
    problem = simple_knapsack_vectors()
    solver = GurobipySolver(problem)

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
