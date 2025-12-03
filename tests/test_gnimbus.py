"""Tests related to the GNIMBUS method."""

import numpy as np
import numpy.testing as npt
import pytest

from desdeo.gdm.gdmtools import dict_of_rps_to_list_of_rps, list_of_rps_to_dict_of_rps, agg_aspbounds, scale_delta
from desdeo.gdm.voting_rules import majority_rule, plurality_rule
from desdeo.mcdm.gnimbus import (
    GNIMBUSError,
    infer_group_classifications,
    solve_group_sub_problems,
    voting_procedure,
)
from desdeo.mcdm.nimbus import generate_starting_point
from desdeo.problem.testproblems import dtlz2, nimbus_test_problem, re22, simple_knapsack_vectors, zdt1
from desdeo.tools import IpoptOptions, PyomoIpoptSolver, add_asf_diff


@pytest.mark.gdmtools
def test_dict_to_list_and_back():
    """Verify conversion between dict-of-reference-points and list-of-reference-points.

    This test ensures `dict_of_rps_to_list_of_rps` returns a list of dictionaries
    with correct types and that `list_of_rps_to_dict_of_rps` reconstructs the
    original dictionary structure.
    """
    rps = {
        "DM1": {"f_1": 0.0, "f_2": 0.5, "f_3": 1.0},
        "DM2": {"f_1": 0.0, "f_2": 1.0, "f_3": 0.5},
        "DM3": {"f_1": 0.5, "f_2": 1.0, "f_3": 0.0},
    }
    result = dict_of_rps_to_list_of_rps(rps)
    print(result)  # results look resonable
    # Check if the result is a list, testing AI overlords code, seems decent
    assert isinstance(result, list)
    # If it's a list, iterate through its items
    for item in result:
        # Check if each item is a dictionary
        assert isinstance(item, dict)
        # If it's a dictionary, iterate through its key-value pairs
        for key, value in item.items():
            # Check if the key is a string and the value is a float
            assert isinstance(key, str)
            assert isinstance(value, float)
    back_to = list_of_rps_to_dict_of_rps(result)
    print(back_to)
    # First, check if the top-level result is a dictionary.
    assert isinstance(back_to, dict)
    # Then, iterate through the outer dictionary's key-value pairs.
    for key, value in back_to.items():
        # Check that each key is a string.
        assert isinstance(key, str)
        # Check that each value is a dictionary.
        assert isinstance(value, dict)
        # Now, iterate through the inner dictionary's key-value pairs.
        for inner_key, inner_value in value.items():
            # Check that each inner key is a string.
            assert isinstance(inner_key, str)
            # Check that each inner value is a float.
            assert isinstance(inner_value, float)


