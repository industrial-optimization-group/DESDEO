"""Test the nevergrad-based solvers."""

from desdeo.problem import dtlz2
from desdeo.tools import (
    create_ng_ngopt_solver,
    add_weighted_sums,
    NgOptOptions,
    add_asf_nondiff,
    add_epsilon_constraints,
)


def test_ngopt_solver():
    """Tests the NGOpt solver interface."""
    problem = dtlz2(5, 3)

    rp = {"f_1": 0.6, "f_2": 0.6, "f_3": 0.6}

    solver_opts = NgOptOptions(budget=1000)

    problem_w_sf, target, _ = add_epsilon_constraints(
        problem, "target", {"f_1": "f_1_eps", "f_2": "f_2_eps", "f_3": "f_3_eps"}, "f_1", rp
    )

    solver = create_ng_ngopt_solver(problem_w_sf, options=solver_opts)

    res = solver(target)

    return
