"""Tests related to the sympy evaluator."""

import numpy.testing as npt
import pytest

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    FormatEnum,
    MathParser,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    ScalarizationFunction,
    SympyEvaluator,
    Variable,
    VariableTypeEnum,
)
from desdeo.problem.sympy_evaluator import SympyEvaluatorError
from desdeo.problem.testproblems import binh_and_korn, river_pollution_problem, zdt1
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

    f_1_res = 5.205
    npt.assert_almost_equal(res["f_1"], f_1_res)
    npt.assert_almost_equal(res["f_1_min"], -f_1_res)

    f_2_res = 2.92703406574689
    npt.assert_almost_equal(res["f_2"], f_2_res)
    npt.assert_almost_equal(res["f_2_min"], -f_2_res)

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
        ws["f_1"] * -f_1_res + ws["f_2"] * -f_2_res + ws["f_3"] * -f_3_res + ws["f_4"] * -f_4_res + ws["f_5"] * f_5_res,
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


def _objective(symbol: str, func: list) -> Objective:
    return Objective(
        name=symbol,
        symbol=symbol,
        func=func,
        maximize=False,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )


def _problem(**kwargs) -> Problem:
    kwargs.setdefault("objectives", [_objective("f_1", ["Add", "x", 1])])
    return Problem(
        name="Chained elements",
        description="Elements defined in terms of earlier elements of the same kind.",
        variables=[
            Variable(
                name="x",
                symbol="x",
                variable_type=VariableTypeEnum.real,
                lowerbound=0.0,
                upperbound=10.0,
                initial_value=1.0,
            )
        ],
        **kwargs,
    )


@pytest.mark.sympy
def test_objective_may_reference_earlier_objective():
    """An objective can be defined in terms of an objective declared before it.

    Expressions of the same kind used not to be substituted into each other at all, so
    the reference survived into ``sympy.lambdify``, which closed over it and returned an
    unevaluated expression (``2*f_1``) in place of a number.
    """
    problem = _problem(objectives=[_objective("f_1", ["Add", "x", 1]), _objective("f_2", ["Multiply", 2, "f_1"])])

    values = SympyEvaluator(problem).evaluate({"x": 3.0})

    npt.assert_allclose(values["f_1"], 4.0)
    npt.assert_allclose(values["f_2"], 8.0)


@pytest.mark.sympy
def test_scalarization_may_reference_earlier_scalarization():
    """A scalarization function can be defined in terms of one declared before it."""
    problem = _problem(
        scalarization_funcs=[
            ScalarizationFunction(name="s_1", symbol="s_1", func=["Add", "x", 1]),
            ScalarizationFunction(name="s_2", symbol="s_2", func=["Multiply", 2, "s_1"]),
        ]
    )

    values = SympyEvaluator(problem).evaluate({"x": 3.0})

    npt.assert_allclose(values["s_1"], 4.0)
    npt.assert_allclose(values["s_2"], 8.0)


@pytest.mark.sympy
def test_unresolvable_reference_raises():
    """A reference that cannot be resolved is an error, not a symbolic result.

    Only backward references resolve, so an objective defined in terms of one declared
    after it has nothing to substitute.
    """
    problem = _problem(objectives=[_objective("f_1", ["Multiply", 2, "f_2"]), _objective("f_2", ["Add", "x", 1])])

    with pytest.raises(SympyEvaluatorError, match="f_2"):
        SympyEvaluator(problem)


@pytest.mark.sympy
def test_constraint_may_reference_scalarization():
    """Constraints are resolved last, so a constraint may reference a scalarization function.

    The scenario tools generate exactly this: aggregating a scalarization function with
    ``add_worst_case_robust`` bounds each per-leaf scalarization in a constraint.  The
    sympy evaluator used to resolve constraints before scalarization functions, leaving
    the reference unsubstituted.
    """
    problem = _problem(
        scalarization_funcs=[ScalarizationFunction(name="s_1", symbol="s_1", func=["Add", "x", 1])],
        constraints=[Constraint(name="c_1", symbol="c_1", func=["Add", "s_1", -10], cons_type=ConstraintTypeEnum.LTE)],
    )

    values = SympyEvaluator(problem).evaluate({"x": 3.0})

    npt.assert_allclose(values["s_1"], 4.0)
    npt.assert_allclose(values["c_1"], -6.0)
