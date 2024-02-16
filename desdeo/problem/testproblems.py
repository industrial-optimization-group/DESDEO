"""Pre-defined multiobjective optimization problems.

Pre-defined problems for, e.g.,
testing and illustration purposed are defined here.
"""

from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    DiscreteDefinition,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


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


def river_pollution_problem(five_objective_variant: bool = True) -> Problem:
    """Create a pydantic dataclass representation of the river pollution problem with either five or four variables.

    The objective functions "DO city", "DO municipality", and
    "BOD deviation" are to be minimized, while "ROI fishery" and "ROI city" are to be
    maximized. If the four variant problem is used, the the "BOD deviation" objective
    function is not present.

    Args:
        five_objective_variant (bool, optional): Whether to use to five
            objective function variant of the problem or not. Defaults to True.

    Returns:
        Problem: the river pollution problem.

    References:
        Narula, Subhash C., and HRoland Weistroffer. "A flexible method for
            nonlinear multicriteria decision-making problems." IEEE Transactions on
            Systems, Man, and Cybernetics 19.4 (1989): 883-887.
        Miettinen, Kaisa, and Marko M. Mäkelä. "Interactive method NIMBUS for
            nondifferentiable multiobjective optimization problems." Multicriteria
            Analysis: Proceedings of the XIth International Conference on MCDM, 1–6
            August 1994, Coimbra, Portugal. Berlin, Heidelberg: Springer Berlin
            Heidelberg, 1997.
    """
    variable_1 = Variable(
        name="BOD", symbol="x_1", variable_type="real", lowerbound=0.3, upperbound=1.0, initial_value=0.65
    )
    variable_2 = Variable(
        name="DO", symbol="x_2", variable_type="real", lowerbound=0.3, upperbound=1.0, initial_value=0.65
    )

    f_1 = "-4.07 - 2.27 * x_1"
    f_2 = "-2.60 - 0.03 * x_1 - 0.02 * x_2 - 0.01 / (1.39 - x_1**2) - 0.30 / (1.39 - x_2**2)"
    f_3 = "-8.21 + 0.71 / (1.09 - x_1**2)"
    f_4 = "-0.96 + 0.96 / (1.09 - x_2**2)"
    f_5 = "Max(Abs(x_1 - 0.65), Abs(x_2 - 0.65))"

    objective_1 = Objective(name="DO city", symbol="f_1", func=f_1, maximize=False)
    objective_2 = Objective(name="DO municipality", symbol="f_2", func=f_2, maximize=False)
    objective_3 = Objective(name="ROI fishery", symbol="f_3", func=f_3, maximize=True)
    objective_4 = Objective(name="ROI city", symbol="f_4", func=f_4, maximize=True)
    objective_5 = Objective(name="BOD deviation", symbol="f_5", func=f_5, maximize=False)

    objectives = (
        [objective_1, objective_2, objective_3, objective_4, objective_5]
        if five_objective_variant
        else [objective_1, objective_2, objective_3, objective_4]
    )

    return Problem(
        name="The river pollution problem",
        description="The river pollution problem to maximize return of investments and minimize pollution.",
        variables=[variable_1, variable_2],
        objectives=objectives,
    )


def simple_test_problem() -> Problem:
    """Defines a simple problem suitable for testing purposes."""
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type="real", lowerbound=0, upperbound=10, initial_value=5),
        Variable(name="x_2", symbol="x_2", variable_type="real", lowerbound=0, upperbound=10, initial_value=5),
    ]

    constants = [Constant(name="c", symbol="c", value=4.2)]

    f_1 = "x_1 + x_2"
    f_2 = "x_2**3"
    f_3 = "x_1 + x_2"
    f_4 = "Max(Abs(x_1 - x_2), c)"  # c = 4.2
    f_5 = "(-x_1) * (-x_2)"

    objectives = [
        Objective(name="f_1", symbol="f_1", func=f_1, maximize=False),  # min!
        Objective(name="f_2", symbol="f_2", func=f_2, maximize=True),  # max!
        Objective(name="f_3", symbol="f_3", func=f_3, maximize=True),  # max!
        Objective(name="f_4", symbol="f_4", func=f_4, maximize=False),  # min!
        Objective(name="f_5", symbol="f_5", func=f_5, maximize=True),  # max!
    ]

    return Problem(
        name="Simple test problem.",
        description="A simple problem for testing purposes.",
        constants=constants,
        variables=variables,
        objectives=objectives,
    )


