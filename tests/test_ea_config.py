"""Tests for Evolutionary Algorithms."""

from contextlib import suppress

import polars as pl
import pytest

from desdeo.emo import algorithms
from desdeo.problem.testproblems import (
    dtlz2,
    momip_ti2,
    river_pollution_problem,
)


@pytest.mark.ea
def test_nsga3_dtlz2():
    """Test whether the NSGA-III algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.nsga3_options())

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front
    median = norm.median()
    assert isinstance(median, float)
    assert median < 1.1


@pytest.mark.ea
def test_rvea_dtlz2():
    """Test whether the RVEA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.rvea_options())

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front
    median = norm.median()
    assert isinstance(median, float)
    assert median < 1.1


@pytest.mark.ea
def test_ibea_dtlz2():
    """Test whether the IBEA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.ibea_options())

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front
    median = norm.median()
    assert isinstance(median, float)
    assert median < 1.1


@pytest.mark.ea
def test_mixed_integer_nsga3():
    """Test whether the mixed-integer NSGA-III variant can be initialized and run as a whole."""
    problem = momip_ti2()
    with suppress(NotImplementedError):
        solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.nsga3_mixed_integer_options())
        _ = solver()


@pytest.mark.ea
def test_nsga3_river():
    """Test whether the 'default' NSGA-III variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.nsga3_options())


    _ = solver()


@pytest.mark.ea
def test_mixed_integer_rvea():
    """Test whether the mixed-integer RVEA variant can be initialized and run as a whole."""
    problem = momip_ti2()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.rvea_mixed_integer_options())

    _ = solver()


@pytest.mark.ea
def test_rvea_river():
    """Test whether the 'default' RVEA variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.rvea_options())

    _ = solver()


@pytest.mark.ea
def test_mixed_integer_ibea():
    """Test whether the mixed-integer IBEA variant can be initialized and run as a whole."""
    problem = momip_ti2()
    with suppress(NotImplementedError):
        solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.ibea_mixed_integer_options())
        _ = solver()


@pytest.mark.ea
def test_ibea_river():
    """Test whether the 'default' IBEA variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.ibea_options())

    _ = solver()


# Other tests are covered by test_ea.py
