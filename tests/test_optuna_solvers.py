"""Tests for the optuna solver interfaces."""

import pytest

from desdeo.problem import ScalarizationFunction
from desdeo.problem.testproblems import binh_and_korn
from desdeo.tools import add_epsilon_constraints

from optuna_solver_interfaces import OptunaSolver, OptunaOptions
from pymoo.problems import get_problem
import numpy as np


@pytest.mark.optuna
def test_optuna_with_constraints(results_on: bool = False):
    """Tests the Optuna solver with constraints."""
    problem = binh_and_korn((False, False))

    target = "first"
    problem = problem.add_scalarization(
        ScalarizationFunction(
            name=target,
            symbol=target,
            func="1*f_2",
            is_linear=problem.is_linear,
            is_convex=problem.is_convex,
            is_twice_differentiable=problem.is_twice_differentiable,
        )
    )


    solver = OptunaSolver(problem)

    results = solver.solve(target)

    if results_on:
        print("optuna results:",results)
        print("OPTUNA optimal variables:",results.optimal_variables)
        print("OPTUNA optimal objectives:", results.optimal_objectives)
        true_solution = {"x_1": 5.0, "x_2": 3.0}
        print("true_solution:", true_solution)
        l1_error = sum(abs(true_solution[k] - results.optimal_variables[k]) for k in true_solution)
        print("L^1 error norm", l1_error)

    """ comparison of solution to Pymoo's solution and calculating the difference of solutions
        in L^1 error norm
    """
    problem_pareto = get_problem("bnh")
    arr = np.array([1.0, 2.0])
    eps_values = np.linspace(0.0, 136.0,num=10)
    obj_values = []
    var_values = []
    pareto_front_l1 = 0
    for eps in eps_values:
        # epsilons = {"obj2": eps}
        eps_symbols = {"f_1": "f_1_eps", "f_2": "f_2_eps"}
        objective_symbol = "f_2"
        epsilons = {"f_1": eps, "f_2": None}
        # target = "obj1_target"

        problem_w_cons, target, eps_symbols = add_epsilon_constraints(
            problem,
            "eps_objective",
            eps_symbols,
            objective_symbol,
            epsilons
        )
        options = OptunaOptions(num_jobs=1, budget=40)
        solver = OptunaSolver(problem_w_cons, options=options)

        res = solver.solve(target)

        ob_values = np.array([res.optimal_objectives["f_1"],res.optimal_objectives["f_2"]])
        obj_values.append(ob_values)
        values = np.array([res.optimal_variables["x_1"], res.optimal_variables["x_2"]])
        var_values.append(values)

        pareto_front_l1 = pareto_front_l1 + np.sum(abs(problem_pareto.evaluate(values)[0]-ob_values))

    print("pareto_front_l1_error_norm", pareto_front_l1)