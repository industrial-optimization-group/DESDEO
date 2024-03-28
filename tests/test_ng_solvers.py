"""Test the nevergrad-based solvers."""

from desdeo.problem import dtlz2
from desdeo.tools import (
    NevergradGenericOptions,
    add_asf_nondiff,
    add_epsilon_constraints,
    create_ng_generic_solver,
)


def test_ngopt_solver():
    """Tests the NGOpt solver interface."""
    problem = dtlz2(5, 3)

    rp = {"f_1": 0.8, "f_2": 0.8, "f_3": 0.76}

    solver_opts = NevergradGenericOptions(budget=200, num_workers=50, optimizer="TBPSA")

    # without constraints
    problem_w_sf, target = add_asf_nondiff(problem, "target", rp)

    solver = create_ng_generic_solver(problem_w_sf, options=solver_opts)

    res = solver(target)

    assert res.constraint_values is None

    # with constraints
    problem_w_sf, target, _ = add_epsilon_constraints(
        problem, "target", {"f_1": "f_1_eps", "f_2": "f_2_eps", "f_3": "f_3_eps"}, "f_1", rp
    )

    solver = create_ng_generic_solver(problem_w_sf, options=solver_opts)

    res = solver(target)

    assert "f_2_eps" in res.constraint_values
    assert "f_3_eps" in res.constraint_values
