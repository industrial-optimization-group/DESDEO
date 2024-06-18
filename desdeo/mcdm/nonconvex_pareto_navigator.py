"""Functions related to the Nonconvex Pareto Navigator method are defined here.

Reference of the method:

Hartikainen, M., Miettinen, K., & Klamroth, K. (2019). Interactive nonconvex pareto navigator
for multiobjective optimization. European Journal of Operational Research, 275(1), 238-251.
"""

import numpy as np

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    ScalarizationFunction,
    Variable,
    VariableTypeEnum,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array
)
from desdeo.tools.scalarization import (
    add_lte_constraints,
    get_corrected_ideal_and_nadir
)
from desdeo.mcdm.pareto_navigator import (
    calculate_adjusted_speed,
    calculate_search_direction
)

from desdeo.tools.gurobipy_solver_interfaces import GurobipySolver

from desdeo.tools.paint import paint

def get_corrected_solutions(problem: Problem, solutions: list[dict[str, float]]) -> list[dict[str, float]]:
    """Correct the objective values of the objectives that are to be maximized for a set of solutions.

    Args:
        problem (Problem): The original problem.
        solutions (list[dict[str, float]]): A list of solutions.

    Returns:
        list[dict[str, float]]: A list of corrected solutions.
    """
    corrected_solutions = []
    for solution in solutions:
        sol = {
            objective.symbol: solution[objective.symbol] if not objective.maximize else -solution[objective.symbol]
            for objective in problem.objectives
        }
        corrected_solutions.append(sol)
    return corrected_solutions

def get_paint_approximation(problem: Problem, paint_approx: np.ndarray | None = None) -> np.ndarray:
    """Compute the PAINT approximation and reformulate it.

    Args:
        problem (Problem): The problem being solved.
        paint_approx (np.ndarray | None, optional): A precomputed PAINT approximation (for tests). Defaults to None.

    Returns:
        np.ndarray: The PAINT approximation as a matrix with each node as a Pareto optimal solution instead of an index.
    """
    po_solutions = []
    for obj in problem.objectives:
        if not obj.maximize:
            po_solutions.append(problem.discrete_representation.objective_values[obj.symbol])
        else:
            values = []
            for value in problem.discrete_representation.objective_values[obj.symbol]:
                values.append(-value)
            po_solutions.append(values)
    po_solutions = np.array(po_solutions).T

    # run PAINT to get the approximation
    approximation = paint(po_solutions) if paint_approx is None else paint_approx

    # form the PAINT approximation into a matrix
    matrix = []
    for p in approximation:
        row = []
        for i in p:
            row.append(po_solutions[i])
        matrix.append(row)
    return np.array(matrix)

def e_cones(problem: Problem, solutions: list[dict[str, float]]) -> np.ndarray:
    """Create the matrix V to form the e-cones.

    Args:
        problem (Problem): The problem being solved.
        solutions (list[dict[str, float]]): A list of approximated solutions given by the PAINT approximation.

    Returns:
        np.ndarray: The matrix V to form the e-cones.
    """
    k = len(problem.objectives)

    values = []
    for s1 in solutions:
        for s2 in solutions:
            dividend = 0
            if s1 == s2:
                continue
            for obj1 in s1:
                dividend = s2[obj1] - s1[obj1]
                divisor = 0
                for obj2 in s1:
                    if obj1 == obj2:
                        continue
                    divisor += (s1[obj2] - s2[obj2])
                division = dividend / divisor
                values.append(division)

    admissible = []
    for value in values:
        if value < 1 / (k - 1) and value > 0:
            admissible.append(value)
    epsilon = max(admissible) # min or max?

    epsilons = np.ones(k)
    epsilons = epsilon * epsilons

    matrix_v = np.identity(k)
    for i in range(k):
        for j in range(k):
            if i != j:
                matrix_v[i][j] = -epsilons[i]

    return np.linalg.inv(matrix_v).T

