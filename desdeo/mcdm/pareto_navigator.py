"""Functions related to the Pareto Navigator method are defined here.

Reference of the method:

Eskelinen, Petri, et al. "Pareto navigator for interactive nonlinear
multiobjective optimization." OR spectrum 32 (2010): 211-227.
"""

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull

from desdeo.problem import (
    Problem,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array
)


def classification_to_reference_point(
    problem: Problem,
    pref_info: dict[str, str],
    current_solution: dict[str, float]
) -> dict[str, float]:
    """Convert preference information given as classification into a reference point.

    Args:
        problem (Problem): The problem being solved.
        pref_info (dict[str, str]): The preference information given as classification.
        current_solution (dict[str, float]): The current solution.

    Returns:
        dict[str, float]: A reference point converted from classification.
    """
    ref = []
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()

    for pref in pref_info:
        if pref_info[pref] == "<":
            ref.append(ideal[pref])
        elif pref_info[pref] == ">":
            ref.append(nadir[pref])
        elif pref_info[pref] == "=":
            ref.append(current_solution[pref])

    return numpy_array_to_objective_dict(problem, np.array(ref))

def calculate_adjusted_speed(allowed_speeds: np.ndarray, speed: float, scalar: float | None = 20) -> float:
    """Calculate an adjusted speed from a given float.

    Note:
        Adjusting the speed is not specified in the article but seems necessary.

    Args:
        allowed_speeds (np.ndarray): An array of allowed speeds.
        speed (float): A given speed value where.
        scalar (float | None (optional)): A scale to adjust the speed. Defaults to 20.

    Returns:
        float: An adjusted speed value calculated from given float.
            Is between 0 and 1.
    """
    return (speed / np.max(allowed_speeds)) / scalar

def calculate_search_direction(
    problem: Problem,
    reference_point: dict[str, float],
    current_point: dict[str, float]
) -> dict[str, float]:
    """Calculate search direction from the current point to the reference point.

    Args:
        problem (Problem): The problem being solved.
        reference_point (dict[str, float]): The given reference point.
        current_point (dict[str, float]): Currently navigated point.

    Returns:
        dict[str, float]: The direction from the current point to the reference point.
    """
    z = objective_dict_to_numpy_array(problem, current_point)
    q = objective_dict_to_numpy_array(problem, reference_point)

    d = q - z
    return numpy_array_to_objective_dict(problem, d)

def get_polyhedral_set(problem: Problem) -> tuple[np.ndarray, np.ndarray]:
    """Get a polyhedral set as convex hull from the set of pareto optimal solutions.

    Args:
        problem (Problem): The problem being solved.

    Returns:
        tuple[np.ndarray, np.ndarray]: The A matrix and b vector from the polyhedral set equation.
    """
    objective_values = problem.discrete_representation.objective_values
    representation = np.array([objective_values[obj.symbol] for obj in problem.objectives])

    convex_hull = ConvexHull(representation.T)
    matrix_a = convex_hull.equations[:, 0:-1]
    b = -convex_hull.equations[:, -1]
    return matrix_a, b

def construct_matrix_a(problem: Problem, matrix_a: np.ndarray) -> np.ndarray:
    """Construct the A' matrix in the linear parametric programming problem from the article.

    Args:
        problem (Problem): The problem being solved.
        matrix_a (np.ndarray): The A matrix from the polyhedral set equation.

    Returns:
        np.ndarray: The A' matrix in the linear parametric programming problem from the article.
    """
    ideal = objective_dict_to_numpy_array(problem, problem.get_ideal_point())
    nadir = objective_dict_to_numpy_array(problem, problem.get_nadir_point())
    weights = 1/(nadir - ideal)

    weights_inverse = np.reshape(np.vectorize(lambda w: -1 / w)(weights), (len(weights), 1))
    identity = np.identity(len(weights))
    a_upper = np.c_[weights_inverse, identity]

    zeros = np.zeros((len(matrix_a), 1))
    a_lower = np.c_[zeros, matrix_a]

    return np.concatenate((a_upper, a_lower))

