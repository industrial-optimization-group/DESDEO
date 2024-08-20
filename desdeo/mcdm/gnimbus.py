"""Functions related to the Sychronous NIMBUS method.

References:
    Miettinen, K., & Mäkelä, M. M. (2006). Synchronous approach in interactive
        multiobjective optimization. European Journal of Operational Research,
        170(3), 909–922.
"""  # noqa: RUF002

import numpy as np

from desdeo.problem import GenericEvaluator, Problem, VariableType, variable_dict_to_numpy_array, variable_dict_to_numpy_array_as_group
from desdeo.tools import (
    BaseSolver,
    SolverOptions,
    SolverResults,
    add_group_asf_diff,
    add_group_asf,
    add_group_guess_sf_diff,
    add_group_guess_sf,
    add_group_nimbus_sf_diff,
    add_group_nimbus_sf,
    add_group_stom_sf_diff,
    add_group_stom_sf,
    guess_best_solver,
)
from desdeo.mcdm.nimbus import (
    generate_starting_point,
    infer_classifications,
    NimbusError
)

def solve_sub_problems(  # noqa: PLR0913
    problem: Problem,
    current_objectives: dict[str, float],
    reference_points: list[dict[str, float]],
    num_desired: int,
    scalarization_options: dict | None = None,
    create_solver: BaseSolver | None = None,
    solver_options: SolverOptions | None = None,
) -> list[SolverResults]:
    r"""Solves a desired number of sub-problems as defined in the NIMBUS methods.

    Solves 1-4 scalarized problems utilizing different scalarization
    functions. The scalarizations are based on the classification of a
    solutions provided by a decision maker. The classifications
    are represented by a reference point. Returns a number of new solutions
    corresponding to the number of scalarization functions solved.

    Depending on `num_desired`, solves the following scalarized problems corresponding
    the the following scalarization functions:

    1.  the NIMBUS scalarization function,
    2.  the STOM scalarization function,
    3.  the achievement scalarizing function, and
    4.  the GUESS scalarization function.

    Raises:
        NimbusError: the given problem has an undefined ideal or nadir point, or both.
        NimbusError: either the reference point of current objective functions value are
            missing entries for one or more of the objective functions defined in the problem.

    Args:
        problem (Problem): the problem being solved.
        current_objectives (dict[str, float]): an objective dictionary with the objective functions values
            the classifications have been given with respect to.
        reference_point (dict[str, float]): an objective dictionary with a reference point.
            The classifications utilized in the sub problems are derived from
            the reference point.
        num_desired (int): the number of desired solutions to be solved. Solves as
            many scalarized problems. The value must be in the range 1-4.
        scalarization_options (dict | None, optional): optional kwargs passed to the scalarization function.
            Defaults to None.
        create_solver (CreateSolverType | None, optional): a function that given a problem, will return a solver.
            If not given, an appropriate solver will be automatically determined based on the features of `problem`.
            Defaults to None.
        solver_options (SolverOptions | None, optional): optional options passed
            to the `create_solver` routine. Ignored if `create_solver` is `None`.
            Defaults to None.

    Returns:
        list[SolverResults]: a list of `SolverResults` objects. Contains as many elements
            as defined in `num_desired`.
    """
    if None in problem.get_ideal_point() or None in problem.get_nadir_point():
        msg = "The given problem must have both an ideal and nadir point defined."
        raise NimbusError(msg)

    for reference_point in reference_points:
        if not all(obj.symbol in reference_point for obj in problem.objectives):
            msg = f"The reference point {reference_point} is missing entries " "for one or more of the objective functions."
            raise NimbusError(msg)

        if not all(obj.symbol in current_objectives for obj in problem.objectives):
            msg = f"The current point {reference_point} is missing entries " "for one or more of the objective functions."
            raise NimbusError(msg)

    init_solver = create_solver if create_solver is not None else guess_best_solver(problem)
    _solver_options = solver_options if solver_options is not None else None

    # derive the classifications based on the reference point and and previous
    # objective function values
    classification_list = []
    for reference_point in reference_points:
        classification_list.append(infer_classifications(problem, current_objectives, reference_point))

    # TODO(gialmisi): this info should come from the problem
    is_smooth = True

    solutions = []

    # solve the nimbus scalarization problem, this is done always
    '''add_nimbus_sf = add_group_nimbus_sf_diff if is_smooth else add_group_nimbus_sf

    problem_w_nimbus, nimbus_target = add_nimbus_sf(
        problem, "nimbus_sf", classification_list, current_objectives, **(scalarization_options or {})
    )

    if _solver_options:
        nimbus_solver = init_solver(problem_w_nimbus, _solver_options)
    else:
        nimbus_solver = init_solver(problem_w_nimbus)

    solutions.append(nimbus_solver.solve(nimbus_target))'''

    # solve STOM
    add_stom_sf = add_group_stom_sf_diff if is_smooth else add_group_stom_sf

    problem_w_stom, stom_target = add_stom_sf(problem, "stom_sf", reference_points, **(scalarization_options or {}))
    if _solver_options:
        stom_solver = init_solver(problem_w_stom, _solver_options)
    else:
        stom_solver = init_solver(problem_w_stom)

    solutions.append(stom_solver.solve(stom_target))

    # solve ASF
    add_asf = add_group_asf_diff if is_smooth else add_group_asf

    problem_w_asf, asf_target = add_asf(problem, "asf", reference_points, **(scalarization_options or {}))

    if _solver_options:
        asf_solver = init_solver(problem_w_asf, _solver_options)
    else:
        asf_solver = init_solver(problem_w_asf)

    solutions.append(asf_solver.solve(asf_target))

    # solve GUESS
    add_guess_sf = add_group_guess_sf_diff if is_smooth else add_group_guess_sf

    problem_w_guess, guess_target = add_guess_sf(
        problem, "guess_sf", reference_points, **(scalarization_options or {})
    )

    if _solver_options:
        guess_solver = init_solver(problem_w_guess, _solver_options)
    else:
        guess_solver = init_solver(problem_w_guess)

    solutions.append(guess_solver.solve(guess_target))

    return solutions