def zdt1(number_of_variables: int) -> Problem:
    n = number_of_variables

    # function f_1
    f1_symbol = "f_1"
    f1_expr = "1 * x_1"

    # function g
    g_symbol = "g"
    g_expr_1 = f"1 + (9 / ({n} - 1))"
    g_expr_2 = "(" + " + ".join([f"x_{i}" for i in range(2, n + 1)]) + ")"
    g_expr = g_expr_1 + " * " + g_expr_2

    # function h(f, g)
    h_symbol = "h"
    h_expr = f"1 - Sqrt(({f1_expr}) / ({g_expr}))"

    # function f_2
    f2_symbol = "f_2"
    f2_expr = f"{g_symbol} * {h_symbol}"

    variables = [
        Variable(name=f"x_{i}", symbol=f"x_{i}", variable_type="real", lowerbound=0, upperbound=1, initial_value=0.5)
        for i in range(1, n + 1)
    ]

    objectives = [
        Objective(name="f_1", symbol=f1_symbol, func=f1_expr, maximize=False, ideal=0, nadir=1),
        Objective(name="f_2", symbol=f2_symbol, func=f2_expr, maximize=False, ideal=0, nadir=1),
    ]

    extras = [
        ExtraFunction(name="g", symbol=g_symbol, func=g_expr),
        ExtraFunction(name="h", symbol=h_symbol, func=h_expr),
    ]

    return Problem(
        name="zdt1",
        description="The ZDT1 test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
    )


def simple_data_problem() -> Problem:
    """Defines a simple problem with only data-based objective functions."""
    constants = [Constant(name="c", symbol="c", value=10)]

    n_var = 5
    variables = [
        Variable(
            name=f"y_{i}",
            symbol=f"y_{i}",
            variable_type=VariableTypeEnum.real,
            lowerbound=-50.0,
            upperbound=50.0,
            initial_value=0.1,
        )
        for i in range(1, n_var + 1)
    ]

    n_objectives = 3
    # only the first objective is to be maximized, the rest are to be minimized
    objectives = [
        Objective(
            name=f"g_{i}",
            symbol=f"g_{i}",
            func=None,
            objective_type=ObjectiveTypeEnum.data_based,
            maximize=i == 1,
            ideal=3000 if i == 1 else -60.0 if i == 3 else 0,
            nadir=0 if i == 1 else 15 - 2.0 if i == 3 else 15,
        )
        for i in range(1, n_objectives + 1)
    ]

    constraints = [Constraint(name="cons 1", symbol="c_1", cons_type=ConstraintTypeEnum.EQ, func="y_1 + y_2 - c")]

    data_len = 10
    var_data = {f"y_{i}": [i * 0.5 + j for j in range(data_len)] for i in range(1, n_var + 1)}
    obj_data = {
        "g_1": [sum(var_data[f"y_{j}"][i] for j in range(1, n_var + 1)) ** 2 for i in range(data_len)],
        "g_2": [max(var_data[f"y_{j}"][i] for j in range(1, n_var + 1)) for i in range(data_len)],
        "g_3": [-sum(var_data[f"y_{j}"][i] for j in range(1, n_var + 1)) for i in range(data_len)],
    }

    discrete_def = DiscreteDefinition(variable_values=var_data, objective_values=obj_data)

    return Problem(
        name="Simple data problem",
        description="Simple problem with all objectives being data-based. Has constraints and a constant also.",
        constants=constants,
        variables=variables,
        objectives=objectives,
        constraints=constraints,
        discrete_definition=discrete_def,
    )


if __name__ == "__main__":
    problem = simple_data_problem()
    print(problem.model_dump_json(indent=2))
