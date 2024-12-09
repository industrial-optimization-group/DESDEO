"""Tests related to explainers."""

import pytest

from desdeo.emo.operators.generator import LHSGenerator
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.explanations.explainer import BlackBox, ShapExplainer
from desdeo.problem.testproblems import dtlz2
from desdeo.mcdm import rpm_solve_solutions
from desdeo.tools import PyomoBonminSolver
from desdeo.tools.patterns import Publisher

import polars as pl


@pytest.mark.explainer
def test_blackbox():
    """Test the black box works as expected."""
    problem = dtlz2(5, 3)

    def evaluator(reference_point, problem, solver):
        results = rpm_solve_solutions(problem=problem, reference_point=reference_point, solver=solver)
        return pl.DataFrame([res.optimal_objectives for res in results])

    bb = BlackBox(evaluator, {"problem": problem, "solver": PyomoBonminSolver})

    ref_point = {"f_1": 0.5, "f_2": 0.7, "f_3": 0.4}

    res = bb.evaluate(ref_point)

    assert "f_1" in res
    assert "f_2" in res
    assert "f_3" in res


@pytest.mark.explainer
def test_shap_explainer():
    """Test the SHAP explainer."""
    problem = dtlz2(5, 3)

    def evaluator(reference_point, problem, solver):
        results = rpm_solve_solutions(problem=problem, reference_point=reference_point, solver=solver)
        return pl.DataFrame([res.optimal_objectives for res in results])

    bb = BlackBox(evaluator, {"problem": problem, "solver": PyomoBonminSolver})

    publisher = Publisher()
    emo_evaluator = EMOEvaluator(problem, publisher=publisher)
    generator = LHSGenerator(problem, emo_evaluator, n_points=10000, seed=0, publisher=publisher)

    missing_data = generator.do()[1][[objective.symbol for objective in problem.objectives]]

    explainer = ShapExplainer(bb, missing_data)

    print()
