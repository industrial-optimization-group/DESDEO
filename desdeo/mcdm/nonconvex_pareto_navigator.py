import numpy as np
from scipy.optimize import milp

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
    add_asf_nondiff,
    add_lte_constraints,
    get_corrected_ideal_and_nadir
)

from desdeo.tools.utils import guess_best_solver
from desdeo.tools.gurobipy_solver_interfaces import GurobipySolver
from desdeo.tools.pyomo_solver_interfaces import PyomoBonminSolver

from desdeo.tools.paint import PAINT

def e_cones():
    return

def calculate_moved_reference_point(
    problem: Problem,
    current_solution: dict[str, float],
    reference_point: dict[str, float],
    step_size: float
) -> np.ndarray:
    z = objective_dict_to_numpy_array(problem, current_solution)
    q = objective_dict_to_numpy_array(problem, reference_point)
    return z + step_size*(q - z)

def create_milp(problem: Problem, approximation, a: int, b: int) -> Problem:
    variables = []
    for i in range(a):
        y = Variable(
            name=f"y_{i}",
            symbol=f"y_{i}",
            variable_type=VariableTypeEnum.binary,
            lowerbound=0,
            upperbound=1,
            initial_value=0
        )
        variables.append(y)
    for i in range(a):
        for j in range(b):
            lbd = Variable(
                name=f"l_{i}_{j}",
                symbol=f"l_{i}_{j}",
                variable_type=VariableTypeEnum.real,
                lowerbound=0.0,
                upperbound=1.0
            )
            variables.append(lbd)

    objectives =  []
    ind = 1
    for obj in problem.objectives:
        # form the sum of sums for each z_k
        sums = []
        for k in range(a):
            exprs = []
            for j in range(b):
                expr = f"l_{k}_{j} * {approximation[k][j][ind-1]}"
                exprs.append(expr)
            expr = " + ".join(exprs)
            sums.append(expr)
        sums = " + ".join(sums)

        func = Objective(
            name = f"f_{ind}",
            symbol = f"f_{ind}",
            func = sums,
            objective_type = ObjectiveTypeEnum.analytical,
            maximize = False,
            ideal = obj.ideal,
            nadir = obj.nadir
        )
        objectives.append(func)
        ind += 1

    constraints = []
    const_exprs = []
    for i in range(a):
        for j in range(b):
            expr = f"l_{i}_{j}"
            const_exprs.append(expr)
    const_exprs = " + ".join(const_exprs) + " - 1"
    lambda_const = Constraint(
        name="lambda_con",
        symbol="lambda_con",
        cons_type=ConstraintTypeEnum.EQ,
        func=const_exprs
    )
    constraints.append(lambda_const)

    for i in range(a):
        exprs = []
        for j in range(b):
            expr = f"l_{i}_{j}"
            exprs.append(expr)
        expr = " + ".join(exprs)
        expr = f"{expr} - y_{j}"
        const = Constraint(
            name=f"lte_con_{i}",
            symbol=f"lte_con_{i}",
            cons_type=ConstraintTypeEnum.LTE,
            func=expr
        )
        constraints.append(const)

    const_exprs = []
    for i in range(a):
        expr = f"y_{i}"
        const_exprs.append(expr)
    exprs = " + ".join(const_exprs) + " - 1"
    y_const = Constraint(
        name="y_con",
        symbol="y_con",
        cons_type=ConstraintTypeEnum.EQ,
        func=exprs
    )
    constraints.append(y_const)

    milp = Problem(
        name="milp",
        description="milp",
        variables=variables,
        objectives=objectives,
        constraints=constraints
    )
    milp = milp.add_variables(problem.variables)
    milp = milp.add_constraints(problem.constraints)
    return milp

