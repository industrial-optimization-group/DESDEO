"""Test related to the external problems."""

import pytest

from desdeo.emo import algorithms
from desdeo.problem.external.core import ProviderRegistry, ProviderResolver
from desdeo.problem.external.pymoo_provider import (
    PymooProblemParams,
    PymooProvider,
    create_pymoo_problem,
)
from desdeo.problem.simulator_evaluator import SimulatorEvaluator


@pytest.mark.external
def test_pymoo_provider():
    """Test the basic operation of the Pymoo problem provider."""
    registry = ProviderRegistry()

    registry.register("pymoo", PymooProvider())

    resolver = ProviderResolver(registry)

    locator = "desdeo://external/pymoo/evaluate"
    params = PymooProblemParams(name="truss2d")

    info = resolver.info(locator, params.model_dump(exclude_none=True))
    obj_symbols = set(info.objective_symbols)
    var_symbols = set(info.variable_symbols)
    constr_symbols = set(info.constraint_symbols)

    xs = {s: [0.5, 0.5, 0.4] for s in var_symbols}

    for _ in range(10):
        res = resolver.evaluate(locator, params.model_dump(exclude_none=True), xs)

    assert obj_symbols.issubset(res)
    assert constr_symbols.issubset(res)


@pytest.mark.external
def test_pymoo_construct_problem():
    """Test that the pymoo provider can be used to construct a DESDEO Problem."""
    name = "dtlz2"
    n_var = 12
    n_obj = 3
    params = PymooProblemParams(name=name, n_var=n_var, n_obj=n_obj)

    problem = create_pymoo_problem(params)

    obj_symbols = [obj.symbol for obj in problem.objectives]
    var_symbols = [var.symbol for var in problem.variables]

    assert len(problem.variables) == n_var
    assert len(problem.objectives) == n_obj
    assert problem.name == name.upper()
    assert [f"f_{i}" for i in range(1, n_obj + 1)] == obj_symbols
    assert [f"x_{i}" for i in range(1, n_var + 1)] == var_symbols
    assert [problem.get_variable(s).lowerbound for s in var_symbols] == n_var * [0.0]
    assert [problem.get_variable(s).upperbound for s in var_symbols] == n_var * [1.0]
    assert [problem.get_objective(s).maximize for s in obj_symbols] == [False] * n_obj
    assert problem.get_ideal_point() == dict.fromkeys(obj_symbols, 0.0)
    assert problem.get_nadir_point() == dict.fromkeys(obj_symbols, 1.0)


@pytest.mark.external
def test_pymoo_problem_evaluate():
    """Test that the pymoo problems can be evaluated."""
    name = "dtlz2"
    n_var = 12
    n_obj = 3
    params = PymooProblemParams(name=name, n_var=n_var, n_obj=n_obj)

    problem = create_pymoo_problem(params)

    var_symbols = {var.symbol for var in problem.variables}
    obj_symbols = {obj.symbol for obj in problem.objectives}
    obj_symbols_min = {f"{obj.symbol}_min" for obj in problem.objectives}

    evaluator = SimulatorEvaluator(problem, params)

    xs_1d = dict.fromkeys(var_symbols, 0.5)

    res_1d = evaluator.evaluate(xs_1d)

    assert (obj_symbols | obj_symbols_min).issubset(res_1d.columns)
    assert res_1d.height == 1

    xs_2d = {s: [0.5, 0.5] for s in var_symbols}

    res_2d = evaluator.evaluate(xs_2d)

    assert (obj_symbols | obj_symbols_min).issubset(res_2d.columns)
    assert res_2d.height == 2

    xs_3d = {s: [0.5, 0.5, 0.5] for s in var_symbols}

    res_3d = evaluator.evaluate(xs_3d)

    assert (obj_symbols | obj_symbols_min).issubset(res_3d.columns)
    assert res_3d.height == 3


@pytest.mark.external
def test_w_emo():
    """Test that external (at least pymoo) problems work with EMO methods."""
    name = "dtlz2"
    n_var = 3
    n_obj = 2
    params = PymooProblemParams(name=name, n_var=n_var, n_obj=n_obj)

    problem = create_pymoo_problem(params)

    solver, extras = algorithms.emo_constructor(emo_options=algorithms.nsga3_options(), problem=problem)

    solver()