# @pytest.mark.skip
@pytest.mark.gnimbus
def test_voting_procedure():
    """Exercise the voting procedure for GNIMBUS.

    This test prepares a small problem and a set of candidate solutions produced
    by `solve_group_sub_problems`, then exercises `voting_procedure` with
    different vote distributions to validate majority, plurality and
    intermediate-tie behaviours.
    """
    problem = dtlz2(8, 3)

    solver_options = IpoptOptions()
    # get some initial solution
    initial_rp = {"f_1": 0.4, "f_2": 0.5, "f_3": 0.8}
    problem_w_sf, target = add_asf_diff(problem, "target", initial_rp)
    solver = PyomoIpoptSolver(problem_w_sf, solver_options)
    initial_result = solver.solve(target)

    # f1: 0.385, f2: 0.485, f3: 0.776
    initial_fs = initial_result.optimal_objectives

    print(initial_fs)
    # let f1 worsen until 0.6, keep f2, improve f3 until 0.6
    # irst_rp = {"f_1": 0.6, "f_2": initial_fs["f_2"], "f_3": 0.6}
    dms_rps = {
        "DM1": {"f_1": 0.35, "f_2": initial_fs["f_2"], "f_3": 1},  # improve f_1, keep f_2 same, impair f_3
        "DM2": {"f_1": 0.3, "f_2": 0.8, "f_3": 0.5},  # improve f_1 to 0.3, impair f_2, improve f_3 to 0.5
        "DM3": {"f_1": 0.5, "f_2": 0.6, "f_3": 0.0},  # impair f_1 to 0.5, impair f_2 to 0.6, improve f_3
    }

    solution_results = solve_group_sub_problems(
        problem, initial_fs, dms_rps, "learning", create_solver=PyomoIpoptSolver, solver_options=solver_options
    )
    voted_solutions = solution_results

    # TEST PLURALITY WINS
    # make different votes
    votes_idxs = {"DM1": 1, "DM2": 2, "DM3": 2, "DM4": 0}
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    assert res == solution_results[2]
    next_current_solution = res.optimal_objectives
    print(next_current_solution)

    # TEST random among 2 top voted
    votes_idxs = {"DM1": 1, "DM2": 2, "DM3": 2, "DM4": 1}
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    assert res == solution_results[1] or res == solution_results[2]
    next_current_solution = res.optimal_objectives
    print(next_current_solution)

    # TEST random among 3 top voted
    votes_idxs = {"DM1": 0, "DM2": 0, "DM3": 1, "DM4": 1, "DM5": 2, "DM6": 2}
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    assert res == solution_results[0] or res == solution_results[1] or res == solution_results[2]
    assert res != solution_results[3]
    next_current_solution = res.optimal_objectives
    print(next_current_solution)

    # TEST random among 4 top voted
    votes_idxs = {"DM1": 0, "DM2": 3, "DM3": 2, "DM4": 1}
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    assert res == solution_results[0] or res == solution_results[1] or res == solution_results[2] or res == solution_results[3]
    next_current_solution = res.optimal_objectives
    print(next_current_solution)

    """
    # TEST PLULARITY WINS
    # make different votes
    votes_idxs = {"DM1": 1, "DM2": 0, "DM3": 0, "DM4": 3, "DM5": 2}
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    print("here", res)
    assert res == solution_results[0]
    next_current_solution = res.optimal_objectives
    print(next_current_solution)
    """

    """
    # TEST intermediate
    votes_idxs = {"DM1": 0, "DM2": 0, "DM3": 2, "DM4": 2}
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    next_current_solution = res.optimal_objectives
    print(next_current_solution)

    # TEST according to gnimbus WINS
    votes_idxs = {"DM1": 1, "DM2": 0, "DM3": 2}
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    print(res)
    print(solution_results[0])
    assert res == solution_results[0]  # for now tie-breaking rule is taking the first one. Error what?

    next_current_solution = res.optimal_objectives
    print(next_current_solution)
    """

@pytest.mark.gnimbus
@pytest.mark.slow
def test_solve_sub_problems_nondiff():
    """
    Test that the scalarization problems in GNIMBUS are solved as expected.

    TODO: get a correct ideal and nadir or some other non-diff problem for results to make sense.
    """
    problem = re22()
    # problem = simple_knapsack_vectors()
    from desdeo.tools import payoff_table_method

    # ideal, nadir = payoff_table_method(problem)

    ideal = {"f_1": 5.88, "f_2": 0}
    nadir = {"f_1": 361.262944647, "f_2": 180.01547}
    print("ideal", ideal)
    print(nadir)

    problem = problem.update_ideal_and_nadir(ideal, nadir)

    # initial_rp = generate_starting_point(problem)  # Why this is so bad
    # initial_rp = {"f_1": 200, "f_2": 100}
    # print(initial_rp)

    # initial_fs = initial_rp.optimal_objectives
    initial_fs = {"f_1": 200, "f_2": 100}
    print(initial_fs)
    dms_rps = {
        "DM1": {"f_1": 300, "f_2": 40},
        "DM2": {"f_1": 210, "f_2": 1},
        "DM3": {"f_1": 10, "f_2": 120},
    }

    phase = "learning"
    solutions = solve_group_sub_problems(
        problem,
        initial_fs,
        dms_rps,
        phase,  # create_solver=PyomoIpoptSolver,  solver_options=solver_options
    )

    assert len(solutions) == len(dms_rps) + 4
    print("DMs solutions")
    print(solutions[0].optimal_objectives)
    print(solutions[1].optimal_objectives)
    print(solutions[2].optimal_objectives)
    print(solutions[3].optimal_objectives)
    print(solutions[4].optimal_objectives)
    print(solutions[5].optimal_objectives)
    print(solutions[6].optimal_objectives)


