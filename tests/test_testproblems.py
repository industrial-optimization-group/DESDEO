"""Test some of the test problems found in DESDEO."""

import numpy as np
import pytest

from desdeo.problem import (
    PolarsEvaluator,
    dtlz2,
    forest_problem,
    re21,
    re22,
    re23,
    re24,
)
from desdeo.tools import GurobipySolver


@pytest.mark.testproblem
def test_dtlz2():
    """Test that the DTLZ2 problem initializes and evaluates correctly."""
    test_variables = [3, 5, 10, 50]
    test_objectives = [2, 4, 5, 7]

    for n_variables, n_objectives in zip(test_variables, test_objectives, strict=True):
        problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)

        assert len(problem.variables) == n_variables
        assert len(problem.objectives) == n_objectives

        xs = {f"{var.symbol}": [0.5] for var in problem.variables}

        evaluator = PolarsEvaluator(problem)

        res = evaluator.evaluate(xs)

        assert np.isclose(sum(res[obj.symbol][0] ** 2 for obj in problem.objectives), 1.0)

    problem = dtlz2(n_variables=5, n_objectives=3)

    xs = {f"{var.symbol}": [0.55] for var in problem.variables}

    assert sum(res[obj.symbol][0] ** 2 for obj in problem.objectives) != 1.0


@pytest.mark.testproblem
def test_re21():
    """Test that the four bar truss design problem evaluates correctly."""
    problem = re21()

    evaluator = PolarsEvaluator(problem)

    xs = {f"{var.symbol}": [2] for var in problem.variables}

    res = evaluator.evaluate(xs)
    obj_symbols = [obj.symbol for obj in problem.objectives]

    objective_values = res[obj_symbols].to_numpy()[0]
    assert np.allclose(objective_values, np.array([2048.528137, 0.02]))


@pytest.mark.testproblem
def test_re22():
    """Test that the reinforced concrete beam design problem evaluates correctly."""
    problem = re22()

    evaluator = PolarsEvaluator(problem)

    xs = {"x_2": [10], "x_3": [20]}
    for i in range(len(problem.variables) - 2):
        if i == 68:
            xs[f"x_1_{i}"] = [1.0]
        else:
            xs[f"x_1_{i}"] = [0.0]

    res = evaluator.evaluate(xs)

    obj_values = [res[obj.symbol][0] for obj in problem.objectives]
    assert np.allclose(obj_values, np.array([421.938, 2]))


@pytest.mark.testproblem
def test_re23():
    """Test that the pressure vessel design problem evaluates correctly."""
    problem = re23()

    evaluator = PolarsEvaluator(problem)

    xs = {"x_1": [50, 11], "x_2": [50, 63], "x_3": [10, 78], "x_4": [10, 187]}
    expected_result = np.array([[2996.845703, 5.9616], [49848.35467, 4266017.057]])

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i])


@pytest.mark.testproblem
def test_re24():
    """Test that the hatch cover design problem evaluates correctly."""
    problem = re24()

    evaluator = PolarsEvaluator(problem)

    xs = {"x_1": [2, 3.3], "x_2": [20, 41.7]}
    expected_result = np.array([[2402, 3.63459881], [5007.3, 3.8568386109]])

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i])


@pytest.mark.testproblem
@pytest.mark.forest_problem
@pytest.mark.gurobipy
def test_forest_problem():
    """Test the forest problem implementation."""
    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=1,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 45654.952)
    assert np.isclose(res.optimal_objectives["f_2"], 1043.729)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 45654.952)
    assert np.isclose(res.optimal_objectives["f_2"], 1043.729)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 29722.469)
    assert np.isclose(res.optimal_objectives["f_2"], 259.236)
    assert np.isclose(res.optimal_objectives["f_3"], 36780.631)

    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=2,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 42937.004)
    assert np.isclose(res.optimal_objectives["f_2"], 1275.250)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 42937.004)
    assert np.isclose(res.optimal_objectives["f_2"], 1275.250)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 17555.857)
    assert np.isclose(res.optimal_objectives["f_2"], -169.233)
    assert np.isclose(res.optimal_objectives["f_3"], 53632.887)

    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=3,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 82195.014)
    assert np.isclose(res.optimal_objectives["f_2"], 994.578)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 82195.014)
    assert np.isclose(res.optimal_objectives["f_2"], 994.578)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 18207.905)
    assert np.isclose(res.optimal_objectives["f_2"], -2014.855)
    assert np.isclose(res.optimal_objectives["f_3"], 152149.555)

    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=4,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 70547.896)
    assert np.isclose(res.optimal_objectives["f_2"], 1120.833)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 70547.896)
    assert np.isclose(res.optimal_objectives["f_2"], 1120.833)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 17379.117)
    assert np.isclose(res.optimal_objectives["f_2"], -1467.016)
    assert np.isclose(res.optimal_objectives["f_3"], 122271.740)

    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=5,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 78183.469)
    assert np.isclose(res.optimal_objectives["f_2"], 961.411)
    assert np.isclose(res.optimal_objectives["f_3"], 100.783)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 75793.429)
    assert np.isclose(res.optimal_objectives["f_2"], 994.566)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 10885.988)
    assert np.isclose(res.optimal_objectives["f_2"], -2202.283)
    assert np.isclose(res.optimal_objectives["f_3"], 154240.330)
