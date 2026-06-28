"""Project a solution on to the Pareto front using reference point scalarization and check for optimality."""

from desdeo.problem import Problem, SimulatorEvaluator
from desdeo.tools import (
    ScipyDeSolver,
    SolverResults,
    add_asf_nondiff,
)


def project_solution(
    problem: Problem,
    objective_vector: dict,
    tolerance: float,
    ideal: dict[str, int | float],
    nadir: dict[str, int | float],
    decision_vector: dict | None = None,
) -> tuple[bool, SolverResults]:
    """Project a solution on to the Pareto front using reference point scalarization and check for optimality.

    The function optimizes the problem using the reference point scalarization method with the provided decision vector
    as the reference point. The scalarization function value of the optimized solution is then compared to the
    scalarization function value of the provided objective vector (equal to zero by definition). If the difference
    between these two values is less than the specified tolerance, the solution is considered to be optimal.
    Currently, the function uses the ScipyDeSolver to solve the scalarized problem.

    Args:
        problem (Problem): The problem object for the optimization problem.
        objective_vector (dict): The objective vector for the solution to be projected.
        tolerance (float): The tolerance for checking optimality.
        ideal (dict[str, int | float]): The ideal point of the problem.
        nadir (dict[str, int | float]): The nadir point of the problem.
        decision_vector (dict | None): The decision vector for the solution to be projected. The decision vector must
            correspond to the given objective vector. If None, the default starting strategy will be used.

    Returns:
        tuple[bool, SolverResults]: A tuple containing a boolean indicating whether the given solution is optimal and
            the solver results. The SolverResults object contains information about the optimization process, including
            the optimal solution found, the success status of the solver, and any messages or errors encountered during
            the optimization process. The scalarization function value of the optimized solution can be accessed using
            `results.scalarization_values["ref_point"]`.
            Note that for the optimality check to be valid, the provided objective vector must be a
            feasible solution to the problem. A solution like the ideal point will always be considered optimal by this
            method. Moreover, the decision vector must be provided, and it must correspond to the given objective
            vector. Without it, the solver may not find any solution dominating a potentially non-optimal solution,
            leading to a false positive result. Note that the solver may fail to find a dominating solution even if one
            exists, again leading to a false positive result.
    """
    scalarized_problem, symbol = add_asf_nondiff(
        problem, symbol="ref_point", reference_point=objective_vector, ideal=ideal, nadir=nadir, reference_in_aug=True
    )
    # Setting up the initial guess using the options does not work currently. Hence the hack.
    # options = ScipyDeOptions(initial_guess=decision_vector)
    # solver = ScipyDeSolver(scalarized_problem, options=options)
    solver = ScipyDeSolver(scalarized_problem)
    if decision_vector is not None:
        solver.initial_guess = list(decision_vector.values())
    # TODO: remove the line below once ISSUE #549 is resolved.
    solver.evaluator = SimulatorEvaluator(scalarized_problem)
    results: SolverResults = solver.solve(symbol)
    if not results.success:
        raise RuntimeError(f"Solver failed to find the optimal solution: {results.message}")
    if results.scalarization_values[symbol] < -tolerance:
        return False, results
    return True, results
