"""Functions related to the GNIMBUS method.

References:
TBA
"""

from typing import Literal

import numpy as np

from desdeo.gdm.gdmtools import agg_aspbounds, dict_of_rps_to_list_of_rps, scale_delta
from desdeo.gdm.voting_rules import plurality_rule
from desdeo.mcdm.nimbus import infer_classifications, solve_sub_problems
from desdeo.problem import (
    Problem,
)
from desdeo.tools import (
    BaseSolver,
    SolverOptions,
    SolverResults,
    GurobipySolver,
    add_group_asf,
    add_group_asf_agg,
    add_group_asf_agg_diff,
    add_group_asf_diff,
    add_group_guess,
    add_group_guess_agg,
    add_group_guess_agg_diff,
    add_group_guess_diff,
    add_group_nimbus,
    add_group_nimbus_compromise,
    add_group_nimbus_compromise_diff,
    add_group_nimbus_diff,
    add_group_stom,
    add_group_stom_agg,
    add_group_stom_agg_diff,
    add_group_stom_diff,
    guess_best_solver,
)


class GNIMBUSError(Exception):
    """Raised when an error with a NIMBUS method is encountered."""


def voting_procedure(problem: Problem, solutions, votes_idxs: dict[str, int]) -> SolverResults:
    """More general procedure for GNIMBUS for any number of DMs.
    TODO(@jpajasmaa): docs and cleaning up.
    """
    # winner_idx = None
    # call majority
    """ general procedure does not apply majority rule
    winner_idx = majority_rule(votes_idxs)
    if winner_idx is not None:
        print("Majority winner", winner_idx)
        return solutions[winner_idx]
    """
    # call plurality
    winners = plurality_rule(votes_idxs)
    print("winners")
    if len(winners) == 1:
        print("Plurality winner", winners[0])
        return solutions[winners[0]]  # need to unlist the winners list

    print("TIE-breaking, select a solution randomly among top voted ones")
    """
        # if two same solutions with same number of votes, call intermediate
        # TODO:(@jpajasmaa) not perfect check as it is possible to have a problem that we can calculate more solutions
        # AND discrete representation also.
        if problem.discrete_representation is None:
            wsol1, wsol2 = solutions[winners[0]].optimal_variables, solutions[winners[1]].optimal_variables
        else:
            wsol1, wsol2 = solutions[winners[0]].optimal_objectives, solutions[winners[1]].optimal_objectives
        print("Finding intermediate solution between", wsol1, wsol2)
        # return solve_intermediate_solutions_only_objs(problem, wsol1, wsol2, num_desired=3)
        return solve_intermediate_solutions(problem, wsol1, wsol2, num_desired=1)[0]
    """
    # n_of_sols = len(solutions)
    rng = np.random.default_rng()
    random_idx = rng.choice(winners)
    return solutions[random_idx]


def infer_group_classifications(
    problem: Problem,
    current_objectives: dict[str, float],
    reference_points: dict[str, dict[str, float]],
    *,
    silent: bool = True,
) -> dict[str, tuple[Literal["improve", "worsen", "conflict"], list[float]]]:
    """Infers group classification from the reference points given by the group.

    Args:
        problem (Problem): the problem being solved
        current_objectives (dict[str, float]): objective values at the current iteration
        reference_points (dict[str, dict[str, float]]): The reference points given by the group.
            The keys of the outer dict are the decision makers and the keys of the inner dict are objective symbols.
        silent (bool): If false, the classifications will be printed.

    Raises:
        GNIMBUSError: _description_

    Returns:
        dict[str, tuple[str, list[float]]]: _description_
    """
    for dm, reference_point in reference_points.items():
        # for rp in reference_point:
        if not all(obj.symbol in reference_point for obj in problem.objectives):
            print(reference_point)
            msg = (
                f"The reference point {reference_point} of {dm} is missing entries "
                "for one or more of the objective functions."
            )
            raise GNIMBUSError(msg)

    group_classifications = {}
    for obj in problem.objectives:
        # maximization
        if obj.maximize and all(
            (
                reference_points[dm][obj.symbol] >= current_objectives[obj.symbol]
                or np.isclose(reference_points[dm][obj.symbol], current_objectives[obj.symbol])
            )
            for dm in reference_points
        ):
            classify = "improve"
        elif obj.maximize and all(
            reference_points[dm][obj.symbol] < current_objectives[obj.symbol] for dm in reference_points
        ):
            classify = "worsen"
        # minimization
        elif (not obj.maximize) and all(
            (
                reference_points[dm][obj.symbol] <= current_objectives[obj.symbol]
                or np.isclose(reference_points[dm][obj.symbol], current_objectives[obj.symbol])
            )
            for dm in reference_points
        ):
            classify = "improve"
        elif (not obj.maximize) and all(
            reference_points[dm][obj.symbol] > current_objectives[obj.symbol] for dm in reference_points
        ):
            classify = "worsen"
        else:
            classify = "conflict"
        group_classifications[obj.symbol] = (classify, [reference_points[dm][obj.symbol] for dm in reference_points])

        if not silent:
            for symbol, value in group_classifications.items():
                if value[0] == "improve":
                    print(f"The group wants to improve objective {symbol}")
                    print(value[1])
                if value[0] == "worsen":
                    print(f"The group wants to worsen objective {symbol}")
                    print(value[1])
                if value[0] == "conflict":
                    print(f"The group has conflicting views about objective {symbol}")
                    print(value[1])

    return group_classifications