def solve_next_solution(
    problem: Problem,
    reference_point: dict[str, float],
    current_solution: dict[str, float],
    step_size: float
):
    moved_reference_point = calculate_moved_reference_point(problem, current_solution, reference_point, step_size)
    moved_reference_point_dict = numpy_array_to_objective_dict(problem, moved_reference_point)

    t = Variable(name="t", symbol="t", variable_type=VariableTypeEnum.real, initial_value = 1.0)

    problem_w_t = problem.add_variables([t])

    func = f"{t.symbol} + 0"

    scalarization = ScalarizationFunction(
        name = "t_func",
        symbol = "t_func",
        func = func,
        is_linear = True)

    constraints = []

    for obj in problem.objectives:
        constr = f"{obj.symbol} - {moved_reference_point_dict[obj.symbol]} - t"

        constraints.append(
            Constraint(
                name="",
                symbol=f"{obj.symbol}_con",
                func=constr,
                cons_type=ConstraintTypeEnum.LTE,
                is_linear=True,
            )
    )

    problem_w_t = problem_w_t.add_scalarization(scalarization)
    problem_w_t = problem_w_t.add_constraints(constraints)

    #init_solver = guess_best_solver(problem_w_t)
    #solver = PyomoBonminSolver(problem_w_t)
    solver = GurobipySolver(problem_w_t)
    res = solver.solve("t_func")
    # define new problem (and scalarization function?) to solve,
    # with min max (z - moved_ref), z in Ne and z vector of variables
    # min t, where z - moved_ref <= t --> z - moved_ref - t <= 0
    # new variable t, new constraint ^
    # extra_func or scalarization function min t

    # add two new variables, l and y
    # sum of matrix l is 1
    # sum of y is 1, meaning all but 1 of y_j are 0

    # max min z - z_ref, with z from surrogate
    return res.optimal_objectives

def calculate_all_solutions(
    problem: Problem,
    current_solution: dict[str, float],
    preference_information: dict[dict[str, float]],
    step_size: float,
    num_solutions: int
):
    bounds = []
    if "bounds" in preference_information:
        b = preference_information["bounds"]
        for obj in problem.objectives:
            if obj.symbol not in b:
                bounds.append(obj.nadir) # if no bound is set on the objective, the bound is set as the nadir
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

    bounds_dict = numpy_array_to_objective_dict(problem, np.array(bounds))
    references_dict = numpy_array_to_objective_dict(problem, np.array(references))

    # form the bounds into constraints
    const_exprs = [
        f"{obj.symbol}_min - {bounds_dict[obj.symbol] * (-1 if obj.maximize else 1)}" for obj in problem.objectives
    ]
    # add the bounds as constraints to the original problem
    problem_w_bounds = add_lte_constraints(problem, const_exprs, [f"const_{i}" for i in range(1, len(const_exprs) + 1)])

    # compute all the solutions in the current direction
    solutions = []
    while len(solutions) < num_solutions:
        current_solution = solve_next_solution(problem_w_bounds, references_dict, current_solution, step_size)
        solutions.append(current_solution)
    return solutions

if __name__ == "__main__":
    problem = pareto_navigator_test_problem()
    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()
    acc = 0.15

    starting_point = {"f_1": 1.38, "f_2": 0.62, "f_3": -35.33}
    preference_information = {
#        "bounds": {"f_1": 1, "f_2": 2},
        "reference_point": {"f_1": ideal["f_1"], "f_2": ideal["f_2"], "f_3": nadir["f_3"]}
    }
    reference_point = {"f_1": ideal["f_1"], "f_2": ideal["f_2"], "f_3": nadir["f_3"]}
    #solutions = calculate_all_solutions(problem, preference_information)
    #print(calculate_all_solutions(problem, preference_information))
    #print(calculate_next_solution(problem, reference_point, starting_point, 1/200))

    #objective_values = problem.discrete_representation.objective_values
    #po_solutions = objective_dict_to_numpy_array(problem, objective_values)
    po_solutions = np.array([[-2.0, -1.0, 0.0, 1.38, 1.73, 2.48, 5.0],
                            [0.0, 4.6, -3.1, 0.62, 1.72, 1.45, 2.2],
                            [-18.0, -25.0, -14.25, -35.33, -38.64, -42.41, -55.0]]).T
    #print(po_solutions)

    test_paint = PAINT(po_solutions)
    test_approx = test_paint.approximate()

    matrix = []
    for p in test_approx:
        row = []
        for i in p:
            row.append(po_solutions[i])
        matrix.append(row)

    #print(test_approx)
    milp = create_milp(problem, matrix, np.shape(matrix)[0], np.shape(matrix)[1])
    #print(milp)
    solutions = calculate_all_solutions(milp, starting_point, preference_information, 1/200, 10)
    #print(solutions)
    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                         - np.array([0.35, -0.51, -26.26])) < acc):
            print("Values close enough to the ones in the article reached. ", solutions[i])
            navigated_point = solutions[i]
            break

    """preference_info = {
        "reference_point": {"f_1": ideal["f_1"], "f_2": nadir["f_2"], "f_3": navigated_point["f_3"]}
    }
    solutions = calculate_all_solutions(milp, navigated_point, preference_info, 1/200, 10)
    for i in range(len(solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, solutions[i])
                            - np.array([-0.89, 2.91, -24.98])) < acc):
            print("Values close enough to the ones in the article reached. ", solutions[i])
            navigated_point = solutions[i]
            break"""
