"""Tests for simulator and surrogate evaluator."""

import pytest
from fixtures import surrogate_file, surrogate_file2  # noqa: F401

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Evaluator,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)
from desdeo.problem.testproblems import simulator_problem


@pytest.mark.simulator_support
def test_w_analytical_simulator_surrogate_problem(surrogate_file, surrogate_file2):  # noqa: F811
    """Test the evaluator with a problem that has analytical, simulator and surrogate based functions."""
    problem = simulator_problem("tests/data")

    surrogates = {"f_5": surrogate_file, "f_6": surrogate_file2, "g_3": surrogate_file, "e_3": surrogate_file2}

    # test that the evaluator can be initialized with parameters and surrogate paths as arguments
    evaluator = Evaluator(
        problem=problem,
        params={"s_1": {"alpha": 0.1, "beta": 0.2}, "s_2": {"epsilon": 10, "gamma": 20}},
        surrogate_paths=surrogates,
    )

    res = evaluator.evaluate(
        {"x_1": [0, 1, 2, 3, 4], "x_2": [4, 3, 2, 1, 0], "x_3": [0, 4, 1, 3, 2], "x_4": [3, 1, 3, 2, 3]}
    )

    # check that a couple of the results are what they should be
    assert res["e_1"][0] == 2.0
    assert res["f_1"][0] == 0.4


@pytest.mark.simulator_support
def test_w_o_parameters(surrogate_file, surrogate_file2):  # noqa: F811
    """Test that not giving parameters does not break anything."""
    problem = simulator_problem("tests/data")

    surrogates = {"f_5": surrogate_file, "f_6": surrogate_file2, "g_3": surrogate_file, "e_3": surrogate_file2}

    evaluator = Evaluator(problem=problem, surrogate_paths=surrogates)

    res = evaluator.evaluate(
        {
            "x_1": [0, 1, 2, 3, 4],
            "x_2": [4, 3, 2, 1, 0],
            "x_3": [0, 4, 1, 3, 2],
            "x_4": [3, 1, 3, 2, 3],
        }
    )

    # check that a couple of the results are what they should be
    assert res["e_1"][0] == 2.0
    assert res["f_1"][0] == 4.0


@pytest.mark.simulator_support
def test_w_o_given_surrogate_paths(surrogate_file, surrogate_file2):  # noqa: F811
    """Test that not giving surrogate paths as argument does not break anything."""
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real),
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real),
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real),
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real),
        Variable(name="x_5", symbol="x_5", variable_type=VariableTypeEnum.real),
    ]
    f1 = Objective(name="f_5", symbol="f_5", surrogates=[surrogate_file], objective_type=ObjectiveTypeEnum.surrogate)
    f2 = Objective(name="f_6", symbol="f_6", surrogates=[surrogate_file2], objective_type=ObjectiveTypeEnum.surrogate)
    g1 = Constraint(
        name="g_3",
        symbol="g_3",
        cons_type=ConstraintTypeEnum.LTE,
        surrogates=[surrogate_file],
    )
    e1 = ExtraFunction(
        name="e_3",
        symbol="e_3",
        surrogates=[surrogate_file2],
    )
    problem = Problem(
        name="Simulator problem",
        description="",
        variables=variables,
        objectives=[f1, f2],
        constraints=[g1],
        extra_funcs=[e1],
    )

    evaluator = Evaluator(
        problem=problem,
        params={"s_1": {"alpha": 0.1, "beta": 0.2}, "s_2": {"epsilon": 10, "gamma": 20}},
    )

    res = evaluator.evaluate(
        {"x_1": [0, 1, 2, 3, 4], "x_2": [4, 3, 2, 1, 0], "x_3": [0, 4, 1, 3, 2], "x_4": [3, 1, 3, 2, 3]}
    )