def calculate_next_solution( # NOQA: PLR0913
    problem: Problem,
    search_direction: dict[str, float],
    current_solution: dict[str, float],
    alpha: float,
    matrix_a: np.ndarray,
    b: np.ndarray
) -> dict[str, float]:
    """Calculate the next solution.

    Args:
        problem (Problem): The problem being solved.
        search_direction (dict[str, float]): The search direction.
        current_solution (dict[str, float]): The currently navigated point.
        alpha (float): Step size. Between 0 and 1.
        matrix_a (np.ndarray): The A' matrix.
        b (np.ndarray): The b vector.

    Returns:
        dict[str, float]: The next solution.
    """
    z = objective_dict_to_numpy_array(problem, current_solution)
    k = len(z)
    d = objective_dict_to_numpy_array(problem, search_direction)

    q = z + alpha * d
    q = np.reshape(q, ((k, 1)))

    b_new = np.append(q, b)

    ideal = objective_dict_to_numpy_array(problem, problem.get_ideal_point())
    nadir = objective_dict_to_numpy_array(problem, problem.get_nadir_point())

    c = np.array([1] + k * [0])

    obj_bounds = np.stack((ideal, nadir))
    bounds = [(None, None)]
    for x, y in obj_bounds.T:
        bounds.append((x, y))

    z_new = linprog(c=c, A_ub=matrix_a, b_ub=b_new, bounds=bounds)
    if z_new["success"]:
        return numpy_array_to_objective_dict(problem, z_new["x"][1:])
    return current_solution # should raise an exception instead

def calculate_all_solutions(
    problem: Problem,
    current_solution: dict[str, float],
    alpha: float,
    num_solutions: int,
    pref_info: dict
) -> list[dict[str, float]]:
    """Performs a set number of steps in the current direction.

    Args:
        problem (Problem): The problem being solved.
        current_solution (dict[str, float]): The current solution.
        alpha (float): Step size. Between 0 and 1.
        num_solutions (int): Number of solutions calculated.
        pref_info (dict): Preference information. Either "reference_point" or "classification".

    Returns:
        list[dict[str, float]]: A list of the computed solutions.
    """
    solution = current_solution

    # check if the preference information is given as a reference point or as classification
    # and calculate the search direction based on the preference information
    if "reference_point" in pref_info:
        reference_point = pref_info["reference_point"]
        d = calculate_search_direction(problem, reference_point, current_solution)
    elif "classification" in pref_info:
        reference_point = classification_to_reference_point(problem, pref_info["classification"], solution)
        d = calculate_search_direction(problem, reference_point, solution)

    # the A matrix and b vector from the polyhedral set equation
    matrix_a, b = get_polyhedral_set(problem)

    # the A' matrix from the linear parametric programming problem
    matrix_a_new = construct_matrix_a(problem, matrix_a)

    solutions: list[dict[str, float]] = []
    while len(solutions) < num_solutions:
        solution = calculate_next_solution(problem, d, solution, alpha, matrix_a_new, b)
        solutions.append(solution)
    return solutions

# Testing
if __name__ == "__main__":
    from desdeo.problem import pareto_navigator_test_problem

    problem = pareto_navigator_test_problem()
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()
    speed = 1
    allowed_speeds = np.array([1, 2, 3, 4, 5])
    adjusted_speed = calculate_adjusted_speed(allowed_speeds, speed)

    starting_point = {"f_1": 1.38, "f_2": 0.62, "f_3": -35.33}

    preference_info = {
        #"reference_point": {"f_1": ideal["f_1"], "f_2": ideal["f_2"], "f_3": nadir["f_3"]}
        "classification": {"f_1": "<", "f_2": "<", "f_3": ">"}
    }

    num_solutions = 200
    acc = 0.15
    solutions = calculate_all_solutions(problem, starting_point, adjusted_speed, num_solutions, preference_info)
    navigated_point = starting_point

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([0.35, -0.51, -26.26])) < acc):
            print("Values close enough to the ones in the article reached. ", solutions[i])
            navigated_point = solutions[i]
            break

    preference_info = {
        #"reference_point": {"f_1": ideal["f_1"], "f_2": nadir["f_2"], "f_3": navigated_point["f_3"]}
        "classification": {"f_1": "<", "f_2": ">", "f_3": "="}
    }

    solutions = calculate_all_solutions(problem, navigated_point, adjusted_speed, num_solutions, preference_info)

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([-0.89, 2.91, -24.98])) < acc):
            print("Values close enough to the ones in the article reached. ", solutions[i])
            navigated_point = solutions[i]
            break

    preference_info = {
        #"reference_point": {"f_1": nadir["f_1"], "f_2": ideal["f_2"], "f_3": ideal["f_3"]}
        "classification": {"f_1": ">", "f_2": "<", "f_3": "<"}
    }
    solutions = calculate_all_solutions(problem, navigated_point, adjusted_speed, num_solutions, preference_info)

    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([-0.32, 2.33, -27.85])) < acc):
            print("Values close enough to the ones in the article reached. ", solutions[i])
            navigated_point = solutions[i]
            break
