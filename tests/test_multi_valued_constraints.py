"""Tests related to multi-valued constraints."""

<<<<<<< HEAD
import numpy as np
=======
>>>>>>> 761c90fb801746ede493a915ab18d85551c0a060
import polars as pl
import polars.testing as plt
import pytest

from desdeo.problem import GurobipyEvaluator, PolarsEvaluator, PyomoEvaluator, SympyEvaluator
from desdeo.problem.sympy_evaluator import SympyEvaluatorError
from desdeo.problem.testproblems import multi_valued_constraint_problem
<<<<<<< HEAD
from desdeo.tools import (
    NevergradGenericSolver,
    PyomoBonminSolver,
    PyomoGurobiSolver,
    PyomoIpoptSolver,
    ScipyDeSolver,
    ScipyMinimizeSolver,
)
from desdeo.tools.generics import SolverError
=======
>>>>>>> 761c90fb801746ede493a915ab18d85551c0a060


def test_with_polars_evaluator():
    """Test multi-valued constraints with the Polars evaluator."""
    problem = multi_valued_constraint_problem()

    evaluator = PolarsEvaluator(problem)

    x_input = pl.DataFrame({"X": [[[1.0], [2.0]], [[2.0], [1.0]], [[-4.0], [4.0]]], "y": [-1.0, 0.0, 1.0]})

    res = evaluator.evaluate(x_input)

    expected = pl.DataFrame(
        {
            "f_1": [6.0, 5.0, 33.0],
            "f_2": [6.0, 1.0, 45.0],
            "g_1": [0.0, 3.0, 19.0],
        }
    )

    g_vals = [
        [[-1.0], [-5.0]],
        [[1.0], [-4.0]],
        [[-8.0], [-4.0]],
    ]
    expected = expected.with_columns(pl.Series("G", g_vals, dtype=pl.Array(pl.Float64, (2, 1))))

    assert "G" in res
    assert res.schema["G"] == pl.Array(pl.Float64, (2, 1))

    plt.assert_frame_equal(
        res.select("f_1", "f_2", "g_1", "G"),
        expected,
    )


def test_with_pyomo_evaluator():
    """Test multi-valued constraints with the Pyomo evaluator."""
    problem = multi_valued_constraint_problem()

    evaluator = PyomoEvaluator(problem)

    x_input = {"X": [[[1.0], [2.0]], [[2.0], [1.0]], [[-4.0], [4.0]]], "y": [-1.0, 0.0, 1.0]}

    res = evaluator.evaluate(x_input)

    expected = [
        {
            "X": {(1, 1): 1.0, (2, 1): 2.0},
            "y": -1.0,
            "f_1": 6.0,
            "f_2": 6.0,
            "g_1": 0.0,
            "A": {(1, 1): 1.0, (1, 2): -1.0, (2, 1): -1.0, (2, 2): -2.0},
            "one": 1.0,
            "G": {(1, 1): -1.0, (2, 1): -5.0},
        },
        {
            "X": {(1, 1): 2.0, (2, 1): 1.0},
            "y": 0.0,
            "f_1": 5.0,
            "f_2": 1.0,
            "g_1": 3.0,
            "A": {(1, 1): 1.0, (1, 2): -1.0, (2, 1): -1.0, (2, 2): -2.0},
            "one": 1.0,
            "G": {(1, 1): 1.0, (2, 1): -4.0},
        },
        {
            "X": {(1, 1): -4.0, (2, 1): 4.0},
            "y": 1.0,
            "f_1": 33.0,
            "f_2": 45.0,
            "g_1": 19.0,
            "A": {(1, 1): 1.0, (1, 2): -1.0, (2, 1): -1.0, (2, 2): -2.0},
            "one": 1.0,
            "G": {(1, 1): -8.0, (2, 1): -4.0},
        },
    ]

    assert res == expected


def test_with_sympy_evaluator():
    """Test multi-valued constraints with the Sympy evaluator.

    TODO: fix me!
    """
    problem = multi_valued_constraint_problem()

    with pytest.raises(SympyEvaluatorError):
        # TODO: implement support for tensors
        evaluator = SympyEvaluator(problem)

    # x_input = {"X": [[[1.0], [2.0]], [[2.0], [1.0]], [[-4.0], [4.0]]], "y": [-1.0, 0.0, 1.0]}

    # res = evaluator.evaluate(x_input)


def test_with_gurobipy_evaluator():
    """Test multi-valued constraints with the Gurobipy evaluator.

    TODO: fix me!
    """
    problem = multi_valued_constraint_problem()

    with pytest.raises(NotImplementedError):
        # TODO: implement missing support for tensors and associated operators
        evaluator = GurobipyEvaluator(problem)

    # x_input = {"X": [[[1.0], [2.0]], [[2.0], [1.0]], [[-4.0], [4.0]]], "y": [-1.0, 0.0, 1.0]}

    # res = evaluator.evaluate(x_input)
<<<<<<< HEAD


def test_with_pyomo_solvers():
    """Test that problem with multi-valued constraint works with most Pyomo solvers."""
    problem = multi_valued_constraint_problem()

    solvers = [PyomoBonminSolver, PyomoIpoptSolver, PyomoGurobiSolver]

    for solver_maker in solvers:
        solver = solver_maker(problem)
        res = solver.solve("f_2")

        assert np.shape(res.optimal_variables["X"]) == np.shape(res.constraint_values["G"])

        tol = 1e-6
        g_values = np.array(res.constraint_values["G"])
        ok_mask = (g_values < 0) | (np.abs(g_values) <= tol)

        assert np.all(ok_mask), f"Bad values: {g_values[~ok_mask]}"


def test_with_ng_solvers():
    """Test that problem with multi-valued constraint works with nevergrad solvers.

    TODO: sympy evaluator must first support tensors...
    """
    problem = multi_valued_constraint_problem()

    with pytest.raises(SympyEvaluatorError):
        # TODO: implement support for tensors for sympyevaluator first
        solver = NevergradGenericSolver(problem)


def test_with_scipy_solvers():
    """Test that problem with multi-valued constraint works with scipy solvers."""
    problem = multi_valued_constraint_problem()

    solvers = [ScipyDeSolver, ScipyMinimizeSolver]

    for solver_maker in solvers:
        with pytest.raises(SolverError):
            # TODO: scipy solvers lacking support for tensors in general
            solver = solver_maker(problem)
=======
>>>>>>> 761c90fb801746ede493a915ab18d85551c0a060
