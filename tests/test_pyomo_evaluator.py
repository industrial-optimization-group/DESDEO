"""Tests for testing the PyomoEvaluator."""
from desdeo.problem.pyomo_evaluator import PyomoEvaluator
from desdeo.problem import binh_and_korn, ExtraFunction
from pyomo.environ import Objective
import pytest


@pytest.fixture
def binh_and_korn_w_extra():
    """Defines a variant of the Bing and Korn function with extra functions."""
    problem = binh_and_korn()
    extra_1 = ExtraFunction(name="Extra 1", symbol="extr_1", func="x_1 + x_2")
    extra_2 = ExtraFunction(name="Extra 2", symbol="extr_2", func="x_2 + x_1")

    return problem.model_copy(
        update={
            "extra_funcs": [extra_1, extra_2],
        }
    )


def test_w_binh_and_korn(binh_and_korn_w_extra):
    """Tests the evalutor with the Binh and Korn problem."""
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

    expr = getattr(evaluator.model, "x_1") + getattr(evaluator.model, "x_2") * getattr(evaluator.model, "extr_1")

    evaluator.model.new_thing = Objective(expr=expr, name="lol")
    print()
