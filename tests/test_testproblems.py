"""Test some of the test problems found in DESDEO."""

import numpy as np
import pytest

from desdeo.problem import GenericEvaluator, dtlz2, forest_problem
from desdeo.tools import GurobipySolver


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


@pytest.mark.forest_problem
def test_forest_problem():
    """Test the forest problem implementation."""
    problem = forest_problem(holding=1, comparing=True)
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

    problem = forest_problem(holding = 2, comparing=True)
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

    problem = forest_problem(holding = 3, comparing=True)
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

    problem = forest_problem(holding = 4, comparing=True)
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

    problem = forest_problem(holding = 5, comparing=True)
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
