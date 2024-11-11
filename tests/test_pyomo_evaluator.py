"""Tests for testing the PyomoEvaluator."""

import numpy.testing as npt
import pyomo.environ as pyomo
import pytest

from desdeo.problem import (
    ExtraFunction,
    ScalarizationFunction,
    binh_and_korn,
)
from desdeo.problem.pyomo_evaluator import PyomoEvaluator


@pytest.fixture
def binh_and_korn_w_extra():
    """Defines a variant of the Bing and Korn function with extra functions and scalarizations."""
    problem = binh_and_korn()
    extra_1 = ExtraFunction(name="Extra 1", symbol="extr_1", func="x_1 + x_2")
    extra_2 = ExtraFunction(name="Extra 2", symbol="extr_2", func="x_2 - x_1")

    scal_1 = ScalarizationFunction(name="scal 1", symbol="s_1", func="x_1 + 2.4*x_2 - x_1")
    scal_2 = ScalarizationFunction(name="scal 2", symbol="s_2", func="x_2 + x_2 - 3*x_1")

    return problem.model_copy(update={"extra_funcs": [extra_1, extra_2], "scalarization_funcs": [scal_1, scal_2]})


@pytest.mark.pyomo
def test_w_binh_and_korn(binh_and_korn_w_extra):
    """Tests the initialization of the evaluator with the Binh and Korn problem."""
    problem = binh_and_korn_w_extra
    evaluator = PyomoEvaluator(problem)

    # has all symbols
    for var in problem.variables:
        assert hasattr(evaluator.model, var.symbol)

    # has all constants
    for con in problem.constants:
        assert hasattr(evaluator.model, con.symbol)

    # has all extras
    for extra in problem.extra_funcs:
        assert hasattr(evaluator.model, extra.symbol)

    # has all objectives, including the _min ones.
    for obj in problem.objectives:
        assert hasattr(evaluator.model, obj.symbol)
        assert hasattr(evaluator.model, f"{obj.symbol}_min")

    # has all constraints
    for cons in problem.constraints:
        assert hasattr(evaluator.model, cons.symbol)
        assert isinstance(getattr(evaluator.model, cons.symbol), pyomo.Constraint)

    # has all scalarizations
    for scal in problem.scalarization_funcs:
        assert hasattr(evaluator.model, scal.symbol)

    evaluator.set_optimization_target("f_1")

    assert hasattr(evaluator.model, "f_1_objective")
    assert isinstance(getattr(evaluator.model, "f_1_objective"), pyomo.Objective)  # noqa: B009
    assert getattr(evaluator.model, "f_1_objective").active  # noqa: B009


@pytest.mark.pyomo
def test_get_values_w_binh_and_korn(binh_and_korn_w_extra):
    """Test that the problem evaluates correctly."""
    problem = binh_and_korn_w_extra
    evaluator = PyomoEvaluator(problem)

    input_1 = {"x_1": [2], "x_2": [8]}

    evaluator.evaluate(input_1)

    res_dict = evaluator.evaluate(input_1)

    assert res_dict["x_1"] == 2
    assert res_dict["x_2"] == 8

    npt.assert_almost_equal(res_dict["f_1"], 272)
    npt.assert_almost_equal(res_dict["f_2"], 18)

    assert res_dict["c_1"] == 4
    assert res_dict["c_2"] == 5

    npt.assert_almost_equal(res_dict["g_1"], 48)
    npt.assert_almost_equal(res_dict["g_2"], -149.3)

    npt.assert_almost_equal(res_dict["extr_1"], 10)
    npt.assert_almost_equal(res_dict["extr_2"], 6)

    npt.assert_almost_equal(res_dict["s_1"], 19.2)
    npt.assert_almost_equal(res_dict["s_2"], 10)
