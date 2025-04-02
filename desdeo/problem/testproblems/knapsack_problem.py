from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)

def simple_knapsack() -> Problem:
    r"""Defines a simple multiobjective knapsack problem.

    Given a set of 4 items, each with a weight and three values corresponding to
    different objectives, the problem is defined as follows:

    -   Item 1: weight = 2, values = (5, 10, 15)
    -   Item 2: weight = 3, values = (4, 7, 9)
    -   Item 3: weight = 1, values = (3, 5, 8)
    -   Item 4: weight = 4, values = (2, 3, 5)

    The problem is then to maximize the following functions:

    \begin{align*}
    f_1(x) &= 5x_1 + 4x_2 + 3x_3 + 2x_4 \\
    f_2(x) &= 10x_1 + 7x_2 + 5x_3 + 3x_4 \\
    f_3(x) &= 15x_1 + 9x_2 + 8x_3 + 5x_4 \\
    \text{s.t.}\quad & 2x_1 + 3x_2 + 1x_3 + 4x_4 \leq 7 \\
    & x_i \in \{0,1\} \quad \text{for} \quad i = 1, 2, 3, 4,
    \end{align*}

    where the inequality constraint is a weight constraint. The problem is a binary variable problem.

    Returns:
        Problem: the simple knapsack problem.
    """
    variables = [
        Variable(
            name=f"x_{i}",
            symbol=f"x_{i}",
            variable_type=VariableTypeEnum.binary,
            lowerbound=0,
            upperbound=1,
            initial_value=0,
        )
        for i in range(1, 5)
    ]

    exprs = {
        "f1": "5*x_1 + 4*x_2 + 3*x_3 + 2*x_4",
        "f2": "10*x_1 + 7*x_2 + 5*x_3 + 3*x_4",
        "f3": "15*x_1 + 9*x_2 + 8*x_3 + 5*x_4",
    }

    ideals = {"f1": 15, "f2": 25, "f3": 37}

    objectives = [
        Objective(
            name=f"f_{i}",
            symbol=f"f_{i}",
            func=exprs[f"f{i}"],
            maximize=True,
            ideal=ideals[f"f{i}"],
            nadir=0,
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
        )
        for i in range(1, 4)
    ]

    constraints = [
        Constraint(
            name="Weight constraint",
            symbol="g_w",
            cons_type=ConstraintTypeEnum.LTE,
            func="2*x_1 + 3*x_2 + 1*x_3 + 4*x_4 - 7",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
        )
    ]

    return Problem(
        name="Simple knapsack",
        description="A simple knapsack problem with three objectives to be maximized.",
        variables=variables,
        objectives=objectives,
        constraints=constraints,
    )


def simple_knapsack_vectors():
    """Define a simple variant of the knapsack problem that utilizes vectors (TensorVariable and TensorConstant)."""
    n_items = 4
    weight_values = [2, 3, 4, 5]
    profit_values = [3, 5, 6, 8]
    efficiency_values = [4, 2, 7, 3]

    max_weight = Constant(name="Maximum weights", symbol="w_max", value=5)

    weights = TensorConstant(name="Weights of the items", symbol="W", shape=[len(weight_values)], values=weight_values)
    profits = TensorConstant(name="Profits", symbol="P", shape=[len(profit_values)], values=profit_values)
    efficiencies = TensorConstant(
        name="Efficiencies", symbol="E", shape=[len(efficiency_values)], values=efficiency_values
    )

    choices = TensorVariable(
        name="Chosen items",
        symbol="X",
        shape=[n_items],
        variable_type="binary",
        lowerbounds=n_items * [0],
        upperbounds=n_items * [1],
        initial_values=n_items * [1],
    )

    profit_objective = Objective(
        name="max profit",
        symbol="f_1",
        func="P@X",
        maximize=True,
        ideal=8,
        nadir=0,
        is_linear=True,
        is_convex=False,
        is_twice_differentiable=False,
    )

    efficiency_objective = Objective(
        name="max efficiency",
        symbol="f_2",
        func="E@X",
        maximize=True,
        ideal=7,
        nadir=0,
        is_linear=True,
        is_convex=False,
        is_twice_differentiable=False,
    )

    weight_constraint = Constraint(
        name="Weight constraint",
        symbol="g_1",
        cons_type="<=",
        func="W@X - w_max",
        is_linear=True,
        is_convex=False,
        is_twice_differentiable=False,
    )

    return Problem(
        name="Simple two-objective Knapsack problem",
        description="A simple variant of the classic combinatorial problem.",
        constants=[max_weight, weights, profits, efficiencies],
        variables=[choices],
        objectives=[profit_objective, efficiency_objective],
        constraints=[weight_constraint],
    )
