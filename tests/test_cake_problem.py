"""Tests related to the best cake problem."""

from desdeo.mcdm.nimbus import solve_sub_problems
from desdeo.problem.testproblems import best_cake_problem


def test_with_nimbus():
    """Test that solving the cake problem with NIMBUS runs."""
    problem = best_cake_problem()

    rp = {"dry_crumb": 7.0, "sweet_texture": 7.0, "rise_collapse": 7.0, "moistness_grease": 7.0, "browning_burn": 7.0}
    init_point = {
        "dry_crumb": 6.0,
        "sweet_texture": 8.0,
        "rise_collapse": 6.0,
        "moistness_grease": 8.0,
        "browning_burn": 7.0,
    }

    res = solve_sub_problems(problem, init_point, rp, 4)

    assert len(res) == 4