def create_milp(problem: Problem, approximation: np.ndarray, cones: np.ndarray | None = None) -> Problem:
    """Form the mixed integer linear problem to replace the original problem.

    The problem was defined in Hartikainen, M., Miettinen, K., & Wiecek, M. M. (2012). PAINT: Pareto front interpolation
    for nonlinear multiobjective optimization. Computational optimization and applications, 52, 845-867.

    Args:
        problem (Problem): The original problem.
        approximation (np.ndarray): The PAINT approximation to use in the surrogate.
        cones (np.ndarray, optional): The e-cones.

    Returns:
        Problem: A mixed integer linear problem to act as a surrogate problem for the original.
    """
    a, b = np.shape(approximation)[0], np.shape(approximation)[1]
    ideal, nadir = get_corrected_ideal_and_nadir(problem)

    variables = []
    # a loop to form the decision variables
    for i in range(a):
        # form and add the y variables
        y = Variable(
            name=f"y_{i}",
            symbol=f"y_{i}",
            variable_type=VariableTypeEnum.binary,
            lowerbound=0,
            upperbound=1,
            initial_value=0
        )
        variables.append(y)

        # form and add the lambda variables from the lambda matrix
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
    ind = 1 # as of now, an index to get the objective values from the polytopes of the approximation
    # a loop to form the objective funtions
    for obj in problem.objectives:
        sums = []
        for k in range(a):
            exprs = []
            for j in range(b):
                expr = f"l_{k}_{j} * {approximation[k][j][ind-1]}"
                exprs.append(expr)
            expr = " + ".join(exprs)
            sums.append(expr)
        sums = " + ".join(sums)

        # form the sum of sums for each f_i
        if cones is None:
            # form the sums into objectives
            func = Objective(
                name = f"f_{ind}",
                symbol = f"f_{ind}",
                func = sums,
                objective_type = ObjectiveTypeEnum.analytical,
                maximize = False,
                ideal = ideal[obj.symbol],
                nadir = nadir[obj.symbol]
            )
            objectives.append(func)
            ind += 1
        else:
            # form the sums into objectives
            func = Objective(
                name = f"f_{ind}",
                symbol = f"f_{ind}",
                func = sums,
                objective_type = ObjectiveTypeEnum.analytical,
                maximize = False,
                ideal = -float("inf"), # if there are e-cones, ideal is not assigned here but as separate constraints
                nadir = float("inf")
            )
            objectives.append(func)
            ind += 1

    constraints = []
    lambda_exprs = []
    y_exprs = []
    # a loop to form the constraints
    for i in range(a):
        exprs = []
        # form and add the inequality constraints involving lambda and y variables
        for j in range(b):
            expr = f"l_{i}_{j}"
            lambda_exprs.append(expr)
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

        # form the y sum equality constraint
        y_expr = f"y_{i}"
        y_exprs.append(y_expr)
    # form and add the lambda sum equality constraint
    lambda_exprs = " + ".join(lambda_exprs) + " - 1"
    lambda_const = Constraint(
        name="lambda_con",
        symbol="lambda_con",
        cons_type=ConstraintTypeEnum.EQ,
        func=lambda_exprs
    )
    constraints.append(lambda_const)

    # form and add the y sum equality constraint
    y_exprs = " + ".join(y_exprs) + " - 1"
    y_const = Constraint(
        name="y_con",
        symbol="y_con",
        cons_type=ConstraintTypeEnum.EQ,
        func=y_exprs
    )
    constraints.append(y_const)

    # add the constraints coming from the e-cones
    if cones is not None:
        for i in range(len(problem.objectives)):
            e_cone_exprs = []
            for j in range(len(problem.objectives)):
                e_cone_exprs.append(f"{-cones[i][j]} * f_{j+1} + {ideal[problem.objectives[j].symbol]}")
            e_cone_expr = " + ".join(e_cone_exprs)
            e_cone_con = Constraint(
                name=f"e_cone_con_{i}",
                symbol=f"e_cone_con_{i}",
                cons_type=ConstraintTypeEnum.LTE,
                func=e_cone_expr
            )
            constraints.append(e_cone_con)

    return Problem(
        name="milp",
        description="milp",
        variables=variables,
        objectives=objectives,
        constraints=constraints
    )

def solve_next_solution(
    problem: Problem,
    search_direction: dict[str, float],
    current_solution: dict[str, float],
    step_size: float
) -> dict[str, float | list[float]]:
    """Solve the next solution.

    Args:
        problem (Problem): The problem being solved.
        search_direction (dict[str, float]): The current search direction.
        current_solution (dict[str, float]): The current solution.
        step_size (float): The step size.

    Returns:
        dict[str, float | list[float]]: The next solution.
    """
    # get the moved reference point
    z = objective_dict_to_numpy_array(problem, current_solution)
    d = objective_dict_to_numpy_array(problem, search_direction)
    moved_reference_point = z + step_size * d
    moved_reference_point_dict = numpy_array_to_objective_dict(problem, moved_reference_point)

    t = Variable(name="t", symbol="t", variable_type=VariableTypeEnum.real, initial_value = 1.0)

    problem_w_t = problem.add_variables([t])

    func = f"{t.symbol} + 0"

    scalarization = ScalarizationFunction(
        name = "t_func",
        symbol = "t_func",
        func = func,
        is_linear = True
    )

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

    solver = GurobipySolver(problem_w_t)
    res = solver.solve("t_func")
    print(moved_reference_point, d)
    return res.optimal_objectives

