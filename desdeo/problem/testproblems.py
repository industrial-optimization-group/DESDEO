"""Pre-defined multiobjective optimization problems.

Pre-defined problems for, e.g.,
testing and illustration purposed are defined here.
"""

from desdeo.problem.schema import Problem, Constant, Variable, Objective, Constraint


def binh_and_korn() -> Problem:
    """Create a pydantic dataclass representation of the Binh and Korn problem.

    The function has two objective functions, two variables, and two constraint functions.

    References:
        Binh T. and Korn U. (1997) MOBES: A Multiobjective Evolution Strategy for Constrained Optimization Problems.
        In: Proceedings of the Third International Conference on Genetic Algorithms. Czech Republic. pp. 176-182.
    """
    # These constants are for demonstrative purposes.
    constant_1 = Constant(name="Four", symbol="c_1", value=4)
    constant_2 = Constant(name="Five", symbol="c_2", value=5)

    variable_1 = Variable(
        name="The first variable", symbol="x_1", variable_type="real", lowerbound=0, upperbound=5, initial_value=2.5
    )
    variable_2 = Variable(
        name="The second variable", symbol="x_2", variable_type="real", lowerbound=0, upperbound=3, initial_value=1.5
    )

    objective_1 = Objective(
        name="Objective 1",
        symbol="f_1",
        func=["Add", ["Multiply", "c_1", ["Square", "x_1"]], ["Multiply", "c_1", ["Square", "x_2"]]],
        maximize=False,
        ideal=None,
        nadir=None,
    )
    objective_2 = Objective(
        name="Objective 2",
        symbol="f_2",
        func=["Add", ["Square", ["Subtract", "x_1", "c_2"]], ["Square", ["Subtract", "x_2", "c_2"]]],
        maximize=False,
        ideal=None,
        nadir=None,
    )

    constraint_1 = Constraint(
        name="Constraint 1",
        symbol="g_1",
        cons_type="<=",
        func=["Add", ["Square", ["Subtract", "x_1", "c_2"]], ["Square", "x_2"], -25],
    )

    constraint_2 = Constraint(
        name="Constraint 2",
        symbol="g_2",
        cons_type="<=",
        func=["Add", ["Negate", ["Square", ["Subtract", "x_1", 8]]], ["Negate", ["Square", ["Add", "x_2", 3]]], 7.7],
    )

    return Problem(
        name="The Binh and Korn function",
        description="The two-objective problem used in the paper by Binh and Korn.",
        constants=[constant_1, constant_2],
        variables=[variable_1, variable_2],
        objectives=[objective_1, objective_2],
        constraints=[constraint_1, constraint_2],
    )

if __name__=="__main__":
    problem = binh_and_korn()
    print(problem.model_dump_json(indent=2))