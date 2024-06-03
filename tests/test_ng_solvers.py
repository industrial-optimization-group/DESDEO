"""Test the nevergrad-based solvers."""

import pytest

from desdeo.problem import zdt1
from desdeo.tools import (
    NevergradGenericOptions,
    NevergradGenericSolver,
    add_asf_nondiff,
    add_epsilon_constraints,
    available_nevergrad_optimizers,
)


@pytest.mark.nevergrad
def test_ngopt_solver():
    """Tests the solver interface will all solvers with a small budget and multiple workers."""
    problem = zdt1(5)
    rp = {"f_1": 0.8, "f_2": 0.8}

    budget = 50

    for solver_name in available_nevergrad_optimizers:
        solver_opts = NevergradGenericOptions(budget=budget, num_workers=2, optimizer=solver_name)

        # without constraints
        problem_w_sf, target = add_asf_nondiff(problem, "target", rp, reference_in_aug=True)

        solver = NevergradGenericSolver(problem_w_sf, options=solver_opts)

        res = solver.solve(target)

        assert res.success

        # with constraints
        problem_w_sf, target, _ = add_epsilon_constraints(
            problem, "target", {"f_1": "f_1_eps", "f_2": "f_2_eps"}, "f_1", rp
        )

        solver = NevergradGenericSolver(problem_w_sf, options=solver_opts)

        res = solver.solve(target)

        assert res.success
