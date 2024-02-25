"""Test for adding and utilizing scalarization functions."""
import numpy as np
import pytest

from desdeo.problem import GenericEvaluator, river_pollution_problem, simple_test_problem
from desdeo.tools.scalarization import (
    add_lte_constraints,
    add_scalarization_function,
    create_asf,
    create_epsilon_constraints_json,
    create_weighted_sums,
)
from desdeo.tools.scipy_solver_interfaces import create_scipy_minimize_solver


@pytest.fixture
def river_w_fake_ideal_and_nadir():
    """Adds an ideal and nadir point to the river pollution problem for testing purposes."""
    problem = river_pollution_problem()
    return problem.model_copy(
        update={
            "objectives": [
                objective.model_copy(update={"ideal": 0.5, "nadir": 5.5}) for objective in problem.objectives
            ]
        }
    )


def test_create_asf(river_w_fake_ideal_and_nadir):
    """Tests that the achievement scalarization function is created correctly."""
    problem = river_w_fake_ideal_and_nadir

    # min, min, max, max, min
    asf = create_asf(problem, {"f_1": 1, "f_2": 2, "f_3": 3, "f_4": 2, "f_5": 1}, delta=0.1, rho=2.2)

    assert asf == (
        "Max((f_1_min - 1) / (5.5 - (0.5 - 0.1)), (f_2_min - 2) / (5.5 - (0.5 - 0.1)), "
        "(f_3_min - 3 * -1) / (-5.5 - (-0.5 - 0.1)), (f_4_min - 2 * -1) / (-5.5 - (-0.5 - 0.1)), "
        "(f_5_min - 1) / (5.5 - (0.5 - 0.1))) + 2.2 * (f_1_min / (5.5 - (0.5 - 0.1)) + f_2_min / (5.5 - (0.5 - 0.1)) "
        "+ f_3_min / (-5.5 - (-0.5 - 0.1)) + f_4_min / (-5.5 - (-0.5 - 0.1)) + f_5_min / (5.5 - (0.5 - 0.1)))"
    )


def test_create_ws():
    """Tests that the weighted sum scalarization is added correctly."""
    problem = simple_test_problem()
    ws = {"f_1": 1, "f_2": 2, "f_3": 1, "f_4": 3, "f_5": 7.2}

    sf = create_weighted_sums(problem, ws)

    assert sf == "(1 * f_1_min) + (2 * f_2_min) + (1 * f_3_min) + (3 * f_4_min) + (7.2 * f_5_min)"


def test_add_scalarization_function(river_w_fake_ideal_and_nadir):
    """Tests that scalarization functions are added correctly."""
    problem = river_w_fake_ideal_and_nadir

    ws = {"f_1": 1, "f_2": 2, "f_3": 1, "f_4": 3, "f_5": 5}
    wsf = create_weighted_sums(problem, ws)

    ref_point = {"f_1": 1, "f_2": 2, "f_3": 3, "f_4": 4, "f_5": 5}
    asf = create_asf(problem, ref_point)

    problem, symbol_ws = add_scalarization_function(problem, wsf, "WS", name="Weighted sums")
    problem, symbol_asf = add_scalarization_function(problem, asf, "ASF", name="Achievement scalarizing function")

    assert len(problem.scalarizations_funcs) == 2  # there should be two scalarization functions now
    assert problem.scalarizations_funcs[0].name == "Weighted sums"
    assert problem.scalarizations_funcs[1].name == "Achievement scalarizing function"
    assert problem.scalarizations_funcs[0].symbol == symbol_ws
    assert problem.scalarizations_funcs[1].symbol == symbol_asf


@pytest.mark.slow
def test_epsilon_constraint():
    """Tests the epsilon constraint scalarization."""
    problem = simple_test_problem()

    epsilons = {"f_1": 5.0, "f_2": None, "f_3": -4.0, "f_4": 4.3, "f_5": -3}
    eps_target = "f_2"

    sf, cons_exprs = create_epsilon_constraints_json(problem, eps_target, epsilons)

    problem, target = add_scalarization_function(problem, sf, "f_2_eps")

    con_symbols = [f"con_{i}" for i in range(1, len(cons_exprs) + 1)]
    problem_w_cons = add_lte_constraints(problem, cons_exprs, con_symbols)

    solver = create_scipy_minimize_solver(problem_w_cons)

    res = solver(target)

    # check that constraints are ok
    cons_values = [res.constraint_values[s] for s in con_symbols]

    atol = 1e-9
    shifted = np.array(cons_values) - atol

    assert np.all(shifted < 0)
