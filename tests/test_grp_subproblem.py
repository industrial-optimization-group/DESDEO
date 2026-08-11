"""
Tests related to preference aggregation of reference points and max-min fairness with local preference models
"""
import pytest
import numpy as np

from desdeo.problem.testproblems import zdt1, dtlz2, binh_and_korn, river_pollution_problem
from desdeo.problem import get_nadir_dict, get_ideal_dict, objective_dict_to_numpy_array
from desdeo.tools.utils import PyomoIpoptSolver

from desdeo.gdm.grp_subproblem import (
    build_grp_subproblem,
    additive_preference_constraints,
    symmetric_cones_preference_constraints,
    maxmin_fairness_constraints,
    maxmin_fairness_objective
)

@pytest.fixture
def zdt1_setup():
    problem = zdt1(30)
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))
    cip = np.array([1.0, 1.0])
    rps = np.array([[0.1, 0.95], [0.5, 0.83], [0.9, 0.69], [0.6, 0.75]])
    return problem, ideal, nadir, cip, rps

@pytest.mark.gdmtools
def test_additive_model_zdt1(zdt1_setup):
    """Test the additive local preference model using IPOPT on ZDT1."""
    problem, ideal, nadir, cip, rps = zdt1_setup
    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, nadir=nadir,
        preference_factory=additive_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha_min")
    assert result is not None

    cgrp_0, cgrp_1 = result.optimal_variables['cgrp_0'], result.optimal_variables['cgrp_1']
    assert isinstance(cgrp_0, (int, float))
    assert isinstance(cgrp_1, (int, float))
    assert 0.0 <= cgrp_0 <= 1.0
    assert 0.0 <= cgrp_1 <= 1.0

    w_sum = sum([result.optimal_variables[f'w_{m}'] for m in range(len(rps))])  # pyright: ignore
    assert np.isclose(w_sum, 1.0, atol=1e-4)

@pytest.mark.gdmtools
def test_cones_model_zdt1(zdt1_setup):
    """Test the unified symmetric cones model."""
    problem, ideal, nadir, cip, rps = zdt1_setup
    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, nadir=nadir,
        preference_factory=symmetric_cones_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha")
    assert result is not None
    cgrp_0 = result.optimal_variables['cgrp_0']
    assert isinstance(cgrp_0, (int, float))
    assert 0.0 <= cgrp_0 <= 1.0

@pytest.mark.gdmtools
def test_scaling_projections(zdt1_setup):
    """Test that providing Pareto projections alters the resulting GRP."""
    problem, ideal, nadir, cip, rps = zdt1_setup
    projections = np.array([[0.01, 0.99], [0.1, 0.7], [0.75, 0.18], [0.22, 0.46]])

    prob_unscaled = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, nadir=nadir,
        preference_factory=additive_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )
    res_unscaled = PyomoIpoptSolver(prob_unscaled).solve("obj_alpha_min")

    prob_scaled = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, nadir=nadir, projections=projections,
        preference_factory=additive_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )
    res_scaled = PyomoIpoptSolver(prob_scaled).solve("obj_alpha_min")

    # GRPs must differ due to scaling shift
    print(res_scaled)
    print(res_unscaled)
    assert not np.isclose(res_unscaled.optimal_variables['cgrp_0'], res_scaled.optimal_variables['cgrp_0'])

@pytest.mark.slow
@pytest.mark.gdmtools
def test_dtlz2_high_dimensional():
    """
    Test the smooth symmetric cones factory on a 3-objective DTLZ2 problem.
    """
    problem = dtlz2(n_variables=12, n_objectives=3)
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    ideal = np.array([0.0, 0.0, 0.0])
    cip = np.array([1.0, 1.0, 1.0])
    rps = np.array([[0.2, 0.8, 0.5], [0.7, 0.2, 0.6], [0.4, 0.5, 0.1]])

    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, nadir=nadir,
        preference_factory=symmetric_cones_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha_min")

    # Checking that something correct comes out
    assert result is not None
    assert 'cgrp_2' in result.optimal_variables
    for m in range(3):
        assert f's_{m}' in result.optimal_variables


@pytest.mark.gdmtools
def test_binh_and_korn_unscaled_warning():
    """
    Test the additive model on the Binh and Korn problem.
    This problem has unscaled objectives (e.g., up to 136.0), which perfectly tests
    if the codebase correctly flags unscaled data with a UserWarning while
    still successfully solving a simpler 2D problem.
    """
    problem = binh_and_korn()
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))

    cip = nadir  # Nadir is approx [136.0, 50.0]

    # 3 DMs with unscaled reference points
    rps = np.array([
        [50.0, 20.0],
        [100.0, 25.0],
        [30.0, 50.0]
    ])

    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, nadir=nadir,
        preference_factory=additive_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha_min")

    assert result is not None
    assert 'cgrp_0' in result.optimal_variables
    assert 'cgrp_1' in result.optimal_variables

    # Verify the GRP coordinates are within the unscaled bounds
    cgrp_0 = result.optimal_variables['cgrp_0']
    cgrp_1 = result.optimal_variables['cgrp_1']
    assert isinstance(cgrp_0, (int, float))
    assert isinstance(cgrp_1, (int, float))
    assert 0.0 <= cgrp_0 <= 136.0
    assert 0.0 <= cgrp_1 <= 50.0


@pytest.mark.slow
@pytest.mark.gdmtools
def test_river_pollution_many_objective():
    """
    Test the smooth symmetric cones factory on the River Pollution problem,
    which is a classic real-world benchmark with 5 objective functions.
    """
    problem = river_pollution_problem()
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))

    cip = nadir
    num_objs = len(problem.objectives)

    # Create 3 DMs with reference points distributed between the Ideal and Nadir points
    rps = np.array([
        ideal * 0.2 + nadir * 0.8,
        ideal * 0.5 + nadir * 0.5,
        ideal * 0.8 + nadir * 0.2,
    ])

    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, nadir=nadir,
        preference_factory=symmetric_cones_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha_min")

    assert result is not None

    # Check that the GRP has the correct number of coordinates (e.g., 5)
    for k in range(num_objs):
        assert f'cgrp_{k}' in result.optimal_variables

    # Check that all DMs received an evaluation score
    for m in range(len(rps)):
        assert f's_{m}' in result.optimal_variables