def calculate_all_solutions(
    problem: Problem,
    current_solution: dict[str, float],
    preference_information: dict[dict[str, float]],
    step_size: float,
    num_solutions: int
) -> list[dict[str, float | list[float]]]:
    """Calculate a set number of solutions.

    Args:
        problem (Problem): The problem being solved.
        current_solution (dict[str, float]): the current solution.
        preference_information (dict[dict[str, float]]): The preference information as a reference point and bounds.
        step_size (float): The step size.
        num_solutions (int): The number of solutions to be computed.

    Returns:
        list[dict[str, float | list[float]]]: A list of a set number of solutions.
    """
    bounds = []
    # TODO: check if lower or upper bounds, check maximization
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
    d = calculate_search_direction(problem, references_dict, current_solution)

    # form the bounds into constraints
    const_exprs = [
        f"{obj.symbol}_min - {bounds_dict[obj.symbol]}" for obj in problem.objectives
    ]
    # add the bounds as constraints to the original problem
    problem_w_bounds = add_lte_constraints(problem, const_exprs, [f"const_{i}" for i in range(1, len(const_exprs) + 1)])

    # compute all the solutions in the current direction
    solutions = []
    while len(solutions) < num_solutions:
        current_solution = solve_next_solution(problem_w_bounds, d, current_solution, step_size)
        solutions.append(current_solution)
    return solutions

