"""Tests related to the sympy evaluator."""

import numpy.testing as npt
import pytest

from desdeo.problem import (
    FormatEnum,
    MathParser,
    SympyEvaluator,
    binh_and_korn,
    river_pollution_problem,
    zdt1,
)
from desdeo.tools import add_asf_diff, add_weighted_sums


@pytest.mark.sympy
def test_initialization():
    """Tests the correct initialization of the evaluator."""
    parser = MathParser(to_format=FormatEnum.sympy)
    problem = binh_and_korn(maximize=(False, True))
    evaluator = SympyEvaluator(problem)

    # variables symbols
    assert evaluator.variable_symbols == [var.symbol for var in problem.variables]

    # constants
    constant_symbols = [s.symbol for s in problem.constants]
    constant_values = [s.value for s in problem.constants]
    for i, t in enumerate(d := evaluator.constant_expressions):
        assert t == constant_symbols[i]
        npt.assert_almost_equal(d[t].evalf(), constant_values[i])

    # extra expressions
    assert evaluator.extra_expressions is None

    # objective functions
    objective_symbols = [obj.symbol for obj in problem.objectives]
    objective_exprs = [obj.func for obj in problem.objectives]
    for i, t in enumerate(d := evaluator.objective_expressions):
        assert t == objective_symbols[i]
        assert d[t] == parser.parse(objective_exprs[i])

    # constraints
    constraint_symbols = [con.symbol for con in problem.constraints]
    constraint_exprs = [con.func for con in problem.constraints]
    for i, t in enumerate(d := evaluator.constraint_expressions):
        assert t == constraint_symbols[i]
        assert d[t] == parser.parse(constraint_exprs[i])

    # scalarization
    assert evaluator.scalarization_expressions is None

    # add scal, initialize again
    assert problem.scalarization_funcs is None

    rp = {"f_1": 2.5, "f_2": 5.2}
    problem_w_asf, target = add_asf_diff(problem, "target", rp)

    assert len(problem_w_asf.scalarization_funcs) == 1

    evaluator_w_asf = SympyEvaluator(problem_w_asf)

    assert next(iter(evaluator_w_asf.scalarization_expressions.keys())) == target
    assert evaluator_w_asf.scalarization_expressions[target] == parser.parse(problem_w_asf.scalarization_funcs[0].func)

    # extra
    problem_w_extras = zdt1(number_of_variables=10)

    evaluator_w_extras = SympyEvaluator(problem_w_extras)

    extra_symbols = [extra.symbol for extra in problem_w_extras.extra_funcs]
    extra_exprs = [extra.func for extra in problem_w_extras.extra_funcs]
    for i, t in enumerate(d := evaluator_w_extras.extra_expressions):
        assert t == extra_symbols[i]
        assert d[t] == parser.parse(extra_exprs[i])


@pytest.mark.sympy
def test_evaluate():
    """Test that the evaluator evaluates correctly."""
    problem = river_pollution_problem()
    evaluator = SympyEvaluator(problem)

    xs = {"x_1": 0.5, "x_2": 0.6}

    res = evaluator.evaluate(xs)

    for s in problem.get_all_symbols():
        assert s in res

    f_1_res = -5.205
    npt.assert_almost_equal(res["f_1"], f_1_res)
    npt.assert_almost_equal(res["f_1_min"], f_1_res)

    f_2_res = -2.92703406574689
    npt.assert_almost_equal(res["f_2"], f_2_res)
    npt.assert_almost_equal(res["f_2_min"], f_2_res)

    f_3_res = 7.36476190476191
    npt.assert_almost_equal(res["f_3"], f_3_res)
    npt.assert_almost_equal(res["f_3_min"], -f_3_res)

    f_4_res = -0.355068493150685
    npt.assert_almost_equal(res["f_4"], f_4_res)
    npt.assert_almost_equal(res["f_4_min"], -f_4_res)

    f_5_res = 0.15
    npt.assert_almost_equal(res["f_5"], f_5_res)
    npt.assert_almost_equal(res["f_5_min"], f_5_res)

    # scalarization
    ws = {"f_1": 0.1, "f_2": 0.4, "f_3": 0.2, "f_4": 0.05, "f_5": 0.25}
    problem_w_sum, target = add_weighted_sums(problem, "target", ws)
    evaluator_sum = SympyEvaluator(problem_w_sum)

    res = evaluator_sum.evaluate(xs)

    for s in problem_w_sum.get_all_symbols():
        assert s in res

    npt.assert_almost_equal(
        res[target],
        ws["f_1"] * f_1_res + ws["f_2"] * f_2_res + ws["f_3"] * -f_3_res + ws["f_4"] * -f_4_res + ws["f_5"] * f_5_res,
    )

    # constants and constraints
    problem = binh_and_korn(maximize=(True, False))
    evaluator = SympyEvaluator(problem)
    xs = {"x_1": 2.5, "x_2": 3.2}

    res = evaluator.evaluate(xs)

    # minus constants
    for s in problem.get_all_symbols():
        if s in ["c_1", "c_2"]:
            continue
        assert s in res

    npt.assert_almost_equal(res["f_1"], -65.96)
    npt.assert_almost_equal(res["f_1_min"], 65.96)

    npt.assert_almost_equal(res["f_2"], 9.49)
    npt.assert_almost_equal(res["f_2_min"], 9.49)

    npt.assert_almost_equal(res["g_1"], -8.51)
    npt.assert_almost_equal(res["g_2"], -60.99)
