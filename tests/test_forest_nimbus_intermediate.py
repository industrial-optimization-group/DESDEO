"""Test for generating intermediate solutions between NIMBUS solutions for the forest problem."""

import pytest

from desdeo.mcdm import solve_intermediate_solutions, solve_sub_problems
from desdeo.mcdm.nimbus import generate_starting_point
from desdeo.problem.testproblems import forest_problem
from desdeo.tools import GurobipySolver


@pytest.mark.forest_problem
@pytest.mark.gurobipy
@pytest.mark.intermediate
def test_forest_problem_nimbus_to_intermediate():
    """Test intermediate solutions between NIMBUS solutions for the forest problem.

    Purpose of workflow is to mimic one in nimbus UI.
    It is following:
    1. Create a forest problem using generate_starting_point
    2. Solve it with NIMBUS to get two different solutions
    3. Generate intermediate solutions between those two NIMBUS solutions
    """
    # Setup the forest problem
    problem = forest_problem(
        simulation_results="./data/alternatives_290124.csv",
        treatment_key="./data/alternatives_key_290124.csv",
        holding=1,
        comparing=True,
    )

    solver = GurobipySolver(problem)

    # Solve for each objective to find ideal and nadir
    f1_min_result = solver.solve("f_1_min")
    f2_min_result = solver.solve("f_2_min")
    f3_min_result = solver.solve("f_3_min")

    # Set ideal and nadir values manually for each objective
    # For a maximization problem, the ideal is the highest achievable value
    # and nadir is the lowest across all optimal solutions
    
    # First, collect all objective values
    objective_values = {
        "f_1": [f1_min_result.optimal_objectives["f_1"],
                f2_min_result.optimal_objectives["f_1"],
                f3_min_result.optimal_objectives["f_1"]],
        "f_2": [f1_min_result.optimal_objectives["f_2"],
                f2_min_result.optimal_objectives["f_2"],
                f3_min_result.optimal_objectives["f_2"]],
        "f_3": [f1_min_result.optimal_objectives["f_3"],
                f2_min_result.optimal_objectives["f_3"],
                f3_min_result.optimal_objectives["f_3"]]
    }

    # Calculate ideal and nadir values for each objective
    new_ideal = {obj.symbol: max(objective_values[obj.symbol]) for obj in problem.objectives}
    new_nadir = {obj.symbol: min(objective_values[obj.symbol]) for obj in problem.objectives}

    # Use the update_ideal_and_nadir method to create a new problem with updated values
    problem = problem.update_ideal_and_nadir(new_ideal, new_nadir)

    # Generate a starting point using NIMBUS initialization
    start_result = generate_starting_point(
        problem=problem,
        solver=GurobipySolver,
    )
    # Use the starting point as initial objectives
    initial_objectives = start_result.optimal_objectives

    # Create reference point focused on f_3 improvement
    ref_point = {
        "f_1": initial_objectives["f_1"] * 0.8,  # allow f_1 to worsen by 20%
        "f_2": initial_objectives["f_2"] * 0.9,  # allow f_2 to worsen by 10%
        "f_3": problem.objectives[2].ideal,      # improve f_3 to ideal level
    }

    # Generate two NIMBUS solutions for intermediate generation
    nimbus_solutions = solve_sub_problems(
        problem,
        initial_objectives,
        ref_point,
        2,  # Get two solutions
        solver=GurobipySolver,
    )

    # Verify we got solutions
    assert len(nimbus_solutions) == 2
    assert nimbus_solutions[0].success

    # Extract variable values from solutions
    solution_1 = nimbus_solutions[0].optimal_variables
    solution_2 = nimbus_solutions[1].optimal_variables

    # Verify solutions are different
    assert solution_1 != solution_2

    # Now generate intermediate solutions
    num_desired = 3
    
    intermediate_results = solve_intermediate_solutions(
        problem,
        solution_1,
        solution_2,
        num_desired,
        solver=GurobipySolver,
    )

    # Verify intermediate solutions
    assert len(intermediate_results) == num_desired

    for res in intermediate_results:
        # Check solution is valid
        assert res.success
        assert all(obj.symbol in res.optimal_objectives for obj in problem.objectives)
        assert all(var.symbol in res.optimal_variables for var in problem.variables)