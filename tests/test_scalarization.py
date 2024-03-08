"""Test for adding and utilizing scalarization functions."""
import numpy as np
import pytest

from desdeo.problem import ConstraintTypeEnum, river_pollution_problem, simple_test_problem
from desdeo.tools.scalarization import (
    add_lte_constraints,
    add_scalarization_function,
    add_asf_nondiff,
    add_asf_generic_nondiff,
    add_epsilon_constraints,
    create_epsilon_constraints_json,
    add_weighted_sums,
)
from desdeo.tools.scipy_solver_interfaces import create_scipy_minimize_solver


def flatten(nested_list: list) -> list:
    """Flattens a given nested list.

    Args:
        nested_list (list): list to be flattened.

    Returns:
        list: the flattened list.
    """
    flat_list = []
    # Iterate through each element in the nested list
    for element in nested_list:
        # If the element is a list, extend the flat list with the flattened element
        if isinstance(element, list):
            flat_list.extend(flatten(element))
        else:
            # If the element is not a list, append it to the flat list
            flat_list.append(element)
    return flat_list


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


def test_add_asf_nondiff(river_w_fake_ideal_and_nadir):
    """Tests that the achievement scalarization function is added correctly."""
    problem = river_w_fake_ideal_and_nadir

    # min, min, max, max, min
    reference_point = {"f_1": 1.9, "f_2": 2.9, "f_3": 3.1, "f_4": 2.3, "f_5": 1.1}
    problem, target = add_asf_nondiff(problem, symbol="asf", reference_point=reference_point, delta=0.1, rho=2.2)

    assert target == problem.scalarization_funcs[0].symbol
    assert "Max" in flatten(problem.scalarization_funcs[0].func)
    assert 0.1 in flatten(problem.scalarization_funcs[0].func)
    assert 2.2 in flatten(problem.scalarization_funcs[0].func)

    for key, value in reference_point.items():
        assert f"{key}_min" in flatten(problem.scalarization_funcs[0].func)
        assert value in flatten(problem.scalarization_funcs[0].func)


def test_add_asf_generic_nondiff(river_w_fake_ideal_and_nadir):
    """Tests that the generic achievement scalarization function is added correctly."""
    problem = river_w_fake_ideal_and_nadir

    # min, min, max, max, min
    reference_point = {"f_1": 1.9, "f_2": 2.9, "f_3": 3.1, "f_4": 2.3, "f_5": 1.1}
    weights = {"f_1": 9.19, "f_2": 9.2, "f_3": 1.3, "f_4": 3.2, "f_5": 0.11}
    problem, target = add_asf_generic_nondiff(
        problem, symbol="asf", reference_point=reference_point, weights=weights, rho=2.2
    )

    assert target == problem.scalarization_funcs[0].symbol
    assert "Max" in flatten(problem.scalarization_funcs[0].func)
    assert 2.2 in flatten(problem.scalarization_funcs[0].func)

    for key, value in reference_point.items():
        assert f"{key}_min" in flatten(problem.scalarization_funcs[0].func)
        assert value in flatten(problem.scalarization_funcs[0].func)

    for key, value in weights.items():
        assert f"{key}_min" in flatten(problem.scalarization_funcs[0].func)
        assert value in flatten(problem.scalarization_funcs[0].func)


def test_create_ws():
    """Tests that the weighted sum scalarization is added correctly."""
    problem = simple_test_problem()
    ws = {"f_1": 0.011, "f_2": 2.2, "f_3": 1.1, "f_4": 3.9, "f_5": 7.2}

    problem, target = add_weighted_sums(problem, symbol="ws", weights=ws)

    assert problem.scalarization_funcs[0].symbol == target

    for key, value in ws.items():
        assert f"{key}_min" in flatten(problem.scalarization_funcs[0].func)
        assert value in flatten(problem.scalarization_funcs[0].func)