def solve_intermediate_solutions(  # noqa: PLR0913
    problem: Problem,
    solution_1: dict[str, VariableType | list[VariableType]],
    solution_2: dict[str, VariableType | list[VariableType]],
    num_desired: int,
    scalarization_options: dict | None = None,
    create_solver: BaseSolver | None = None,
    solver_options: SolverOptions | None = None,
) -> list[SolverResults]:
    """Generates a desired number of intermediate solutions between two given solutions.

    Generates a desires number of intermediate solutions given two Pareto optimal solutions.
    The solutions are generated by taking n number of steps between the two solutions in the
    objective space. The objective vectors corresponding to these solutions are then
    utilized as reference points in the achievement scalarizing function. Solving the functions
    for each reference point will project the reference point on the Pareto optimal
    front of the problem. These projected solutions are then returned. Note that the
    intermediate solutions are generated _between_ the two given solutions, this means the
    returned solutions will not include the original points.

    Args:
        problem (Problem): the problem being solved.
        solution_1 (dict[str, VariableType | list[VariableType]]): the first of the solutions between which the intermediate
            solutions are to be generated.
        solution_2 (dict[str, VariableType | list[VariableType]]): the second of the solutions between which the intermediate
            solutions are to be generated.
        num_desired (int): the number of desired intermediate solutions to be generated. Must be at least `1`.
        scalarization_options (dict | None, optional): optional kwargs passed to the scalarization function.
            Defaults to None.
        create_solver (CreateSolverType | None, optional): a function that given a problem, will return a solver.
            If not given, an appropriate solver will be automatically determined based on the features of `problem`.
            Defaults to None.
        solver_options (SolverOptions | None, optional): optional options passed
            to the `create_solver` routine. Ignored if `create_solver` is `None`.
            Defaults to None.

    Returns:
        list[SolverResults]: a list with the projected intermediate solutions as
            `SolverResults` objects.
    """
    if int(num_desired) < 1:
        msg = f"The given number of desired intermediate ({num_desired=}) solutions must be at least 1."
        raise NimbusError(msg)

    init_solver = guess_best_solver(problem) if create_solver is None else create_solver
    _solver_options = None if solver_options is None or create_solver is None else solver_options

    # compute the element-wise difference between each solution (in the decision space)
    solution_1_arr = variable_dict_to_numpy_array_as_group(problem, solution_1)
    solution_2_arr = variable_dict_to_numpy_array_as_group(problem, solution_2)
    delta = solution_1_arr - solution_2_arr

    # the '2' is in the denominator because we want to calculate the steps
    # between the two given points; we are not interested in the given points themselves.
    step_size = delta / (2 + num_desired)

    intermediate_points = np.array([solution_2_arr + i * step_size for i in range(1, num_desired + 1)])

    xs = {f"{variable.symbol}": intermediate_points[:, i].tolist() for (i, variable) in enumerate(problem.variables)}

    # evaluate the intermediate points to get reference points
    # TODO(gialmisi): an evaluator might have to be selected depending on the problem

    if isinstance(list(solution_1.values())[0], list):
        # TODO: evaluator for solutions with list of VariableType
        reference_points = [{'f_1': 2.1330502713915447, 'f_2': 2.014950917318272, 'f_3': 1.2630304116362192}]
    else:
        evaluator = GenericEvaluator(problem)

        reference_points: list[dict[str, float]] = (
            evaluator.evaluate(xs).select([obj.symbol for obj in problem.objectives]).to_dicts()
        )

    # for each reference point, add and solve the ASF scalarization problem
    # projecting the reference point onto the Pareto optimal front of the problem.
    # TODO(gialmisi): this can be done in parallel.
    intermediate_solutions = []
    for rp in reference_points:
        # add scalarization
        # TODO(gialmisi): add logic that selects correct variant of the ASF
        # depending on problem properties (either diff or non-diff)
        #asf_problem, target = add_asf_nondiff(problem, "target", rp, **(scalarization_options or {}))
        asf_problem, target = add_group_asf_diff(problem, "target", [rp], **(scalarization_options or {}))

        if _solver_options:
            solver = init_solver(asf_problem, _solver_options)
        else:
            solver = init_solver(asf_problem)

        # solve and store results
        result: SolverResults = solver.solve(target)

        intermediate_solutions.append(result)

    return intermediate_solutions