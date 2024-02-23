"""Tests for testing the PyomoEvaluator."""
from desdeo.problem.pyomo_evaluator import PyomoEvaluator
from desdeo.problem import binh_and_korn, ExtraFunction, ScalarizationFunction

import pyomo.environ as pyomo
import pytest


@pytest.fixture
def binh_and_korn_w_extra():
    """Defines a variant of the Bing and Korn function with extra functions and scalarizations."""
    problem = binh_and_korn()
    extra_1 = ExtraFunction(name="Extra 1", symbol="extr_1", func="x_1 + x_2")
    extra_2 = ExtraFunction(name="Extra 2", symbol="extr_2", func="x_2 - x_1")

    scal_1 = ScalarizationFunction(name="scal 1", symbol="s_1", func="x_1 + 2.4*x_2 - x_1")
    scal_2 = ScalarizationFunction(name="scal 2", symbol="s_2", func="x_2 + x_2 - 3*x_1")

    return problem.model_copy(update={"extra_funcs": [extra_1, extra_2], "scalarizations_funcs": [scal_1, scal_2]})


def test_w_binh_and_korn(binh_and_korn_w_extra):
    """Tests the initialization of the evalutor with the Binh and Korn problem."""
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

        # all objectives should be deactivated by default
        assert not getattr(evaluator.model, obj.symbol).active
        assert not getattr(evaluator.model, f"{obj.symbol}_min").active

        assert isinstance(getattr(evaluator.model, obj.symbol), pyomo.Objective)

    # has all constraints
    for cons in problem.constraints:
        assert hasattr(evaluator.model, cons.symbol)
        assert isinstance(getattr(evaluator.model, cons.symbol), pyomo.Constraint)

    # has all scalarizations
    for scal in problem.scalarizations_funcs:
        assert hasattr(evaluator.model, scal.symbol)
        assert isinstance(getattr(evaluator.model, scal.symbol), pyomo.Objective)

        # scalarizations should be deactivated by default
        assert not getattr(evaluator.model, scal.symbol).active
