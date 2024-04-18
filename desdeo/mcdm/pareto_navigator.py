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
    get_ideal_dict,
    get_nadir_dict,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array
)


def calculate_adjusted_speed(allowed_speeds: np.ndarray, speed: float) -> float:
    """Calculate an adjusted speed from a given float.

    Note:
        Adjusting the speed is not specified in the article but seems necessary.

    Args:
        allowed_speeds (np.ndarray): An array of allowed speeds.
        speed (int): A given speed value where.

    Returns:
        float: An adjusted speed value calculated from given float.
            Is between 0 and 1.
    """
    return (speed / np.max(allowed_speeds)) / 20

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
    A = convex_hull.equations[:, 0:-1]
    b = -convex_hull.equations[:, -1]
    return A, b

def construct_A_matrix(problem: Problem, A: np.ndarray) -> np.ndarray:
    """Construct the A' matrix in the linear parametric programming problem from the article.

    Args:
        problem (Problem): The problem being solved.
        A (np.ndarray): The A matrix from the polyhedral set equation.

    Returns:
        np.ndarray: The A' matrix in the linear parametric programming problem from the article.
    """
    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))
    weights = 1/(nadir - ideal)

    weights_inverse = np.reshape(np.vectorize(lambda w: -1 / w)(weights), (len(weights), 1))
    identity = np.identity(len(weights))
    A_upper = np.c_[weights_inverse, identity]

    zeros = np.zeros((len(A), 1))
    A_lower = np.c_[zeros, A]

    return np.concatenate((A_upper, A_lower))

#def pareto_navigator_init(problem: Problem, starting_point: dict[str, float]):
#    A, b = get_polyhedral_set(problem)
#
#    A_new = construct_A_matrix(problem, A)
#    return


def calculate_next_solution(
    problem: Problem,
    search_direction: dict[str, float],
    current_point: dict[str, float],
    alpha: float
) -> dict[str, float]:
    """Calculate the next solution.

    Args:
        problem (Problem): The problem being solved.
        search_direction (dict[str, float]): The search direction.
        current_point (dict[str, float]): The currently navigated point.
        alpha (float): Step size. Between 0 and 1.

    Returns:
        dict[str, float]: The next solution.
    """
    z = objective_dict_to_numpy_array(problem, current_point)
    k = len(z)
    d = objective_dict_to_numpy_array(problem, search_direction)

    A, b = get_polyhedral_set(problem)

    A_new = construct_A_matrix(problem, A)

    q = z + alpha * d
    q = np.reshape(q, ((k, 1)))

    b_new = np.append(q, b)

    ideal = objective_dict_to_numpy_array(problem, get_ideal_dict(problem))
    nadir = objective_dict_to_numpy_array(problem, get_nadir_dict(problem))

    c = np.array([1] + k * [0])

    obj_bounds = np.stack((ideal, nadir))
    bounds = [(None, None)]
    for x, y in obj_bounds.T:
        bounds.append((x, y))

    z_new = linprog(c=c, A_ub=A_new, b_ub=b_new, bounds=bounds)
    if z_new["success"]:
        return numpy_array_to_objective_dict(problem, z_new["x"][1:])
    return ""

# Testing
if __name__ == "__main__":
    from desdeo.problem import pareto_navigator_test_problem

    problem = pareto_navigator_test_problem()
    ideal = get_ideal_dict(problem)
    nadir = get_nadir_dict(problem)
    speed = 1
    allowed_speeds = np.array([1, 2, 3, 4, 5])
    adjusted_speed = calculate_adjusted_speed(allowed_speeds, speed)

    starting_point = {'f_1': 1.38, 'f_2': 0.62, 'f_3': -35.33}
    reference_point = {'f_1': ideal['f_1'], 'f_2': ideal['f_2'], 'f_3': nadir['f_3']}

    d = calculate_search_direction(problem, reference_point, starting_point)

    navigated_point = calculate_next_solution(problem, d, starting_point, adjusted_speed)

    max_it = 200
    acc = 0.15
    step_n = 0
    while step_n < max_it:
        navigated_point = calculate_next_solution(problem, d, navigated_point, adjusted_speed)
        step_n += 1
        if np.all(np.abs(objective_dict_to_numpy_array(problem, navigated_point)
                         - np.array([0.35, -0.51, -26.26])) < acc):
            print("Values close enough to the ones in the article reached. ", navigated_point)
            break

    reference_point = {'f_1': ideal['f_1'], 'f_2': nadir['f_2'], 'f_3': navigated_point['f_3']}
    d = calculate_search_direction(problem, reference_point, navigated_point)
    step_n = 0

    while step_n < max_it:
        navigated_point = calculate_next_solution(problem, d, navigated_point, adjusted_speed)
        step_n += 1
        if np.all(np.abs(objective_dict_to_numpy_array(problem, navigated_point)
                         - np.array([-0.89, 2.91, -24.98])) < acc):
            print("Values close enough to the ones in the article reached. ", navigated_point)
            break

    reference_point = {'f_1': nadir['f_1'], 'f_2': ideal['f_2'], 'f_3': ideal['f_3']}
    d = calculate_search_direction(problem, reference_point, navigated_point)
    step_n = 0

    while step_n < max_it:
        navigated_point = calculate_next_solution(problem, d, navigated_point, adjusted_speed)
        step_n += 1
        if np.all(np.abs(objective_dict_to_numpy_array(problem, navigated_point)
                         - np.array([-0.32, 2.33, -27.85])) < acc):
            print("Values close enough to the ones in the article reached. ", navigated_point)
            break
