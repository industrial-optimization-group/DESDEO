"""Tests related to explainers."""

import numpy as np
import polars as pl
import pytest

from desdeo.explanations import ShapExplainer, generate_biased_mean_data


@pytest.mark.explainer
@pytest.mark.slow
def test_explainer():
    """Testing..."""
    rng = np.random.default_rng(seed=1)
    n = 100
    x1 = rng.uniform(0, 10, n)
    x2 = rng.uniform(0, 10, n)
    x3 = rng.uniform(0, 10, n)
    dummy_data = pl.DataFrame({"z1": x1, "z2": x2, "z3": x3, "f1": x1 + x2 + x3, "f2": x1 - x2 - x3, "f3": x3 - x2})

    model = ShapExplainer(problem_data=dummy_data, input_symbols=["z1", "z2", "z3"], output_symbols=["f1", "f2", "f3"])

    # 1. DM gives zs and gets result fs
    z1 = 10
    z2 = 2
    z3 = 4

    # 2. Generate background based on fs
    # 3. Find outputs that are close to fs
    target = np.array([z1, z2, z3])
    background_subset = generate_biased_mean_data(dummy_data[["f1", "f2", "f3"]].to_numpy(), target)

    model.setup(background_data=pl.DataFrame(dummy_data[background_subset]))

    shaps = model.explain_input(pl.DataFrame({"z1": z1, "z2": z2, "z3": z3}))