@pytest.mark.gnimbus
@pytest.mark.slow
def test_solve_sub_problems_diff():
    """Test that the scalarization problems in GNIMBUS are solved as expected."""
    n_variables = 8
    n_objectives = 3

    problem = dtlz2(n_variables, n_objectives)

    solver_options = IpoptOptions()

    # get some initial solution
    initial_rp = {"f_1": 0.4, "f_2": 0.5, "f_3": 0.8}
    problem_w_sf, target = add_asf_diff(problem, "target", initial_rp)
    solver = PyomoIpoptSolver(problem_w_sf, solver_options)
    initial_result = solver.solve(target)

    # f1: 0.385, f2: 0.485, f3: 0.776
    initial_fs = initial_result.optimal_objectives

    print(initial_fs)
    # let f1 worsen until 0.6, keep f2, improve f3 until 0.6
    # irst_rp = {"f_1": 0.6, "f_2": initial_fs["f_2"], "f_3": 0.6}
    dms_rps = {
        "DM1": {"f_1": 0.0, "f_2": initial_fs["f_2"], "f_3": 1},  # improve f_1, keep f_2 same, impair f_3
        "DM2": {"f_1": 0.3, "f_2": 1, "f_3": 0.5},  # improve f_1 to 0.3, impair f_2, improve f_3 to 0.5
        "DM3": {"f_1": 0.5, "f_2": 0.6, "f_3": 0.0},  # impair f_1 to 0.5, impair f_2 to 0.6, improve f_3
    }

    phase = "learning"
    solutions = solve_group_sub_problems(
        problem, initial_fs, dms_rps, phase, create_solver=PyomoIpoptSolver, solver_options=solver_options
    )

    assert len(solutions) == 4 + len(dms_rps)
    print(solutions[0].optimal_objectives)
    print(solutions[1].optimal_objectives)
    print(solutions[2].optimal_objectives)
    print(solutions[3].optimal_objectives)
    print(solutions[4].optimal_objectives)
    print(solutions[5].optimal_objectives)
    print(solutions[6].optimal_objectives)

    phase = "crp"
    solutions = solve_group_sub_problems(
        problem, initial_fs, dms_rps, phase, create_solver=PyomoIpoptSolver, solver_options=solver_options
    )

    assert len(solutions) == 4 + len(dms_rps)
    print(solutions[0].optimal_objectives)
    print(solutions[1].optimal_objectives)
    print(solutions[2].optimal_objectives)
    print(solutions[3].optimal_objectives)
    print(solutions[4].optimal_objectives)
    print(solutions[5].optimal_objectives)
    print(solutions[6].optimal_objectives)

    phase = "decision"
    solutions = solve_group_sub_problems(
        problem, initial_fs, dms_rps, phase, create_solver=PyomoIpoptSolver, solver_options=solver_options
    )

    assert len(solutions) == 1
    print(solutions[0].optimal_objectives)

    phase = "compromise"
    solutions = solve_group_sub_problems(
        problem, initial_fs, dms_rps, phase, create_solver=PyomoIpoptSolver, solver_options=solver_options
    )

    assert len(solutions) == 1
    print(solutions[0].optimal_objectives)

    non_valid_rps = {
        "DM1": {"f_1": 0.0, "f_2": initial_fs["f_2"], "f_3": 0},  # improve f_1, keep f_2 same, impair f_3
        "DM2": {"f_1": 0.3, "f_2": 0.0, "f_3": 0.5},  # improve f_1 to 0.3, impair f_2, improve f_3 to 0.5
        "DM3": {"f_1": 0.15, "f_2": 0.16, "f_3": 0.0},  # impair f_1 to 0.5, impair f_2 to 0.6, improve f_3
    }

    phase = "learning"
    with pytest.raises(Exception) as e_info:
        solutions = solve_group_sub_problems(
            problem, initial_fs, non_valid_rps, phase, create_solver=PyomoIpoptSolver, solver_options=solver_options
        )


