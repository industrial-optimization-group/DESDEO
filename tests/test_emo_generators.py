"""Tests for SeededHybridGenerator."""

import polars as pl
import pytest

from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import SeededHybridGenerator
from desdeo.problem.testproblems import dtlz2
from desdeo.tools.patterns import Publisher


@pytest.mark.ea
def test_seeded_hybrid_generator_basic():
    """SeededHybridGenerator returns correct shapes and includes the seed."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    publisher = Publisher()
    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)

    seed_vals = {sym: [0.5] for sym in [v.symbol for v in problem.variables]}
    seed_solution = pl.DataFrame(seed_vals)

    gen = SeededHybridGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        verbosity=1,
        n_points=10,
        seed_solution=seed_solution,
        perturb_fraction=0.2,  # 2 seeded/perturbed (incl seed), 8 random
        sigma=0.05,
        flip_prob=0.0,
        seed=0,
    )

    solutions, outputs = gen.do()

    # shapes
    assert solutions.shape == (10, len(problem.variables))
    assert outputs.shape[0] == 10

    # columns match variables
    assert set(solutions.columns) == {v.symbol for v in problem.variables}

    # seed is included as the first row
    assert solutions.head(1).equals(seed_solution.select(solutions.columns))

    # all solutions within bounds
    for v in problem.variables:
        col = solutions[v.symbol]
        assert col.min() >= v.lowerbound
        assert col.max() <= v.upperbound