def solve_group_sub_problems(  # noqa: PLR0913, RET503
    problem: Problem,
    current_objectives: dict[str, float],
    reference_points: dict[str, dict[str, float]],
    phase: str,
    scalarization_options: dict | None = None,
    create_solver: BaseSolver | None = None,
    solver_options: SolverOptions | None = None,
) -> list[SolverResults]:
    r"""Solves a number of sub-problems as defined in the GNIMBUS methods.

    TODO: update docs

    Solves 4 scalarized problems utilizing different scalarization
    functions. The scalarizations are based on the classification of a
    solutions provided by a decision maker. The classifications
    are represented by a reference point. Returns a number of new solutions
    corresponding to the number of scalarization functions solved.

    Solves the following scalarized problems corresponding
    the the following scalarization functions:

    1.  the NIMBUS scalarization function,
    2.  the STOM scalarization function,
    3.  the achievement scalarizing function, and
    4.  the GUESS scalarization function.

    Raises:
        GNIMBUSError: the given problem has an undefined ideal or nadir point, or both.
        GNIMBUSError: either the reference point of current objective functions value are
            missing entries for one or more of the objective functions defined in the problem.

    Args:
        problem(Problem): the problem being solved.
        current_objectives(dict[str, float]): an objective dictionary with the objective functions values
            the classifications have been given with respect to.
        reference_points(dict[str, dict[str, float]]): A dictionary containing an objective dictionary with a reference point for each DM.
            The classifications utilized in the sub problems are derived from
            the reference points.
        phase(str): The selected phase of the solution process. Must be one of "learning", "crp", "decision" or "compromise".
        scalarization_options(dict | None, optional): optional kwargs passed to the scalarization function.
            Defaults to None.
        create_solver(CreateSolverType | None, optional): a function that given a problem, will return a solver.
            If not given, an appropriate solver will be automatically determined based on the features of `problem`.
            Defaults to None.
        solver_options(SolverOptions | None, optional): optional options passed
            to the `create_solver` routine. Ignored if `create_solver` is `None`.
            Defaults to None.

    Returns:
        list[SolverResults]: a list of `SolverResults` objects. Contains as many elements
            as defined in `num_desired`.
    """
    if None in problem.get_ideal_point() or None in problem.get_nadir_point():
        msg = "The given problem must have both an ideal and nadir point defined."
        raise GNIMBUSError(msg)

    DMs = reference_points.keys()
    for dm in DMs:
        reference_point = reference_points[dm]
        # for rp in reference_point:
        if not all(obj.symbol in reference_point for obj in problem.objectives):
            print(reference_point)
            msg = (
                f"The reference point {reference_point} is missing entries for one or more of the objective functions."
            )
            raise GNIMBUSError(msg)
        # check that at least one objective function is allowed to be improved and one is allowed to worsen
        classifications = infer_classifications(problem, current_objectives, reference_point)
        if not any(classifications[obj.symbol][0] in ["<", "<="] for obj in problem.objectives) or not any(
            classifications[obj.symbol][0] in [">=", "0"] for obj in problem.objectives
        ):
            msg = (
                f"The given classifications {classifications} should allow at least one objective function value "
                "to improve and one to worsen."
            )
            raise GNIMBUSError(msg)

    if not all(obj.symbol in current_objectives for obj in problem.objectives):
        msg = f"The current point {current_objectives} is missing entries for one or more of the objective functions."
        raise GNIMBUSError(msg)

    init_solver = create_solver if create_solver is not None else guess_best_solver(problem)
    if init_solver is GurobipySolver and not solver_options:
        solver_options = {"OutputFlag": 0} #TODO: how does one want this to behave?
    _solver_options = solver_options if solver_options is not None else None
    # print("solver is ", init_solver)

    solutions = []
    classification_list = []
    achievable_prefs = []

    ind_sols = []
    reference_points_list = dict_of_rps_to_list_of_rps(reference_points)

    # Solve for individual solutions using nimbus scalarization.
    for dm_rp in reference_points:
        ind_sols.append(solve_sub_problems(
            problem=problem,
            current_objectives=current_objectives,
            reference_point=reference_points[dm_rp],
            num_desired=1,
            scalarization_options=None,
            solver=init_solver,
            solver_options=_solver_options)[0],
        )

    achievable_prefs = []
    for q in range(len(reference_points)):
        achievable_prefs.append(ind_sols[q].optimal_objectives)

    agg_aspirations, agg_bounds = agg_aspbounds(achievable_prefs, problem)
    delta = scale_delta(problem, d=1e-6)

    if phase == "decision":
        for dm_rp in reference_points:
            classification_list.append(infer_classifications(problem, current_objectives, reference_points[dm_rp]))
        gnimbus_scala = add_group_nimbus_diff if problem.is_twice_differentiable else add_group_nimbus
        add_nimbus_sf = gnimbus_scala

        problem_g_nimbus, gnimbus_target = add_nimbus_sf(
            problem, "nimbus_sf", classification_list, current_objectives, agg_bounds, delta, **(scalarization_options or {})
        )

        if _solver_options:
            gnimbus_solver = init_solver(problem_g_nimbus, _solver_options)  # type:ignore
        else:
            gnimbus_solver = init_solver(problem_g_nimbus)  # type:ignore

        solutions.append(gnimbus_solver.solve(gnimbus_target))

        infer_group_classifications(problem, current_objectives, reference_points, silent=False)

        return solutions

    elif phase == "compromise":
        # Run compromise phase with applying group-asf.
        reference_points_list = dict_of_rps_to_list_of_rps(reference_points)
        # solve ASF
        add_asf = add_group_asf_diff if problem.is_twice_differentiable else add_group_asf
        problem_w_asf, asf_target = add_asf(
            problem, "asf", reference_points_list, agg_bounds, delta, **(scalarization_options or {})
        )
        if _solver_options:
            asf_solver = init_solver(problem_w_asf, _solver_options)  # type:ignore
        else:
            asf_solver = init_solver(problem_w_asf)  # type:ignore

        solutions.append(asf_solver.solve(asf_target))

        return solutions

        """
        classification_list = infer_group_classifications(problem, current_objectives, reference_points)
        # All cool, the preference's are in a bit of a different format that other branches but works.

        gnimbus_scala = add_group_nimbus_compromise_diff \
            if problem.is_twice_differentiable else add_group_nimbus_compromise
        add_nimbus_sf = gnimbus_scala

        problem_g_nimbus, gnimbus_target = add_nimbus_sf(
            problem, "nimbus_sf", classification_list, current_objectives, **(scalarization_options or {})
        )
        # ISSUE: makes the problem not twice differentiable, thus the initial solver doesn't work
        # Also needed a little tweaking inside the scalarization functions.

        if _solver_options:
            gnimbus_solver = init_solver(problem_g_nimbus, _solver_options)  # type:ignore
        else:
            gnimbus_solver = init_solver(problem_g_nimbus)  # type:ignore

        solutions.append(gnimbus_solver.solve(gnimbus_target))

        infer_group_classifications(problem, current_objectives, reference_points, silent=False)

        return solutions
        """

    elif phase == "learning":
        reference_points_list = dict_of_rps_to_list_of_rps(reference_points)

        # Add individual solutions
        for i in range(len(ind_sols)):
            solutions.append(ind_sols[i])
        """ Group nimbus scalarization with delta and added hard_constraints  """
        classification_list = []
        for dm_rp in reference_points:
            classification_list.append(infer_classifications(problem, current_objectives, reference_points[dm_rp]))
        print(classification_list)
        gnimbus_scala = add_group_nimbus_diff if problem.is_twice_differentiable else add_group_nimbus
        add_nimbus_sf = gnimbus_scala

        problem_w_nimbus, nimbus_target = add_nimbus_sf(
            problem,
            "nimbus_sf",
            classification_list,
            current_objectives,
            agg_bounds,
            delta,
            **(scalarization_options or {}),
        )

        if _solver_options:
            nimbus_solver = init_solver(problem_w_nimbus, _solver_options)  # type:ignore
        else:
            nimbus_solver = init_solver(problem_w_nimbus)  # type:ignore

        solutions.append(nimbus_solver.solve(nimbus_target))

        """ SOLVING Group Scals with scaled delta, original RPs and hard_constraints """
        # solve STOM
        add_stom_sf = add_group_stom_diff if problem.is_twice_differentiable else add_group_stom
        problem_w_stom, stom_target = add_stom_sf(
            problem, "stom_sf", reference_points_list, agg_bounds, delta, **(scalarization_options or {})
        )
        if _solver_options:
            stom_solver = init_solver(problem_w_stom, _solver_options)  # type:ignore
        else:
            stom_solver = init_solver(problem_w_stom)  # type:ignore

        solutions.append(stom_solver.solve(stom_target))

        # solve ASF
        add_asf = add_group_asf_diff if problem.is_twice_differentiable else add_group_asf
        problem_w_asf, asf_target = add_asf(
            problem, "asf", reference_points_list, agg_bounds, delta, **(scalarization_options or {})
        )
        if _solver_options:
            asf_solver = init_solver(problem_w_asf, _solver_options)  # type:ignore
        else:
            asf_solver = init_solver(problem_w_asf)  # type:ignore

        solutions.append(asf_solver.solve(asf_target))

        # Solve GUESS
        add_guess_sf = add_group_guess_diff if problem.is_twice_differentiable else add_group_guess
        problem_w_guess, guess_target = add_guess_sf(
            problem, "guess_sf", reference_points_list, agg_bounds, delta, **(scalarization_options or {})
        )
        if _solver_options:
            guess_solver = init_solver(problem_w_guess, _solver_options)  # type:ignore
        else:
            guess_solver = init_solver(problem_w_guess)  # type:ignore

        solutions.append(guess_solver.solve(guess_target))

        infer_group_classifications(problem, current_objectives, reference_points, silent=False)

        return solutions

    else:  # phase is concsensus reaching
        # Add individual solutions
        for i in range(len(ind_sols)):
            solutions.append(ind_sols[i])

        """ Group nimbus scalarization with delta and added hard_constraints  """
        classification_list = []
        for dm_rp in reference_points:
            print("RPS", reference_points[dm_rp])
            classification_list.append(infer_classifications(problem, current_objectives, reference_points[dm_rp]))
        print(classification_list)
        gnimbus_scala = add_group_nimbus_diff if problem.is_twice_differentiable else add_group_nimbus
        add_nimbus_sf = gnimbus_scala

        problem_w_nimbus, nimbus_target = add_nimbus_sf(
            problem,
            "nimbus_sf",
            classification_list,
            current_objectives,
            agg_bounds,
            delta,
            **(scalarization_options or {}),
        )

        if _solver_options:
            nimbus_solver = init_solver(problem_w_nimbus, _solver_options)  # type:ignore
        else:
            nimbus_solver = init_solver(problem_w_nimbus)  # type:ignore

        solutions.append(nimbus_solver.solve(nimbus_target))

        """ SOLVING Group Scals with scaled delta, agg. aspirations and hard_constraints """

        add_stom_sf2 = add_group_stom_agg_diff if problem.is_twice_differentiable else add_group_stom_agg

        problem_g_stom, stomg_target = add_stom_sf2(
            problem, "stom_sf2", agg_aspirations, agg_bounds, delta, **(scalarization_options or {})
        )
        if _solver_options:
            stomg_solver = init_solver(problem_g_stom, _solver_options)  # type:ignore
        else:
            stomg_solver = init_solver(problem_g_stom)  # type:ignore

        solutions.append(stomg_solver.solve(stomg_target))

        add_asf2 = add_group_asf_agg_diff if problem.is_twice_differentiable else add_group_asf_agg
        problem_g_asf, asfg_target = add_asf2(
            problem, "asf2", agg_aspirations, agg_bounds, delta, **(scalarization_options or {})
        )
        if _solver_options:
            asfg_solver = init_solver(problem_g_asf, _solver_options)  # type:ignore
        else:
            asfg_solver = init_solver(problem_g_asf)  # type:ignore

        solutions.append(asfg_solver.solve(asfg_target))

        add_guess_sf2 = add_group_guess_agg_diff if problem.is_twice_differentiable else add_group_guess_agg

        problem_g_guess, guess2_target = add_guess_sf2(
            problem, "guess_sf2", agg_aspirations, agg_bounds, delta, **(scalarization_options or {})
        )

        if _solver_options:
            guess2_solver = init_solver(problem_g_guess, _solver_options)  # type:ignore
        else:
            guess2_solver = init_solver(problem_g_guess)  # type:ignore

        solutions.append(guess2_solver.solve(guess2_target))

        infer_group_classifications(problem, current_objectives, reference_points, silent=False)

        return solutions