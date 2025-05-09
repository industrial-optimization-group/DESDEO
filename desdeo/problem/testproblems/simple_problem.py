from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
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


def simple_integer_test_problem() -> Problem:
    """Defines a simple integer problem suitable for testing purposes."""
    variables = [
        Variable(
            name="x_1",
            symbol="x_1",
            variable_type=VariableTypeEnum.integer,
            lowerbound=0,
            upperbound=10,
            initial_value=5,
        ),
        Variable(
            name="x_2",
            symbol="x_2",
            variable_type=VariableTypeEnum.integer,
            lowerbound=0,
            upperbound=10,
            initial_value=5,
        ),
        Variable(
            name="x_3",
            symbol="x_3",
            variable_type=VariableTypeEnum.integer,
            lowerbound=0,
            upperbound=10,
            initial_value=5,
        ),
        Variable(
            name="x_4",
            symbol="x_4",
            variable_type=VariableTypeEnum.integer,
            lowerbound=0,
            upperbound=10,
            initial_value=5,
        ),
    ]

    constants = [Constant(name="c", symbol="c", value=4.2)]

    f_1 = "x_1 + x_2 + x_3"
    f_2 = "x_2**x_4 - x_3**x_1"
    f_3 = "x_1 - x_2 + x_3*x_4"
    f_4 = "Max(Abs(x_1 - x_2), c) + Max(x_3, x_4)"  # c = 4.2
    f_5 = "(-x_1) * (-x_2)"

    objectives = [
        Objective(name="f_1", symbol="f_1", func=f_1, maximize=False),  # min!
        Objective(name="f_2", symbol="f_2", func=f_2, maximize=True),  # max!
        Objective(name="f_3", symbol="f_3", func=f_3, maximize=True),  # max!
        Objective(name="f_4", symbol="f_4", func=f_4, maximize=False),  # min!
        Objective(name="f_5", symbol="f_5", func=f_5, maximize=True),  # max!
    ]

    return Problem(
        name="Simple integer test problem.",
        description="A simple problem for testing purposes.",
        constants=constants,
        variables=variables,
        objectives=objectives,
    )


def simple_data_problem() -> Problem:
    """Defines a simple problem with only data-based objective functions."""
    constants = [Constant(name="c", symbol="c", value=1000)]

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

    discrete_def = DiscreteRepresentation(variable_values=var_data, objective_values=obj_data)

    return Problem(
        name="Simple data problem",
        description="Simple problem with all objectives being data-based. Has constraints and a constant also.",
        constants=constants,
        variables=variables,
        objectives=objectives,
        constraints=constraints,
        discrete_representation=discrete_def,
    )


def simple_linear_test_problem() -> Problem:
    """Defines a simple single objective linear problem suitable for testing purposes."""
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type="real", lowerbound=-10, upperbound=10, initial_value=5),
        Variable(name="x_2", symbol="x_2", variable_type="real", lowerbound=-10, upperbound=10, initial_value=5),
    ]

    constants = [Constant(name="c", symbol="c", value=4.2)]

    f_1 = "x_1 + x_2"

    objectives = [
        Objective(name="f_1", symbol="f_1", func=f_1, maximize=False),  # min!
    ]

    con_1 = Constraint(name="g_1", symbol="g_1", cons_type=ConstraintTypeEnum.LTE, func="c - x_1")
    con_2 = Constraint(name="g_2", symbol="g_2", cons_type=ConstraintTypeEnum.LTE, func="0.5*x_1 - x_2")

    return Problem(
        name="Simple linear test problem.",
        description="A simple problem for testing purposes.",
        constants=constants,
        variables=variables,
        constraints=[con_1, con_2],
        objectives=objectives,
    )


def simple_scenario_test_problem():
    """Returns a simple, scenario-based multiobjective optimization test problem."""
    constants = [Constant(name="c_1", symbol="c_1", value=3)]
    variables = [
        Variable(
            name="x_1",
            symbol="x_1",
            lowerbound=-5.1,
            upperbound=6.2,
            initial_value=0,
            variable_type=VariableTypeEnum.real,
        ),
        Variable(
            name="x_2",
            symbol="x_2",
            lowerbound=-5.2,
            upperbound=6.1,
            initial_value=0,
            variable_type=VariableTypeEnum.real,
        ),
    ]

    constraints = [
        Constraint(
            name="con_1",
            symbol="con_1",
            cons_type=ConstraintTypeEnum.LTE,
            func="x_1 + x_2 - 15",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys="s_1",
        ),
        Constraint(
            name="con_2",
            symbol="con_2",
            cons_type=ConstraintTypeEnum.LTE,
            func="x_1 + x_2 - 65",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys="s_2",
        ),
        Constraint(
            name="con_3",
            symbol="con_3",
            cons_type=ConstraintTypeEnum.LTE,
            func="x_2 - 50",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys=None,
        ),
        Constraint(
            name="con_4",
            symbol="con_4",
            cons_type=ConstraintTypeEnum.LTE,
            func="x_1 - 5",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys=["s_1", "s_2"],
        ),
    ]

    expr_1 = "x_1 + x_2"
    expr_2 = "x_1 - x_2"
    expr_3 = "(x_1 - 3)**2 + x_2"
    expr_4 = "c_1 + x_2**2 - x_1"
    expr_5 = "-x_1 - x_2"

    objectives = [
        Objective(
            name="f_1",
            symbol="f_1",
            func=expr_1,
            maximize=False,
            ideal=-100,
            nadir=100,
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys="s_1",
        ),
        Objective(
            name="f_2",
            symbol="f_2",
            func=expr_2,
            maximize=False,
            ideal=-100,
            nadir=100,
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys=["s_1", "s_2"],
        ),
        Objective(
            name="f_3",
            symbol="f_3",
            func=expr_3,
            maximize=False,
            ideal=-100,
            nadir=100,
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys=None,
        ),
        Objective(
            name="f_4",
            symbol="f_4",
            func=expr_4,
            maximize=False,
            ideal=-100,
            nadir=100,
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys="s_2",
        ),
        Objective(
            name="f_5",
            symbol="f_5",
            func=expr_5,
            maximize=False,
            ideal=-100,
            nadir=100,
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys="s_2",
        ),
    ]

    extra_funcs = [
        ExtraFunction(
            name="extra_1",
            symbol="extra_1",
            func="5*x_1",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
            scenario_keys="s_2",
        )
    ]

    return Problem(
        name="Simple scenario test problem",
        description="For testing the implementation of scenario-based problems.",
        variables=variables,
        constants=constants,
        constraints=constraints,
        objectives=objectives,
        extra_funcs=extra_funcs,
        scenario_keys=["s_1", "s_2"],
    )
