"""Tests related to the GNIMBUS method."""

from desdeo.mcdm.nimbus import generate_starting_point
from desdeo.tools import IpoptOptions, PyomoIpoptSolver, add_asf_diff
from desdeo.problem.testproblems import dtlz2, nimbus_test_problem, zdt1, re22, simple_knapsack_vectors
import numpy as np
import numpy.testing as npt
import pytest

from desdeo.mcdm.gnimbus import (voting_procedure,
                                 solve_intermediate_solutions, solve_group_sub_problems,
                                 find_min_max_values, scale_delta)

from desdeo.gdm.voting_rules import majority_rule, plurality_rule
from desdeo.gdm.gdmtools import dict_of_rps_to_list_of_rps, list_of_rps_to_dict_of_rps


@pytest.mark.gdmtools
def test_dict_to_list_and_back():
    rps = {
        "DM1": {"f_1": 0.0, "f_2": 0.5, "f_3": 1.},
        "DM2": {"f_1": 0.0, "f_2": 1., "f_3": 0.5},
        "DM3": {"f_1": 0.5, "f_2": 1., "f_3": 0.0},
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

    problem = dtlz2(8, 3)

    solver_options = IpoptOptions()
    # get some initial solution
    initial_rp = {
        "f_1": 0.4, "f_2": 0.5, "f_3": 0.8
    }
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

    # TEST MAJORITY WINS
    # make different votes
    votes_idxs = {
        "DM1": 1,
        "DM2": 2,
        "DM3": 2
    }
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    assert res == solution_results[2]
    next_current_solution = res.optimal_objectives
    print(next_current_solution)

    # TEST PLULARITY WINS
    # make different votes
    votes_idxs = {
        "DM1": 1,
        "DM2": 0,
        "DM3": 0,
        "DM4": 3,
        "DM5": 2

    }
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    print("here", res)
    assert res == solution_results[0]
    next_current_solution = res.optimal_objectives
    print(next_current_solution)

    # TEST intermediate
    votes_idxs = {
        "DM1": 0,
        "DM2": 0,
        "DM3": 2,
        "DM4": 2
    }
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    next_current_solution = res.optimal_objectives
    print(next_current_solution)

    # TEST according to gnimbus WINS
    votes_idxs = {
        "DM1": 1,
        "DM2": 0,
        "DM3": 2
    }
    res = voting_procedure(problem, voted_solutions, votes_idxs)
    print(res)
    print(solution_results[0])
    assert res == solution_results[0]  # for now tie-breaking rule is taking the first one. Error what?
    next_current_solution = res.optimal_objectives
    print(next_current_solution)


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
        problem, initial_fs, dms_rps, phase,  # create_solver=PyomoIpoptSolver,  solver_options=solver_options
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
    initial_rp = {
        "f_1": 0.4, "f_2": 0.5, "f_3": 0.8
    }
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

    non_valid_rps = {
        "DM1": {"f_1": 0.0, "f_2": initial_fs["f_2"], "f_3": 0},  # improve f_1, keep f_2 same, impair f_3
        "DM2": {"f_1": 0.3, "f_2": 0.0, "f_3": 0.5},  # improve f_1 to 0.3, impair f_2, improve f_3 to 0.5
        "DM3": {"f_1": 0.15, "f_2": 0.16, "f_3": 0.0},  # impair f_1 to 0.5, impair f_2 to 0.6, improve f_3
    }

    phase = "learning"

    # pytest.raises(Exception)
    #    solutions=solve_group_sub_problems(
    #        problem, initial_fs, non_valid_rps, phase, create_solver=PyomoIpoptSolver, solver_options=solver_options
    #    )
    # )
    with pytest.raises(Exception) as e_info:
        solutions = solve_group_sub_problems(
            problem, initial_fs, non_valid_rps, phase, create_solver=PyomoIpoptSolver, solver_options=solver_options
        )
