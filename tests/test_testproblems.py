"""Test some of the test problems found in DESDEO."""

import numpy as np

from desdeo.problem import GenericEvaluator, dtlz2, re21, re22, re23


def test_dtlz2():
    """Test that the DTLZ2 problem initializes and evaluates correctly."""
    test_variables = [3, 5, 10, 50]
    test_objectives = [2, 4, 5, 7]

    for n_variables, n_objectives in zip(test_variables, test_objectives, strict=True):
        problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)

        assert len(problem.variables) == n_variables
        assert len(problem.objectives) == n_objectives

        xs = {f"{var.symbol}": [0.5] for var in problem.variables}

        evaluator = GenericEvaluator(problem)

        res = evaluator.evaluate(xs)

        assert np.isclose(sum(res[obj.symbol][0] ** 2 for obj in problem.objectives), 1.0)

    problem = dtlz2(n_variables=5, n_objectives=3)

    xs = {f"{var.symbol}": [0.55] for var in problem.variables}

    assert sum(res[obj.symbol][0] ** 2 for obj in problem.objectives) != 1.0

def test_re21():
    """Test that the four bar truss design problem evaluates correctly."""
    problem = re21()

    evaluator = GenericEvaluator(problem)

    xs = {f"{var.symbol}": [2] for var in problem.variables}

    res = evaluator.evaluate(xs)
    obj_symbols = [obj.symbol for obj in problem.objectives]

    objective_values = res[obj_symbols].to_numpy()[0]
    assert np.allclose(objective_values, np.array([2048.528137, 0.02]))

def test_re22():
    """Test that the reinforced concrete beam design problem evaluates correctly."""
    problem = re22()

    evaluator = GenericEvaluator(problem)

    xs = {"x_2": [10], "x_3": [20]}
    for i in range(len(problem.variables) - 2):
        if i == 68:
            xs[f"x_1_{i}"] = [1.0]
        else:
            xs[f"x_1_{i}"] = [0.0]

    res = evaluator.evaluate(xs)

    obj_values = [res[obj.symbol][0] for obj in problem.objectives]
    assert np.allclose(obj_values, np.array([421.938, 2]))

def test_re23():
    """Test that the pressure vessel design problem evaluates correctly."""
    problem = re23()

    from desdeo.problem import GenericEvaluator
    evaluator = GenericEvaluator(problem)

    xs = [{"x_1": 50, "x_2": 50, "x_3": 10, "x_4": 10}, {"x_1": 11, "x_2": 63, "x_3": 78, "x_4": 187}]
    expected_result = np.array([[2996.845703, 5.9616],[49848.35467, 4266017.057]])

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i])
