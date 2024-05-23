import numpy as np

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    ScalarizationFunction,
    Variable,
    VariableTypeEnum,
    numpy_array_to_objective_dict,
    pareto_navigator_test_problem,
    objective_dict_to_numpy_array
)
from desdeo.tools.scalarization import (
    add_lte_constraints,
    get_corrected_ideal_and_nadir
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

def calculate_next_solution(
    problem: Problem,
    reference_point: dict[str, float],
    current_solution: dict[str, float],
    step_size: float
):
    n = objective_dict_to_numpy_array(problem, current_solution)
    asp = objective_dict_to_numpy_array(problem, reference_point)
    moved_reference_point = n + step_size*(asp - n)
    ideal, nadir = get_corrected_ideal_and_nadir(problem)

    t = Variable(name="t", symbol="t", variable_type=VariableTypeEnum.real, initial_value = 1.0)

    problem_w_t = problem.add_variables([t])

    func = "t"

    scalarization = ScalarizationFunction(name = "", symbol = "milp", func = [func])

    moved_reference_point_dict = numpy_array_to_objective_dict(problem, moved_reference_point)

    constraints = []

    #constr = [f"{obj.symbol} - {moved_reference_point_dict[obj.symbol]} - t" for obj in problem.objectives]

    for obj in problem.objectives:
        constr = f"{obj.symbol} - {moved_reference_point_dict[obj.symbol]} - t"

        constraints.append(
            Constraint(
                name="",
                symbol=f"{obj.symbol}_con",
                func=constr,
                cons_type=ConstraintTypeEnum.LTE,
                linear=True,
            )
    )

    problem_w_t = problem_w_t.add_scalarization(scalarization)
    problem_w_t = problem_w_t.add_constraints(constraints)
    # define new problem (and scalarization function?) to solve,
    # with min max (z - moved_ref), z in Ne and z vector of variables
    # min t, where z - moved_ref <= t --> z - moved_ref - t <= 0
    # new variable t, new constraint ^
    # extra_func or scalarization function min t
    return problem_w_t

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
    else:
        for obj in problem.objectives:
            bounds.append(obj.nadir)
    reference_point = preference_information["reference_point"]
    references = []
    for obj in problem.objectives:
        if obj.symbol not in reference_point:
            references.append(obj.ideal)
        else:
            references.append(reference_point[obj.symbol])
    bounds = np.array(bounds)
    bounds_dict = numpy_array_to_objective_dict(problem, bounds)
    const_exprs = [
        f"{obj.symbol}_min - {bounds_dict[obj.symbol] * (-1 if obj.maximize else 1)}" for obj in problem.objectives
    ]
    problem_w_bounds = add_lte_constraints(problem, const_exprs, [f"const_{i}" for i in range(1, len(const_exprs) + 1)])
    references_dict = numpy_array_to_objective_dict(problem, np.array(references))
    return bounds_dict, references_dict

if __name__ == "__main__":
    problem = pareto_navigator_test_problem()
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()

    starting_point = {"f_1": 1.38, "f_2": 0.62, "f_3": -35.33}
    preference_information = {
#        "bounds": {"f_1": 1, "f_2": 2},
        "reference_point": {"f_1": ideal["f_1"], "f_2": ideal["f_2"], "f_3": nadir["f_3"]}
    }
    reference_point = {"f_1": ideal["f_1"], "f_2": ideal["f_2"], "f_3": nadir["f_3"]}
    #solutions = calculate_all_solutions(problem, preference_information)
    #print(calculate_all_solutions(problem, preference_information))
    print(calculate_next_solution(problem, reference_point, starting_point, 1/200))
