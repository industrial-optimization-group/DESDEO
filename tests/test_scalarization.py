"""Test for adding and utilizing scalarization functions."""

import numpy as np
import numpy.testing as npt
import pytest

from desdeo.problem import (
    ConstraintTypeEnum,
    dtlz2,
    momip_ti7,
    river_pollution_problem,
    simple_test_problem,
)
from desdeo.tools import (
    BonminOptions,
    guess_best_solver,
    NevergradGenericOptions,
    NevergradGenericSolver,
    PyomoBonminSolver,
    ScipyMinimizeSolver,
)
from desdeo.tools.scalarization import (
    ScalarizationError,
    add_asf_diff,
    add_asf_generic_diff,
    add_asf_generic_nondiff,
    add_asf_nondiff,
    add_epsilon_constraints,
    add_guess_sf_diff,
    add_guess_sf_nondiff,
    add_nimbus_sf_diff,
    add_nimbus_sf_nondiff,
    add_stom_sf_diff,
    add_stom_sf_nondiff,
    add_weighted_sums,
)


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


@pytest.mark.scalarization
@pytest.mark.asf
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

    n_objectives = 4
    n_variables = 5
    problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)
    reference_point = {"f_1": 0.4, "f_2": 0.8, "f_3": 0.7, "f_4": 0.75}
    reference_point_aug = {"f_1": 1.4, "f_2": 0.2, "f_3": 1.7, "f_4": 0.075}
    weights = {"f_1": 0.3, "f_2": 0.2, "f_3": 0.1, "f_4": 0.4}
    weights_aug = {"f_1": 0.2, "f_2": 0.3, "f_3": 0.4, "f_4": 0.1}

    problem_w_asf, target = add_asf_generic_nondiff(
        problem,
        symbol="asf",
        reference_point=reference_point,
        weights=weights,
        rho=1.0 # set rho as a greater scalar to be able to see the differences in values for these tests
    )
    # asf with a different reference point and different weights used in the augmentation term
    problem_w_asf_aug, target_aug = add_asf_generic_nondiff(
        problem, symbol="asf",
        reference_point=reference_point,
        weights=weights,
        reference_point_aug=reference_point_aug,
        weights_aug=weights_aug,
        rho=1.0 # set rho as a greater scalar to be able to see the differences in values for these tests
    )
    # asf with different weights used in the augmentation term
    problem_w_asf_diff_w, target_diff_w = add_asf_generic_nondiff(
        problem, symbol="asf",
        reference_point=reference_point,
        weights=weights,
        weights_aug=weights_aug,
        rho=1.0 # set rho as a greater scalar to be able to see the differences in values for these tests
    )
    # asf with a different reference point used in the augmentation term
    problem_w_asf_diff_r, target_diff_r = add_asf_generic_nondiff(
        problem, symbol="asf",
        reference_point=reference_point,
        weights=weights,
        reference_point_aug=reference_point_aug,
        rho=1.0 # set rho as a greater scalar to be able to see the differences in values for these tests
    )
    # asf with the same reference point used in the augmentation term
    problem_w_asf_same_r, target_same_r = add_asf_generic_nondiff(
        problem, symbol="asf",
        reference_point=reference_point,
        weights=weights,
        reference_point_aug=reference_point,
        rho=1.0 # set rho as a greater scalar to be able to see the differences in values for these tests
    )

    solver = ScipyMinimizeSolver(problem_w_asf)
    solver_aug = ScipyMinimizeSolver(problem_w_asf_aug)
    solver_diff_w = ScipyMinimizeSolver(problem_w_asf_diff_w)
    solver_diff_r = ScipyMinimizeSolver(problem_w_asf_diff_r)
    solver_same_r = ScipyMinimizeSolver(problem_w_asf_same_r)

    res = solver.solve(target)
    xs = res.optimal_variables
    fs = res.optimal_objectives

    res_aug = solver_aug.solve(target_aug)
    xs_aug = res_aug.optimal_variables
    fs_aug = res_aug.optimal_objectives

    res_diff_w = solver_diff_w.solve(target_diff_w)
    xs_diff_w = res_diff_w.optimal_variables
    fs_diff_w = res_diff_w.optimal_objectives

    res_diff_r = solver_diff_r.solve(target_diff_r)
    xs_diff_r = res_diff_r.optimal_variables
    fs_diff_r = res_diff_r.optimal_objectives

    res_same_r = solver_same_r.solve(target_same_r)
    xs_same_r = res_same_r.optimal_variables
    fs_same_r = res_same_r.optimal_objectives

    # check optimality of solutions
    assert all(np.isclose(xs[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    assert all(np.isclose(xs_aug[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs_aug[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    assert all(np.isclose(xs_diff_w[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs_diff_w[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    assert all(np.isclose(xs_diff_r[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs_diff_r[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    assert all(np.isclose(xs_same_r[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs_same_r[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    # check that reference point and/or different weights in augmentation term returns a different solution
    xs = [xs[var.symbol] for var in problem_w_asf.variables]
    xs_aug = [xs_aug[var.symbol] for var in problem_w_asf.variables]
    xs_diff_w = [xs_diff_w[var.symbol] for var in problem_w_asf.variables]
    xs_diff_r = [xs_diff_r[var.symbol] for var in problem_w_asf.variables]
    xs_same_r = [xs_same_r[var.symbol] for var in problem_w_asf.variables]

    assert xs != xs_aug != xs_diff_w != xs_diff_r != xs_same_r


@pytest.mark.scalarization
@pytest.mark.asf
def test_add_asf_generic_diff():
    """Test that the differentiable variant of the generic achievement scalarizing function produced Pareto optimal solutions."""
    n_objectives = 4
    n_variables = 5
    problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)
    reference_point = {"f_1": 0.4, "f_2": 0.8, "f_3": 0.7, "f_4": 0.75}
    reference_point_aug = {"f_1": 1.4, "f_2": 0.2, "f_3": 1.7, "f_4": 0.075}
    weights = {"f_1": 0.3, "f_2": 0.2, "f_3": 0.1, "f_4": 0.4}
    weights_aug = {"f_1": 0.2, "f_2": 0.3, "f_3": 0.4, "f_4": 0.1}

    problem_w_asf, target = add_asf_generic_diff(
        problem, symbol="asf", reference_point=reference_point, weights=weights
    )
    # asf with a different reference point and different weights used in the augmentation term
    problem_w_asf_aug, target = add_asf_generic_diff(
        problem,
        symbol="asf",
        reference_point=reference_point,
        weights=weights,
        reference_point_aug=reference_point_aug,
        weights_aug=weights_aug
    )
    # asf with different weights used in the augmentation term
    problem_w_asf_diff_w, target = add_asf_generic_diff(
        problem,
        symbol="asf",
        reference_point=reference_point,
        weights=weights,
        weights_aug=weights_aug
    )
    # asf with a different reference point used in the augmentation term
    problem_w_asf_diff_r, target = add_asf_generic_diff(
        problem,
        symbol="asf",
        reference_point=reference_point,
        weights=weights,
        reference_point_aug=reference_point_aug
    )
    # asf with the same reference point used in the augmentation term
    problem_w_asf_same_r, target = add_asf_generic_diff(
        problem,
        symbol="asf",
        reference_point=reference_point,
        weights=weights,
        reference_point_aug=reference_point
    )

    solver = ScipyMinimizeSolver(problem_w_asf)
    solver_aug = ScipyMinimizeSolver(problem_w_asf_aug)
    solver_diff_w = ScipyMinimizeSolver(problem_w_asf_diff_w)
    solver_diff_r = ScipyMinimizeSolver(problem_w_asf_diff_r)
    solver_same_r = ScipyMinimizeSolver(problem_w_asf_same_r)

    res = solver.solve(target)
    xs = res.optimal_variables
    fs = res.optimal_objectives

    res_aug = solver_aug.solve(target)
    xs_aug = res_aug.optimal_variables
    fs_aug = res_aug.optimal_objectives

    res_diff_w = solver_diff_w.solve(target)
    xs_diff_w = res_diff_w.optimal_variables
    fs_diff_w = res_diff_w.optimal_objectives

    res_diff_r = solver_diff_r.solve(target)
    xs_diff_r = res_diff_r.optimal_variables
    fs_diff_r = res_diff_r.optimal_objectives

    res_same_r = solver_same_r.solve(target)
    xs_same_r = res_same_r.optimal_variables
    fs_same_r = res_same_r.optimal_objectives

    # check optimality of solutions
    assert all(np.isclose(xs[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    assert all(np.isclose(xs_aug[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs_aug[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    assert all(np.isclose(xs_diff_w[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs_diff_w[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    assert all(np.isclose(xs_diff_r[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs_diff_r[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    assert all(np.isclose(xs_same_r[f"x_{i}"], 0.5) for i in range(n_objectives, n_variables + 1))
    npt.assert_almost_equal(sum(fs_same_r[obj.symbol] ** 2 for obj in problem_w_asf.objectives) ** 0.5, 1.0)

    # check that reference point and/or different weights in augmentation term returns a different solution
    fs = [res.optimal_objectives[obj.symbol] for obj in problem_w_asf.objectives]
    fs_aug = [res_aug.optimal_objectives[obj.symbol] for obj in problem_w_asf.objectives]
    fs_diff_w = [res_diff_w.optimal_objectives[obj.symbol] for obj in problem_w_asf.objectives]
    fs_diff_r = [res_diff_r.optimal_objectives[obj.symbol] for obj in problem_w_asf.objectives]
    fs_diff_r = [res_diff_r.optimal_objectives[obj.symbol] for obj in problem_w_asf.objectives]

    assert fs != fs_aug != fs_diff_w != fs_diff_r != fs_same_r


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

    solver = ScipyMinimizeSolver(problem_w_cons)

    res = solver.solve(target)

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


@pytest.mark.scalarization
@pytest.mark.nimbus
def test_nimbus_sf_init():
    """Test that the scalarization function is build correctly."""
    problem = river_pollution_problem()

    classifications = {
        "f_1": ("<", None),
        "f_2": ("<=", 42.1),
        "f_3": (">=", 22.2),
        "f_4": ("0", None),
        "f_5": ("=", None),
    }

    current_objective_vector = {"f_1": 69, "f_2": 111, "f_3": 999, "f_4": 0, "f_5": 123}

    problem_w_sf, target = add_nimbus_sf_diff(problem, "target", classifications, current_objective_vector)

    # six constraints should have been added in total (originally no constraints)
    assert len(problem_w_sf.constraints) == 6

    # check for correct constraint symbols
    constraint_symbols = [c.symbol for c in problem_w_sf.constraints]

    assert "f_1_lt" in constraint_symbols
    assert "f_1_eq" in constraint_symbols
    assert "f_2_lte" in constraint_symbols
    assert "f_2_eq" in constraint_symbols
    assert "f_3_gte" in constraint_symbols
    assert "f_5_eq" in constraint_symbols

    assert "_alpha" in flatten(problem_w_sf.get_constraint("f_1_lt").func)
    assert "f_1_min" in flatten(problem_w_sf.get_constraint("f_1_lt").func)

    assert "f_1_min" in flatten(problem_w_sf.get_constraint("f_1_eq").func)
    assert 69 in flatten(problem_w_sf.get_constraint("f_1_eq").func)

    assert "_alpha" in flatten(problem_w_sf.get_constraint("f_2_lte").func)
    assert "f_2_min" in flatten(problem_w_sf.get_constraint("f_2_lte").func)
    assert 42.1 in flatten(problem_w_sf.get_constraint("f_2_lte").func)

    assert "f_2_min" in flatten(problem_w_sf.get_constraint("f_2_eq").func)
    assert 111 in flatten(problem_w_sf.get_constraint("f_2_eq").func)

    assert "f_3_min" in flatten(problem_w_sf.get_constraint("f_3_gte").func)
    assert 22.2 in flatten(problem_w_sf.get_constraint("f_3_gte").func)

    assert "f_5_min" in flatten(problem_w_sf.get_constraint("f_5_eq").func)
    assert 123 in flatten(problem_w_sf.get_constraint("f_5_eq").func)

    assert problem_w_sf.get_variable("_alpha") is not None

    assert problem_w_sf.get_scalarization("target") is not None

    assert all(
        f"{obj.symbol}_min" in flatten(problem_w_sf.get_scalarization("target").func) for obj in problem_w_sf.objectives
    )

    # should raise error, missing classification
    classifications = {
        "f_1": ("<", None),
        "f_2": ("<=", 42.1),
        "f_4": ("0", None),
        "f_5": ("=", None),
    }
    with pytest.raises(ScalarizationError):
        _ = add_nimbus_sf_diff(problem, "target", classifications, current_objective_vector)

    # should raise error, invalid classifications
    classifications = {
        "f_1": ("<", None),
        "f_2": ("<=", 42.1),
        "f_3": ("<=", 22.2),
        "f_4": ("<", None),
        "f_5": ("<", None),
    }
    with pytest.raises(ScalarizationError):
        _ = add_nimbus_sf_diff(problem, "target", classifications, current_objective_vector)


@pytest.mark.scalarization
@pytest.mark.nimbus
@pytest.mark.slow
def test_nimbus_sf_solve():
    """Check that the NIMBUS scalarization finds Pareto optimal solutions."""
    problem = momip_ti7()
    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-Hyb")

    weights = {"f_1": 0.25, "f_2": 0.5, "f_3": 0.25}
    problem_w_sum, t_sum = add_weighted_sums(problem, "target", weights)

    solver = PyomoBonminSolver(problem_w_sum, sol_options)

    results = solver.solve(t_sum)
    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    initial_solution = results.optimal_objectives

    # improve f_1, let f_2 worsen until limit, let f_3 worsen until limit
    f_2_limit = 1.2
    f_3_limit = -0.3
    classifications = {"f_1": ("<", None), "f_2": (">=", f_2_limit), "f_3": (">=", f_3_limit)}

    problem_w_sf, sf_target = add_nimbus_sf_diff(
        problem, "target", classifications=classifications, current_objective_vector=initial_solution
    )

    solver = PyomoBonminSolver(problem_w_sf, sol_options)

    results = solver.solve(sf_target)

    assert results.success
    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0, decimal=6)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    new_solution = results.optimal_objectives

    # check that solution adheres to the classifications
    assert new_solution["f_1"] < initial_solution["f_1"]  # f_1 has improved
    # f_2 must be either f_2_limit or better
    assert np.isclose(new_solution["f_2"], f_2_limit, atol=1e-6) or new_solution["f_2"] < f_2_limit
    # f_3 must be either f_3_limit or better
    assert np.isclose(new_solution["f_3"], f_3_limit, atol=1e-6) or new_solution["f_3"] < f_3_limit

    # worsen f_1, let f_2 keep, improve f_3 until -0.5
    f_1_limit = -0.6
    f_3_limit = -0.5
    new_classifications = {"f_1": (">=", f_1_limit), "f_2": ("=", None), "f_3": ("<=", f_3_limit)}

    problem_w_sf, sf_target = add_nimbus_sf_diff(problem, "target", new_classifications, new_solution)

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-Hyb")
    solver = PyomoBonminSolver(problem_w_sf, sol_options)

    results = solver.solve(sf_target)

    assert results.success
    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0, decimal=6)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    new_new_solution = results.optimal_objectives

    # f_1 should be worse
    assert new_new_solution["f_1"] > new_solution["f_1"]
    assert np.isclose(new_new_solution["f_1"], f_1_limit, atol=1e-6) or new_new_solution["f_1"] < f_1_limit

    # f_2 should stay the same
    npt.assert_almost_equal(new_new_solution["f_2"], new_solution["f_2"], decimal=6)

    # f_3 must have improved
    assert new_new_solution["f_3"] < new_solution["f_3"]


@pytest.mark.scalarization
@pytest.mark.nimbus
@pytest.mark.slow
def test_stom_sf_diff():
    """Test that STOM results in correct solutions."""
    problem = momip_ti7()

    first_reference_point = {"f_1": -2.0, "f_2": 2.0, "f_3": 0.0}

    problem_w_sf, target = add_stom_sf_diff(problem, "target", first_reference_point)

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-Hyb")
    solver = PyomoBonminSolver(problem_w_sf, sol_options)

    results = solver.solve(target)

    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0, decimal=6)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    first_solution = results.optimal_objectives

    assert results.success

    second_reference_point = {"f_1": -1.0, "f_2": -1.0, "f_3": -1.5}

    problem_w_sf, target = add_stom_sf_diff(problem, "target", second_reference_point)

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-Hyb")
    solver = PyomoBonminSolver(problem_w_sf, sol_options)

    results = solver.solve(target)

    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0, decimal=6)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    second_solution = results.optimal_objectives

    assert first_solution["f_1"] < second_solution["f_1"]  # f_1 should have worsened
    assert first_solution["f_2"] > second_solution["f_2"]  # f_2 should have worsened
    assert first_solution["f_3"] > second_solution["f_3"]  # f_3 should have improved


@pytest.mark.nimbus
def test_guess_sf_init():
    """Test that the GUESS scalarization is initialized correctly."""
    problem = river_pollution_problem()

    rp = {"f_1": -5.0, "f_2": -3.0, "f_3": 2.5, "f_4": -5.0, "f_5": 0.35}

    problem_w_sf, target = add_guess_sf_diff(problem, "target", rp)

    assert len(problem_w_sf.constraints) == 4

    rp = {"f_1": -5.0, "f_2": -3.0, "f_3": 2.5, "f_4": -5.0, "f_5": 0.25}

    problem_w_sf, target = add_guess_sf_diff(problem, "target", rp)

    assert len(problem_w_sf.constraints) == 5

    rp = {"f_1": -4.75, "f_2": -2.85, "f_3": 0.32, "f_4": -9.70, "f_5": 0.25}

    problem_w_sf, target = add_guess_sf_diff(problem, "target", rp)

    assert len(problem_w_sf.constraints) == 1


@pytest.mark.scalarization
@pytest.mark.nimbus
@pytest.mark.slow
def test_guess_sf_diff():
    """Test that GUESS results in correct solutions."""
    problem = momip_ti7()

    first_reference_point = {"f_1": -2.0, "f_2": 2.0, "f_3": 0.0}

    problem_w_sf, target = add_guess_sf_diff(problem, "target", first_reference_point)

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-Hyb")
    solver = PyomoBonminSolver(problem_w_sf, sol_options)

    results = solver.solve(target)

    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0, decimal=6)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    first_solution = results.optimal_objectives

    assert results.success

    second_reference_point = {"f_1": -1.0, "f_2": -1.0, "f_3": -1.5}

    problem_w_sf, target = add_guess_sf_diff(problem, "target", second_reference_point)

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-Hyb")
    solver = PyomoBonminSolver(problem_w_sf, sol_options)

    results = solver.solve(target)

    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0, decimal=6)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    second_solution = results.optimal_objectives

    assert first_solution["f_1"] < second_solution["f_1"]  # f_1 should have worsened
    assert first_solution["f_2"] > second_solution["f_2"]  # f_2 should have worsened
    assert first_solution["f_3"] > second_solution["f_3"]  # f_3 should have improved


@pytest.mark.nimbus
def test_achievement_sf_init():
    """Test that the achievement scalarization is initialized correctly."""
    problem = river_pollution_problem()

    rp = {"f_1": -5.0, "f_2": -3.0, "f_3": 2.5, "f_4": -5.0, "f_5": 0.35}

    problem_w_sf, target = add_asf_diff(problem, "target", rp)

    # one for each objective function
    assert len(problem_w_sf.constraints) == 5


@pytest.mark.scalarization
@pytest.mark.nimbus
@pytest.mark.slow
def test_achievement_sf_diff():
    """Test that ASF results in correct solutions."""
    problem = momip_ti7()

    first_reference_point = {"f_1": -2.0, "f_2": 2.0, "f_3": 0.0}

    problem_w_sf, target = add_asf_diff(problem, "target", first_reference_point)

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-Hyb")
    solver = PyomoBonminSolver(problem_w_sf, sol_options)

    results = solver.solve(target)

    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0, decimal=6)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    first_solution = results.optimal_objectives

    assert results.success

    second_reference_point = {"f_1": -1.0, "f_2": -1.0, "f_3": -1.5}

    problem_w_sf, target = add_asf_diff(problem, "target", second_reference_point)

    sol_options = BonminOptions(tol=1e-6, bonmin_algorithm="B-Hyb")
    solver = PyomoBonminSolver(problem_w_sf, sol_options)

    results = solver.solve(target)

    assert results.success

    xs = results.optimal_variables
    npt.assert_almost_equal(xs["x_1"] ** 2 + xs["x_2"] ** 2 + xs["x_3"] ** 2, 1.0, decimal=6)
    assert (xs["x_4"], xs["x_5"], xs["x_6"]) in [(0, 0, -1), (0, -1, 0), (-1, 0, 0)]

    second_solution = results.optimal_objectives

    assert first_solution["f_1"] < second_solution["f_1"]  # f_1 should have worsened
    assert first_solution["f_2"] > second_solution["f_2"]  # f_2 should have worsened
    assert first_solution["f_3"] > second_solution["f_3"]  # f_3 should have improved


@pytest.mark.scalarization
@pytest.mark.nimbus
@pytest.mark.slow
def test_nimbus_sf_nondiff_solve():
    """Check that the non-differentiable NIMBUS scalarization finds Pareto optimal solutions."""
    n_variables = 3
    n_objectives = 3
    problem = dtlz2(n_variables, n_objectives)

    weights = {"f_1": 0.1, "f_2": 0.1, "f_3": 0.8}
    problem_w_sum, t_sum = add_weighted_sums(problem, "target", weights)

    solver_options = NevergradGenericOptions(budget=250, num_workers=1, optimizer="NGOpt")

    solver = NevergradGenericSolver(problem_w_sum, solver_options)

    results = solver.solve(t_sum)
    assert results.success

    xs = results.optimal_variables
    # quite high atol to keep budget and time to compute low
    assert all(np.isclose(xs[f"x_{i}"], 0.5, atol=1e-2) for i in range(n_objectives, n_variables + 1))
    assert np.isclose(sum(results.optimal_objectives[obj.symbol] ** 2 for obj in problem.objectives), 1.0, atol=1e-2)

    initial_solution = results.optimal_objectives

    # improve f_2, let others change freely
    classifications = {"f_1": ("0", None), "f_2": ("<", None), "f_3": ("0", None)}

    problem_w_sf, sf_target = add_nimbus_sf_nondiff(
        problem, "target", classifications=classifications, current_objective_vector=initial_solution
    )

    assert len(problem_w_sf.constraints) == 1

    solver_options = NevergradGenericOptions(budget=500, num_workers=1, optimizer="NGOpt")

    solver = NevergradGenericSolver(problem_w_sf, solver_options)

    results = solver.solve(sf_target)

    xs = results.optimal_variables
    assert results.success
    # atol is crap here as well
    assert all(np.isclose(xs[f"x_{i}"], 0.5, atol=1e-2) for i in range(n_objectives, n_variables + 1))
    assert np.isclose(sum(results.optimal_objectives[obj.symbol] ** 2 for obj in problem.objectives), 1.0, atol=1e-2)

    # solution is feasible
    for c in (r := results.constraint_values):
        assert r[c] <= 0

    second_solution = results.optimal_objectives

    assert initial_solution["f_2"] > second_solution["f_2"]  # f_2 must have improved


@pytest.mark.scalarization
@pytest.mark.nimbus
@pytest.mark.slow
def test_stom_sf_nondiff_solve():
    """Test that the non-differentiable variant of STOM works."""
    n_variables = 3
    n_objectives = 3
    problem = dtlz2(n_variables, n_objectives)

    rp = {"f_1": 0.2, "f_2": 0.5, "f_3": 0.7}

    problem_w_sf, target = add_stom_sf_nondiff(problem, "target", rp)

    solver_options = NevergradGenericOptions(budget=250, num_workers=1, optimizer="NGOpt")

    solver = NevergradGenericSolver(problem_w_sf, solver_options)

    result = solver.solve(target)

    assert result.success

    xs = result.optimal_variables
    assert result.success
    # atol is crap here as well
    assert all(np.isclose(xs[f"x_{i}"], 0.5, atol=1e-1) for i in range(n_objectives, n_variables + 1))
    assert np.isclose(sum(result.optimal_objectives[obj.symbol] ** 2 for obj in problem.objectives), 1.0, atol=1e-2)

    # f_1 should be the lowest value
    assert result.optimal_objectives["f_1"] < result.optimal_objectives["f_2"]
    assert result.optimal_objectives["f_1"] < result.optimal_objectives["f_3"]


@pytest.mark.scalarization
@pytest.mark.nimbus
@pytest.mark.slow
def test_guess_sf_nondiff_solve():
    """Test that the non-differentiable variant of GUESS works."""
    n_variables = 3
    n_objectives = 3
    problem = dtlz2(n_variables, n_objectives)

    rp = {"f_1": 0.6, "f_2": 0.2, "f_3": 0.7}

    problem_w_sf, target = add_guess_sf_nondiff(problem, "target", rp)

    solver_options = NevergradGenericOptions(budget=250, num_workers=1, optimizer="NGOpt")

    solver = NevergradGenericSolver(problem_w_sf, solver_options)

    result = solver.solve(target)

    assert result.success

    xs = result.optimal_variables
    assert result.success
    # atol is crap here as well
    assert all(np.isclose(xs[f"x_{i}"], 0.5, atol=1e-1) for i in range(n_objectives, n_variables + 1))
    assert np.isclose(sum(result.optimal_objectives[obj.symbol] ** 2 for obj in problem.objectives), 1.0, atol=1e-2)

    # f_2 should be the lowest value
    assert result.optimal_objectives["f_2"] < result.optimal_objectives["f_1"]
    assert result.optimal_objectives["f_2"] < result.optimal_objectives["f_3"]