def test_infer_group_classifications_improve_worsen_conflict():
    """Unit tests for `infer_group_classifications` covering improve/worsen/conflict.

    Creates a small synthetic scenario with two DMs' reference points and a
    chosen current objective vector. Checks that each objective is classified
    correctly as 'improve', 'worsen' or 'conflict', and that reported values
    correspond to the original reference points.
    """
    problem = nimbus_test_problem()

    # choose a current point similar to other tests
    current_objectives = {"f_1": 4.5, "f_2": 3.2, "f_3": -5.2, "f_4": -1.2, "f_5": 120.0, "f_6": 9001.0}

    # Construct two DMs' reference points such that:
    # - For f_1 (maximize): both rps >= current -> group wants to improve
    # - For f_2 (minimize): both rps <= current -> group wants to improve
    # - For f_3 (minimize): both rps > current -> group wants to worsen
    # - For f_4 (minimize): mixed -> conflict
    # - For f_5 (minimize): both rps < current -> improve
    # - For f_6 (minimize): both rps <= current -> improve (edge-case close)
    rp_dm1 = {"f_1": 6.0, "f_2": 2.0, "f_3": -3.0, "f_4": -2.0, "f_5": 100.0, "f_6": 9000.0}
    rp_dm2 = {"f_1": 5.0, "f_2": 1.0, "f_3": -4.0, "f_4": 0.0, "f_5": 80.0, "f_6": 8999.0}

    reference_points = {"dm1": rp_dm1, "dm2": rp_dm2}

    classifications = infer_group_classifications(problem, current_objectives, reference_points, silent=True)

    # Ensure we got a classification for each objective and a list of values per DM
    assert set(classifications.keys()) == set(obj.symbol for obj in problem.objectives)

    # f_1 maximize -> both rps are >= current => improve
    assert classifications["f_1"][0] == "improve"
    assert np.isclose(classifications["f_1"][1][0], rp_dm1["f_1"]) and np.isclose(
        classifications["f_1"][1][1], rp_dm2["f_1"]
    )

    # f_2 minimize -> both rps <= current => improve
    assert classifications["f_2"][0] == "improve"

    # f_3 minimize -> both rps > current => worsen
    assert classifications["f_3"][0] == "worsen"

    # f_4 -> conflicting views
    assert classifications["f_4"][0] == "conflict"

    # f_5 minimize -> both rps < current => improve
    assert classifications["f_5"][0] == "improve"

    # f_6 minimize -> both rps <= current => improve
    assert classifications["f_6"][0] == "improve"


def test_infer_group_classifications_missing_entry_raises():
    """Ensure `infer_group_classifications` raises when a DM's RP misses an objective.

    Constructs reference points where one DM is missing an objective entry and
    asserts that `GNIMBUSError` is raised.
    """
    problem = nimbus_test_problem()

    current_objectives = {"f_1": 1.0, "f_2": 2.0, "f_3": 3.0, "f_4": 4.0, "f_5": 5.0, "f_6": 6.0}

    # dm2 missing f_3
    rp_dm1 = {"f_1": 2.0, "f_2": 1.0, "f_3": 0.0, "f_4": 4.5, "f_5": 5.5, "f_6": 6.5}
    rp_dm2 = {"f_1": 2.5, "f_2": 1.5, "f_4": 4.1, "f_5": 5.1, "f_6": 6.1}

    reference_points = {"dm1": rp_dm1, "dm2": rp_dm2}

    with pytest.raises(GNIMBUSError):
        infer_group_classifications(problem, current_objectives, reference_points)
