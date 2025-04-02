"""Tests related to explainers."""

import pytest

from desdeo.emo.operators.generator import LHSGenerator
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.explanations.explainer import BlackBox, ShapExplainer
from desdeo.problem.testproblems import simple_data_problem
from desdeo.mcdm import rpm_solve_solutions
from desdeo.tools import ProximalSolver
from desdeo.problem import numpy_array_to_objective_dict, objective_dict_to_numpy_array
from desdeo.tools.patterns import Publisher

import polars as pl
import numpy as np


@pytest.mark.explainer
def test_blackbox():
    """Test the black box works as expected."""
    problem = simple_data_problem()

    def evaluator(reference_point: np.ndarray, problem, solver):
        results = rpm_solve_solutions(
            problem=problem,
            reference_point=numpy_array_to_objective_dict(problem=problem, numpy_array=reference_point),
            solver=solver,
        )
        return np.array(
            [objective_dict_to_numpy_array(problem=problem, objective_dict=res.optimal_objectives) for res in results]
        )

    bb = BlackBox(problem, evaluator, {"problem": problem, "solver": ProximalSolver})

    # single input
    ref_point = objective_dict_to_numpy_array(problem, {"g_1": 2500.0, "g_2": 7.5, "g_3": -30.0})

    res = bb.evaluate(ref_point)

    assert res.shape == (1, len(problem.objectives) + 1, len(problem.objectives))  # num inputs, k+1, num objectives

    # multi input
    ref_point_multi = np.array([[2500.0, 7.5, -30.0], [1500.0, 2.0, -50], [2500.0, 7.5, -30.0]])

    res = bb.evaluate(ref_point_multi)

    assert res.shape == (
        len(ref_point_multi),
        len(problem.objectives) + 1,
        len(problem.objectives),
    )  # num inputs, k+1, num objectives


@pytest.mark.explainer
def test_shap_explainer():
    """Test the SHAP explainer."""
    problem = simple_data_problem()

    def evaluator(reference_point: np.ndarray, problem, solver):
        results = rpm_solve_solutions(
            problem=problem,
            reference_point=numpy_array_to_objective_dict(problem=problem, numpy_array=reference_point),
            solver=solver,
        )
        return np.array(objective_dict_to_numpy_array(problem=problem, objective_dict=results[0].optimal_objectives))

    bb = BlackBox(problem, evaluator, {"problem": problem, "solver": ProximalSolver})

    publisher = Publisher()
    emo_evaluator = EMOEvaluator(problem, publisher=publisher)
    generator = LHSGenerator(problem, emo_evaluator, n_points=10, seed=0, publisher=publisher)

    missing_data = generator.do()[1][[objective.symbol for objective in problem.objectives]]

    explainer = ShapExplainer(bb, objective_dict_to_numpy_array(problem, problem.get_nadir_point()))

    res = explainer.shap_values(np.array([2600.0, 5.5, -25.0]))

    print()
