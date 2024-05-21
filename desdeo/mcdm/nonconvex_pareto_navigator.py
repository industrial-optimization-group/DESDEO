import numpy as np

from desdeo.problem import (
    Problem,
    numpy_array_to_objective_dict,
    pareto_navigator_test_problem,
    objective_dict_to_numpy_array
)

def paint():
    return

def e_cones():
    return

def handle_preference_information(
        problem: Problem,
        reference_point: dict[str, float],
        bounds: dict[str, float] | None = None
):
    return

def calculate_search_direction():
    return

def calculate_next_solution():
    return

def calculate_all_solutions(
        problem: Problem,
        preference_information: dict[dict[str, float]]
):
    bounds = []
    if "bounds" in preference_information:
        b = preference_information["bounds"]
        for obj in problem.objectives:
            if obj.symbol not in b:
                bounds.append(obj.nadir)
            else:
                bounds.append(b[obj.symbol])
    bounds = np.array(bounds)
    bounds_dict = numpy_array_to_objective_dict(problem, bounds)
    return numpy_array_to_objective_dict(problem, bounds)

if __name__ == "__main__":
    problem = pareto_navigator_test_problem()
    preference_information = {"bounds": {"f_1": 1, "f_2": 2}}
    solutions = calculate_all_solutions(problem, preference_information)
    print(solutions)