def test_add_scalarization_function(river_w_fake_ideal_and_nadir):
    """Tests that scalarization functions are added correctly."""
    problem = river_w_fake_ideal_and_nadir

    ws = {"f_1": 1, "f_2": 2, "f_3": 1, "f_4": 3, "f_5": 5}

    ref_point = {"f_1": 1, "f_2": 2, "f_3": 3, "f_4": 4, "f_5": 5}

    problem, symbol_ws = add_weighted_sums(problem, symbol="WS", weights=ws)
    problem, symbol_asf = add_asf_nondiff(problem, reference_point=ref_point, symbol="ASF")

    assert len(problem.scalarization_funcs) == 2  # there should be two scalarization functions now
    assert problem.scalarization_funcs[0].name == "Weighted sums scalarization function"
    assert problem.scalarization_funcs[1].name == "Achievement scalarizing function"
    assert problem.scalarization_funcs[0].symbol == symbol_ws
    assert problem.scalarization_funcs[1].symbol == symbol_asf


@pytest.mark.slow
def test_add_epsilon_constraint_and_solve():
    """Tests the epsilon constraint scalarization and solving it."""
    problem = simple_test_problem()

    epsilons = {"f_1": 5.0, "f_2": None, "f_3": -4.0, "f_4": 4.3, "f_5": -3}
    eps_symbols = {"f_1": "f_1_eps", "f_2": None, "f_3": "f_3_eps", "f_4": "f_4_eps", "f_5": "f_5_eps"}
    objective_symbol = "f_2"
    target = "f_2_target"

    problem_w_cons, target, eps_symbols = add_epsilon_constraints(
        problem, target, eps_symbols, objective_symbol, epsilons
    )

    solver = create_scipy_minimize_solver(problem_w_cons)

    res = solver(target)

    # check that constraints are ok
    cons_values = [res.constraint_values[s] for s in eps_symbols]

    atol = 1e-9
    shifted = np.array(cons_values) - atol

    assert np.all(shifted < 0)


def test_add_epsilon_constraints():
    """The the correct functioning of adding the epsilon constraint scalarization."""
    _problem = simple_test_problem()

    epsilons = {"f_1": 5.0, "f_2": None, "f_3": -4.0, "f_4": 4.3, "f_5": -3}
    eps_symbols = {"f_1": "f_1_eps", "f_2": None, "f_3": "f_3_eps", "f_4": "f_4_eps", "f_5": "f_5_eps"}
    objective_symbol = "f_2"
    target = "f_2_target"

    problem, target, eps_symbols = add_epsilon_constraints(_problem, target, eps_symbols, objective_symbol, epsilons)

    assert len(problem.constraints) == 4

    assert problem.constraints[0].symbol == "f_1_eps"
    assert problem.constraints[0].name == "Epsilon for f_1"
    assert problem.constraints[0].func == ["Add", "f_1_min", ["Negate", 5.0]]
    assert problem.constraints[0].cons_type == ConstraintTypeEnum.LTE

    assert problem.constraints[1].symbol == "f_3_eps"
    assert problem.constraints[1].name == "Epsilon for f_3"
    assert problem.constraints[1].func == ["Add", "f_3_min", ["Negate", -4]]
    assert problem.constraints[1].cons_type == ConstraintTypeEnum.LTE

    assert problem.constraints[2].symbol == "f_4_eps"
    assert problem.constraints[2].name == "Epsilon for f_4"
    assert problem.constraints[2].func == ["Add", "f_4_min", ["Negate", 4.3]]
    assert problem.constraints[2].cons_type == ConstraintTypeEnum.LTE

    assert problem.constraints[3].symbol == "f_5_eps"
    assert problem.constraints[3].name == "Epsilon for f_5"
    assert problem.constraints[3].func == ["Add", "f_5_min", ["Negate", -3]]
    assert problem.constraints[3].cons_type == ConstraintTypeEnum.LTE

    assert _problem.constraints is None