# test the method
if __name__ == "__main__":
    acc = 0.10
    allowed_speeds = [1, 2, 3, 4, 5]
    speed = 1
    adjusted_speed = calculate_adjusted_speed(allowed_speeds, speed)
    x_1 = Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=4)

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="(5 - x_1) * (x_2 - 11)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=14.9,
        nadir=17.8,
        maximize=False,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func="(5 - x_1) * (x_2 - 11)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=404,
        nadir=451,
        maximize=False,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func="(5 - x_1) * (x_2 - 11)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=0.26,
        nadir=48.9,
        maximize=False,
    )
    f_4 = Objective(
        name="f_4",
        symbol="f_4",
        func="(5 - x_1) * (x_2 - 11)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=14400,
        nadir=15900,
        maximize=False,
    )
    f_5 = Objective(
        name="f_5",
        symbol="f_5",
        func="(5 - x_1) * (x_2 - 11)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=10300,
        nadir=8900,
        maximize=True,
    )
    representation = DiscreteRepresentation(
        variable_values={"x_1": [0, 0, 0, 0, 0, 0, 0]},
        objective_values={
            "f_1": [15.98, 16.11, 16.47, 16.85, 17.4, 16.01, 16.08, 16.80, 17.10],
            "f_2": [417.5, 426.6, 422.0, 415.5, 416.8, 425.2, 425.2, 414.1, 411.6],
            "f_3": [22.82, 1.52, 21.0, 22.75, 17.51, 8.04, 11.0, 18.24, 15.10],
            "f_4": [15030, 14440, 14980, 15000, 14970, 14590, 14700, 14960, 14860],
            "f_5": [9656, 8947, 9730, 9721, 9763, 9132, 9265, 9626, 9529]
        },
        non_dominated=True,
    )

    problem = Problem(
        name="Nonconvex Pareto Navigator test problem",
        description="The test problem used in the nonconvex Pareto navigator paper.",
        variables=[x_1],
        objectives=[f_1, f_2, f_3, f_4, f_5],
        discrete_representation=representation
    )

    ideal = problem.get_ideal_point()
    nadir = problem.get_nadir_point()

    # read this into a file next time
    test_approx = np.array([[0, 0, 0, 0, 0, 0],
                            [1, 1, 1, 1, 1, 1],
                            [2, 2, 2, 2, 2, 2],
                            [3, 3, 3, 3, 3, 3],
                            [4, 4, 4, 4, 4, 4],
                            [5, 5, 5, 5, 5, 5],
                            [6, 6, 6, 6, 6, 6],
                            [7, 7, 7, 7, 7, 7],
                            [8, 8, 8, 8, 8, 8],
                            [0, 3, 0, 0, 0, 0],
                            [0, 4, 0, 0, 0, 0],
                            [0, 5, 0, 0, 0, 0],
                            [0, 6, 0, 0 ,0, 0],
                            [0, 7, 0, 0, 0, 0],
                            [0, 8, 0, 0, 0, 0],
                            [0, 2, 0, 0, 0, 0],
                            [0, 1, 0, 0, 0, 0],
                            [1, 2, 1, 1, 1, 1],
                            [1, 4, 1, 1, 1, 1],
                            [1, 5, 1, 1, 1, 1],
                            [1, 6, 1, 1, 1, 1],
                            [1, 7, 1, 1, 1, 1],
                            [1, 8, 1, 1, 1, 1],
                            [2, 3, 2, 2, 2, 2],
                            [2, 4, 2, 2, 2, 2],
                            [2, 6, 2, 2, 2, 2],
                            [2, 7, 2, 2, 2, 2],
                            [3, 4, 3, 3, 3, 3],
                            [3, 5, 3, 3, 3, 3],
                            [3, 6, 3, 3, 3, 3],
                            [3, 7, 3, 3, 3, 3],
                            [3, 8, 3, 3, 3, 3],
                            [4, 5, 4, 4, 4, 4],
                            [4, 6, 4, 4, 4, 4],
                            [4, 7, 4, 4, 4, 4],
                            [4, 8, 4, 4, 4, 4],
                            [5, 6, 5, 5, 5, 5],
                            [5, 8, 5, 5, 5, 5],
                            [6, 7, 6, 6, 6, 6],
                            [6, 8, 6, 6, 6, 6],
                            [7, 8, 7, 7, 7, 7],
                            [0, 2, 4, 0, 0, 0],
                            [0, 2, 6, 0, 0, 0],
                            [0, 2, 7, 0, 0, 0],
                            [0, 3, 4, 0, 0, 0],
                            [0, 3, 5, 0, 0, 0],
                            [0, 3, 7, 0, 0, 0],
                            [0, 3, 8, 0, 0, 0],
                            [0, 4, 6, 0, 0, 0],
                            [0, 4, 7, 0, 0, 0],
                            [0, 5, 6, 0, 0, 0],
                            [0, 5, 8, 0, 0, 0],
                            [0, 6, 7, 0, 0, 0],
                            [0, 6, 8, 0, 0, 0],
                            [0, 7, 8, 0, 0, 0],
                            [0, 1, 6, 0, 0, 0],
                            [0, 1, 7, 0, 0, 0],
                            [0, 1, 8, 0, 0, 0],
                            [0, 2, 3, 0, 0, 0],
                            [0, 1, 5, 0, 0, 0],
                            [1, 2, 4, 1, 1, 1],
                            [1, 2, 6, 1, 1, 1],
                            [1, 4, 5, 1, 1, 1],
                            [1, 4, 6, 1, 1, 1],
                            [1, 4, 7, 1, 1, 1],
                            [1, 4, 8, 1, 1, 1],
                            [1, 5, 6, 1, 1, 1],
                            [1, 5, 8, 1, 1, 1],
                            [1, 6, 7, 1, 1, 1],
                            [1, 6, 8, 1, 1, 1],
                            [1, 7, 8, 1, 1, 1],
                            [2, 3, 4, 2, 2, 2],
                            [2, 3, 6, 2, 2, 2],
                            [2, 3, 7, 2, 2, 2],
                            [2, 4, 6, 2, 2, 2],
                            [2, 4, 7, 2, 2, 2],
                            [2, 6, 7, 2, 2, 2],
                            [3, 4, 5, 3, 3, 3],
                            [3, 4, 6, 3, 3, 3],
                            [3, 4, 7, 3, 3, 3],
                            [3, 4, 8, 3, 3, 3],
                            [3, 5, 6, 3, 3, 3],
                            [3, 5, 8, 3, 3, 3],
                            [3, 6, 7, 3, 3, 3],
                            [3, 6, 8, 3, 3 ,3],
                            [3, 7, 8, 3, 3, 3],
                            [4, 5, 6, 4, 4, 4],
                            [4, 5, 8, 4, 4, 4],
                            [4, 6, 7, 4, 4, 4],
                            [4, 6, 8, 4, 4, 4],
                            [4, 7, 8, 4, 4, 4],
                            [5, 6, 8, 5, 5, 5],
                            [6, 7, 8, 6, 6, 6],
                            [0, 2, 4, 6, 0, 0],
                            [0, 2, 4, 7, 0, 0],
                            [0, 1, 5, 6, 0, 0],
                            [0, 2, 6, 7, 0, 0],
                            [0, 3, 4, 7, 0, 0],
                            [0, 3, 5, 8, 0, 0],
                            [0, 3, 7, 8, 0, 0],
                            [0, 4, 6, 7, 0, 0],
                            [0, 5, 6, 8, 0, 0],
                            [0, 6, 7, 8, 0, 0],
                            [0, 1, 5, 8, 0, 0],
                            [0, 1, 6, 7, 0, 0],
                            [0, 1, 6, 8, 0, 0],
                            [0, 1, 7, 8, 0, 0],
                            [0, 2, 3, 4, 0, 0],
                            [0, 2, 3, 7, 0, 0],
                            [1, 2, 4, 6, 1, 1],
                            [1, 4, 5, 6, 1, 1],
                            [1, 4, 5, 8, 1, 1],
                            [1, 4, 6, 7, 1, 1],
                            [1, 4, 6, 8, 1, 1],
                            [1, 4, 7, 8, 1, 1],
                            [1, 5, 6, 8, 1, 1],
                            [1, 6, 7, 8, 1, 1],
                            [2, 3, 4, 6, 2, 2],
                            [2, 3, 4, 7, 2, 2],
                            [2, 3, 6, 7, 2, 2],
                            [2, 4, 6, 7, 2, 2],
                            [3, 4, 5, 6, 3, 3],
                            [3, 4, 5, 8, 3, 3],
                            [3, 4, 6, 7, 3, 3],
                            [3, 4, 6, 8, 3, 3],
                            [3, 4, 7, 8, 3, 3],
                            [3, 5, 6, 8, 3, 3],
                            [3, 6, 7, 8, 3, 3],
                            [4, 5, 6, 8, 4, 4],
                            [4, 6, 7, 8, 4, 4],
                            [0, 2, 4, 6, 7, 0],
                            [0, 1, 5, 6, 8, 0],
                            [0, 1, 6, 7, 8, 0],
                            [0, 2, 3, 4, 7, 0],
                            [1, 4, 5, 6, 8, 1],
                            [1, 4, 6, 7, 8, 1],
                            [2, 3, 4, 6, 7, 2],
                            [3, 4, 5, 6, 8, 3],
                            [3, 4, 6, 7, 8, 3]])

    matrix = get_paint_approximation(problem, test_approx)

    starting_point = {"f_1": 16.1, "f_2": 421, "f_3": 42, "f_4": 15320, "f_5": 9852}
    preference_information = {
        "bounds": {"f_1": 16.1, "f_2": 452, "f_3": 49, "f_4": 15500, "f_5": 8860},
        "reference_point": {"f_1": 15.1, "f_2": 427, "f_3": 43, "f_4": 15150, "f_5": 8920}
    }
    reference_point = preference_information["reference_point"]
    for obj in problem.objectives:
        if obj.maximize:
            if "bounds" in preference_information:
                preference_information["bounds"][obj.symbol] = -preference_information["bounds"][obj.symbol]
            starting_point[obj.symbol] = -starting_point[obj.symbol]
            reference_point[obj.symbol] = -reference_point[obj.symbol]

    milp = create_milp(problem, matrix)
    solutions = calculate_all_solutions(milp, starting_point, preference_information, adjusted_speed, 100)

    cones = e_cones(milp, solutions)

    milp = create_milp(milp, matrix, cones)
    starting_point = {"f_1": 16.08, "f_2": 425.2, "f_3": 11.0, "f_4": 14590, "f_5": 9132}
    preference_information = {
        "bounds": {"f_1": 16.1, "f_2": 452, "f_3": 49, "f_4": 15500, "f_5": 8860},
        "reference_point": {"f_1": 15.1, "f_2": 427, "f_3": 43, "f_4": 15150, "f_5": 8920}
    }
    reference_point = preference_information["reference_point"]
    for obj in problem.objectives:
        if obj.maximize:
            if "bounds" in preference_information:
                preference_information["bounds"][obj.symbol] = -preference_information["bounds"][obj.symbol]
            starting_point[obj.symbol] = -starting_point[obj.symbol]
            reference_point[obj.symbol] = -reference_point[obj.symbol]

    solutions = calculate_all_solutions(milp, starting_point, preference_information, adjusted_speed, 10)

    # a separate function for this?
    corrected_solutions = get_corrected_solutions(problem, solutions)
    print(corrected_solutions)

    for i in range(len(corrected_solutions)):
        if np.all(np.abs(objective_dict_to_numpy_array(problem, corrected_solutions[i])
                            - np.array([16.1, 421, 42, 15320, 9652])) < acc):
            print("Values close enough to the ones in the article reached. ", corrected_solutions[i])
            navigated_point = corrected_solutions[i]
            break
