"""
Tests related to preference aggregation of reference points and max-min fairness 
using the new DESDEO functional factory architecture.
"""
import pytest
import numpy as np

from desdeo.problem.testproblems import zdt1, dtlz2
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
    rps = np.array([[0.1, 0.95], [0.5, 0.83], [0.4, 0.81]])
    return problem, ideal, nadir, cip, rps

@pytest.mark.pref_agg
def test_additive_model_zdt1(zdt1_setup):
    """Test the additive local preference model using IPOPT on ZDT1."""
    problem, ideal, nadir, cip, rps = zdt1_setup
    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal,
        preference_factory=additive_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha")
    assert result is not None

    cgrp_0, cgrp_1 = result.optimal_variables['cgrp_0'], result.optimal_variables['cgrp_1']
    assert isinstance(cgrp_0, (int, float))
    assert isinstance(cgrp_1, (int, float))
    assert 0.0 <= cgrp_0 <= 1.0
    assert 0.0 <= cgrp_1 <= 1.0

    w_sum = sum([result.optimal_variables[f'w_{m}'] for m in range(len(rps))])  # pyright: ignore
    assert np.isclose(w_sum, 1.0, atol=1e-4)

@pytest.mark.pref_agg
def test_cones_model_zdt1(zdt1_setup):
    """Test the unified symmetric cones model."""
    problem, ideal, nadir, cip, rps = zdt1_setup
    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal,
        preference_factory=symmetric_cones_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha")
    assert result is not None
    cgrp_0 = result.optimal_variables['cgrp_0']
    assert isinstance(cgrp_0, (int, float))
    assert 0.0 <= cgrp_0 <= 1.0

@pytest.mark.pref_agg
def test_scaling_projections(zdt1_setup):
    """Test that providing Pareto projections safely alters the resulting GRP."""
    problem, ideal, nadir, cip, rps = zdt1_setup
    projections = np.array([[0.05, 0.90], [0.45, 0.45], [0.35, 0.60]])

    prob_unscaled = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal,
        preference_factory=additive_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )
    res_unscaled = PyomoIpoptSolver(prob_unscaled).solve("obj_alpha")

    prob_scaled = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal, projections=projections,
        preference_factory=additive_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )
    res_scaled = PyomoIpoptSolver(prob_scaled).solve("obj_alpha")

    # GRPs must differ due to scaling shift
    assert not np.isclose(res_unscaled.optimal_variables['cgrp_0'], res_scaled.optimal_variables['cgrp_0'])

@pytest.mark.slow
@pytest.mark.pref_agg
def test_dtlz2_high_dimensional():
    """
    Test the smooth symmetric cones factory on a 3-objective DTLZ2 problem.
    """
    problem = dtlz2(n_variables=12, n_objectives=3)
    ideal = np.array([0.0, 0.0, 0.0])
    cip = np.array([1.0, 1.0, 1.0])
    rps = np.array([[0.2, 0.8, 0.5], [0.7, 0.2, 0.6], [0.4, 0.5, 0.1]])

    grp_subproblem = build_grp_subproblem(
        rps=rps, cip=cip, ideal=ideal,
        preference_factory=symmetric_cones_preference_constraints,
        fairness_constraints_factory=maxmin_fairness_constraints,
        fairness_objective_factory=maxmin_fairness_objective
    )

    result = PyomoIpoptSolver(grp_subproblem).solve("obj_alpha")

    # Checking that something correct comes out
    assert result is not None
    assert 'cgrp_2' in result.optimal_variables
    for m in range(3):
        assert f's_{m}' in result.optimal_variables
