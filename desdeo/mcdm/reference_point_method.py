"""Functions related to the reference point method.

This module contains functions related to the reference point method as
presented in Wierzbicki, A. P. (1982). A mathematical basis for satisficing
decision making. Mathematical modelling, 3(5), 391-405.
"""

import numpy as np

from desdeo.problem import (
    Problem,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
)
from desdeo.tools import (
    BaseSolver,
    SolverOptions,
    SolverResults,
    add_asf_diff,
    add_asf_nondiff,
    guess_best_solver,
)


class ReferencePointError(Exception):
    """Raised when an error with the reference point method is encountered."""


def rpm_solve_solutions(
    problem: Problem,
    reference_point: dict[str, float],
    scalarization_options: dict | None = None,
    solver: BaseSolver | None = None,
    solver_options: SolverOptions | None = None,
) -> list[SolverResults]:
    """Finds (near) Pareto optimal solutions based on a reference point.

    Find a (near) Pareto optimal solution based on the given reference point by
    optimizing an achievement scalarizing function. The original reference point
    is also perturbed, and another k (near) Pareto optimal solutions are found.
    The k+1 solutions are then returned.

    Args:
        problem (Problem): the problem to be solved.
        reference_point (dict[str, float]): the reference point. The keys of the dict
            represent the objective function symbols defined in problem. The values
            represent the aspiration level values.
        scalarization_options (dict | None, optional): keyword arguments to be
            passed to the achievement scalarizing function. Defaults to None.
        solver (BaseSolver | None, optional): solver to optimize the achievement
            scalarizing function. If not given, the method tried to guess the
            most suitable solver based on the problem. Defaults to None.
        solver_options (SolverOptions | None, optional): options passed to the
            solver. If not given, the solver will use its default options. Defaults to None.

    Raises:
        ReferencePointError: the reference point is ill-defined.

    Returns:
        list[SolverResults]: a list of results containing the solutions found using
            the reference point and the k perturbed reference points.

    Note:
        If the problem is twice differentiable, `add_asf_diff` is used from `desdeo.tools`.
            If the problem is not twice differentiable, then `add_asf_nondiff` is used.
    """
    # setup problem with ASF
    # check if problem is differentiable or not, choose appropriate ASF variant.

    if not all(obj.symbol in reference_point for obj in problem.objectives):
        msg = f"The reference point {reference_point} is missing entries for one or more of the objective functions."
        raise ReferencePointError(msg)

    _add_asf = add_asf_diff if problem.is_twice_differentiable else add_asf_nondiff

    problem_w_asf, target = _add_asf(
        problem, "_asf", reference_point, **scalarization_options if scalarization_options is not None else {}
    )

    # setup solver
    # solve scalarized problem with given reference point

    _init_solver = guess_best_solver(problem_w_asf) if solver is None else solver
    _solver = _init_solver(problem_w_asf, solver_options)

    initial_solution = _solver.solve(target)

    # using the found solution, perturb the reference point to get
    # k (num of objectives) perturbed reference points

    initial_objective_vector = objective_dict_to_numpy_array(problem, initial_solution.optimal_objectives)
    reference_point_vector = objective_dict_to_numpy_array(problem, reference_point)

    distance = np.linalg.norm(reference_point_vector - initial_objective_vector)
    unit_vectors = np.eye(len(initial_objective_vector))

    perturbed_reference_point_vectors = reference_point_vector + (distance * unit_vectors)

    perturbed_reference_points = [numpy_array_to_objective_dict(problem, v) for v in perturbed_reference_point_vectors]

    # scalarize the problem using the appropriate ASF variant and the perturbed
    # reference points

    perturbed_problems_and_targets = [
        _add_asf(problem, "_asf", rp, **scalarization_options if scalarization_options is not None else {})
        for rp in perturbed_reference_points
    ]

    # solve the problems
    perturbed_solutions = [
        _init_solver(problem_and_target[0], solver_options).solve(problem_and_target[1])
        for problem_and_target in perturbed_problems_and_targets
    ]

    # return the original solution and the solutions found with the perturbed reference points
    return [initial_solution, *perturbed_solutions]
