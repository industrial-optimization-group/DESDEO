"""Tests related to explainers."""

import os
import sys

import numpy as np
import polars as pl
import pytest
import shap
import cvxpy as cp
import sklearn
from scipy.spatial import cKDTree
from scipy.spatial.distance import euclidean
from itertools import combinations

from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import LHSGenerator
from desdeo.explanations.explainer import BlackBox, ShapExplainer
from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import numpy_array_to_objective_dict, objective_dict_to_numpy_array
from desdeo.problem.evaluator import find_closest_points
from desdeo.problem.testproblems import simple_data_problem
from desdeo.tools import ProximalSolver
from desdeo.tools.patterns import Publisher


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


@pytest.mark.explainer
def test_explainer():
    """Testing..."""
    rng = np.random.default_rng(seed=1)
    n = 100
    x1 = rng.uniform(0, 10, n)
    x2 = rng.uniform(0, 10, n)
    x3 = rng.uniform(0, 10, n)
    dummy_data = pl.DataFrame({"z1": x1, "z2": x2, "z3": x3, "f1": x1 + x2 + x3, "f2": x1 - x2 - x3, "f3": x3 - x2})

    class Model:
        def __init__(self, problem_data, input_symbols, output_symbols):
            self.data = problem_data
            self.input_symbols = input_symbols
            self.output_symbols = output_symbols
            self.input_array = self.data[self.input_symbols].to_numpy()
            self.output_array = self.data[self.output_symbols].to_numpy()
            self.to_output_tree = cKDTree(self.input_array)
            self.to_input_tree = cKDTree(self.output_array)
            # self.explainer = shap.Explainer(self.evaluate, masker=self.input_array)
            self.explainer = None

        def setup_explainer(self, background_data):
            self.explainer = shap.Explainer(
                self.evaluate,
                masker=background_data[self.input_symbols].to_numpy(),
            )

        def evaluate(self, evaluate_array: np.ndarray):
            _, indices = self.to_output_tree.query(evaluate_array)

            return self.output_array[indices]

        def inverse_evaluate(self, evaluate_array: np.ndarray):
            _, indices = self.to_input_tree.query(evaluate_array)

            return self.input_array[indices]

        def explain_input(self, to_be_explained):
            _to_be_explained = to_be_explained[self.input_symbols].to_numpy()

            return self.explainer(_to_be_explained)

    model = Model(problem_data=dummy_data, input_symbols=["z1", "z2", "z3"], output_symbols=["f1", "f2", "f3"])

    # 1. DM gives zs and gets result fs
    z1 = 10
    z2 = 2
    z3 = 4
    zs = pl.DataFrame({"z1": z1, "z2": z2, "z3": z3})
    fs = pl.DataFrame({"f1": z1 + z2 + z3, "f2": z1 - z2 - z3, "f3": z3 - z2})

    def generate_background(data, target):
        # Number of data points and features
        n, m = data.shape
        M = data.max(axis=0) * 10000

        # Create a binary variable for each data point
        x = cp.Variable(n, boolean=True)
        z = cp.Variable(m)
        phi = cp.Variable((n, m))

        objective = cp.sum_squares(z - target)

        # Define the constraints
        constraints = [
            *[cp.sum(phi[:, col]) == cp.sum(cp.multiply(x, data[:, col])) for col in range(m)],
            *[phi[:, col] <= cp.multiply(M[col], x) for col in range(m)],
            *[phi[:, col] <= z[col] for col in range(m)],
            *[phi[:, col] >= z[col] - cp.multiply(M[col], 1 - x) for col in range(m)],
            phi >= 0,
            cp.sum(x) >= 2,
        ]

        # Create the problem
        problem = cp.Problem(cp.Minimize(objective), constraints)

        # Solve the problem
        problem.solve(verbose=True, solver="SCIP")

        # Get the selected subset
        selected_subset = [i for i in range(n) if x.value[i] == 1]
        selected_data = data[selected_subset]

        print("Selected subset indices:", selected_subset)
        print("Selected subset:\n", selected_data)
        print("Average of selected subset:", np.mean(selected_data, axis=0))

        return selected_subset

    # 2. Generate background based on fs
    # 3. Find outputs that are close to fs
    target = np.array([z1, z2, z3])
    background_subset = generate_background(dummy_data[["f1", "f2", "f3"]].to_numpy(), target)

    model.setup_explainer(background_data=pl.DataFrame(dummy_data[background_subset]))

    shaps = model.explain_input(pl.DataFrame({"z1": z1, "z2": z2, "z3": z3}))

    print()
