"""Tests related to preference aggregation of reference points and max-min fairness."""

import numpy as np
import pytest

from desdeo.gdm.grp_subproblem import (
    additive_preference_constraints,
    build_grp_subproblem,
    maxmin_fairness_constraints,
    maxmin_fairness_objective,
    symmetric_cones_preference_constraints,
)
from desdeo.problem import get_ideal_dict, get_nadir_dict, objective_dict_to_numpy_array
from desdeo.problem.testproblems import binh_and_korn, river_pollution_problem, zdt1
from desdeo.tools.utils import PyomoIpoptSolver


@pytest.fixture
def zdt1_setup():
    """Problem setup for ZDT1."""
    problem = zdt1(30)
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))
    cip = np.array([1.0, 1.0])
    rps = np.array([[0.1, 0.95], [0.5, 0.83], [0.9, 0.69], [0.6, 0.75]])
    return problem, ideal, nadir, cip, rps

@pytest.mark.gdmtools
def test_additive_model_zdt1(zdt1_setup):
    """Test the additive local preference model using IPOPT on ZDT1."""
    _problem, ideal, nadir, cip, rps = zdt1_setup
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
    assert np.isclose(cgrp_0, 0.1, atol=1e-2)
    assert np.isclose(cgrp_1, 0.95, atol=1e-2)

    assert all(float(result.optimal_variables[f's_{m}']) > 0 for m in range(len(rps)))  # type: ignore

    w_sum = sum([result.optimal_variables[f'w_{m}'] for m in range(len(rps))])  # pyright: ignore
    assert np.isclose(w_sum, 1.0, atol=1e-4)

@pytest.mark.gdmtools
def test_cones_model_zdt1(zdt1_setup):
    """Test the symmetric cones model."""
    _problem, ideal, nadir, cip, rps = zdt1_setup
    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, nadir=nadir,
        preference_factory=symmetric_cones_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha_min")
    assert result is not None
    cgrp_0 = result.optimal_variables['cgrp_0']
    cgrp_1 = result.optimal_variables['cgrp_1']
    assert isinstance(cgrp_0, (int, float))
    assert isinstance(cgrp_1, (int, float))
    assert 0.0 <= cgrp_0 <= 1.0
    assert 0.0 <= cgrp_1 <= 1.0
    assert np.isclose(cgrp_0, 0.6, atol=1e-2)
    assert np.isclose(cgrp_1, 0.75, atol=1e-2)

    assert all(float(result.optimal_variables[f's_{m}']) > 0 for m in range(len(rps)))  # type: ignore

    w_sum = sum([result.optimal_variables[f'w_{m}'] for m in range(len(rps))])  # pyright: ignore
    assert np.isclose(w_sum, 1.0, atol=1e-4)

@pytest.mark.gdmtools
def test_scaling_projections(zdt1_setup):
    """Test that providing Pareto projections alters the resulting GRP."""
    _problem, ideal, nadir, cip, rps = zdt1_setup
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
    assert not np.isclose(res_unscaled.optimal_variables['cgrp_0'], res_scaled.optimal_variables['cgrp_0'])
    assert not np.isclose(res_unscaled.optimal_variables['cgrp_1'], res_scaled.optimal_variables['cgrp_1'])


@pytest.mark.gdmtools
def test_binh_and_korn():
    """Test the additive model on the Binh and Korn problem."""
    problem = binh_and_korn()
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))

    cip = nadir

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

    # Verify the SCALED GRP coordinates are correctly normalized to [0, 1]
    cgrp_scaled_0 = result.optimal_variables['cgrp_scaled_0']
    cgrp_scaled_1 = result.optimal_variables['cgrp_scaled_1']
    assert -1e-4 <= cgrp_scaled_0 <= 1.0001  # type:ignore
    assert -1e-4 <= cgrp_scaled_1 <= 1.0001  # type:ignore

    # Verify the UNSCALED GRP coordinates are successfully mapped back to the objective space, should not be [0,1]
    cgrp_0 = result.optimal_variables['cgrp_0']
    cgrp_1 = result.optimal_variables['cgrp_1']
    assert isinstance(cgrp_0, (int, float))
    assert isinstance(cgrp_1, (int, float))

    # Bounded by ideal and nadir (accounting for minor solver tolerances)
    assert min(ideal[0], nadir[0]) - 1e-4 <= cgrp_0 <= max(ideal[0], nadir[0]) + 1e-4
    assert min(ideal[1], nadir[1]) - 1e-4 <= cgrp_1 <= max(ideal[1], nadir[1]) + 1e-4

@pytest.mark.slow
@pytest.mark.gdmtools
def test_river_pollution_many_objective():
    """Test the symmetric cones on the River Pollution problem."""
    problem = river_pollution_problem()
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))

    cip = nadir
    num_objs = len(problem.objectives)

    # Create 3 DMs with reference points distributed between the Ideal and Nadir points with DM3 being most greedy
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

    # Check that the GRP constraints and conversions were created for all 5 objectives
    for k in range(num_objs):
        assert f'cgrp_{k}' in result.optimal_variables
        assert f'cgrp_scaled_{k}' in result.optimal_variables

        cgrp_k = result.optimal_variables[f'cgrp_{k}']
        cgrp_scaled_k = result.optimal_variables[f'cgrp_scaled_{k}']

        # Ensure normalization logic successfully constrained the internal solver space to [0, 1]
        assert -1e-4 <= cgrp_scaled_k <= 1.0001  # type:ignore

        # Ensure the unscaled variables successfully mapped back into the River Pollution bounds
        assert min(ideal[k], nadir[k]) - 1e-4 <= cgrp_k <= max(ideal[k], nadir[k]) + 1e-4

    # Check that all DMs received an evaluation score > 0
    assert all(float(result.optimal_variables[f's_{m}']) > 0 for m in range(len(rps)))  # type: ignore
