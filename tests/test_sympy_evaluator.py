"""Tests related to the sympy evaluator."""

import pytest
import sympy as sp
import numpy.testing as npt

from desdeo.problem import SympyEvaluator, binh_and_korn, zdt1
from desdeo.tools import add_achievement_sf_diff


@pytest.mark.sympy
def test_initialization():
    """Tests the correct initialization of the evaluator."""
    problem = binh_and_korn()
    evaluator = SympyEvaluator(problem)

    # variables symbols
    assert evaluator.variable_symbols == [var.symbol for var in problem.variables]

    # constants
    constant_symbols = [s.symbol for s in problem.constants]
    constant_values = [s.value for s in problem.constants]
    for i, t in enumerate(evaluator.constant_expressions):
        assert t[0] == constant_symbols[i]
        npt.assert_almost_equal(t[1].evalf(), constant_values[i])

    # extra expressions
    assert evaluator.extra_expressions is None

    # objective functions
    objective_symbols = [obj.symbol for obj in problem.objectives]
    objective_exprs = [obj.func for obj in problem.objectives]
    for i, t in enumerate(evaluator.objective_expressions):
        assert t[0] == objective_symbols[i]
        assert t[1] == sp.sympify(objective_exprs[i], evaluate=False)

    # constraints
    constraint_symbols = [con.symbol for con in problem.constraints]
    constraint_exprs = [con.func for con in problem.constraints]
    for i, t in enumerate(evaluator.constraint_expressions):
        assert t[0] == constraint_symbols[i]
        assert t[1] == sp.sympify(constraint_exprs[i], evaluate=False)

    # scalarization
    assert evaluator.scalarization_expressions is None

    # add scal, initialize again
    assert problem.scalarization_funcs is None

    rp = {"f_1": 2.5, "f_2": 5.2}
    problem_w_asf, target = add_achievement_sf_diff(problem, "target", rp)

    assert len(problem_w_asf.scalarization_funcs) == 1

    evaluator_w_asf = SympyEvaluator(problem_w_asf)

    assert evaluator_w_asf.scalarization_expressions[0][0] == target
    assert evaluator_w_asf.scalarization_expressions[0][1] == sp.sympify(
        problem_w_asf.scalarization_funcs[0].func, evaluate=False
    )

    # extra
    problem_w_extras = zdt1(number_of_variables=10)

    evaluator_w_extras = SympyEvaluator(problem_w_extras)

    extra_symbols = [extra.symbol for extra in problem_w_extras.extra_funcs]
    extra_exprs = [extra.func for extra in problem_w_extras.extra_funcs]
    for i, t in enumerate(evaluator_w_extras.extra_expressions):
        assert t[0] == extra_symbols[i]
        assert t[1] == sp.sympify(extra_exprs[i], evaluate=False)
