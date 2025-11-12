"""Defines a test problem with a constraint that is multi-valued."""

from desdeo.problem import (
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


def multi_valued_constraint_problem() -> Problem:
    r"""Defines a test problem with a multi-valued constraint.

     The problem has two objectives, two variables, and two constraints, the other of which, is multi-valued.
     The problem is defined as follows:
    \[
         \begin{aligned}
         \text{Min} \quad
         & f_1(x_1, x_2, y) = x_1^2 + x_2^2 + y^2, \\[4pt]
         \text{Min} \quad
         & f_2(x_1, x_2, y) = (x_1 - 2)^2 + (x_2 - 1)^2 + (y - 1)^2, \\[6pt]
         \text{subject to} \quad
         & g(x_1, x_2, y) = x_1^2 + x_2 + y - 2 \le 0, \\[4pt]
         & G(x_1, x_2) = A
         \begin{bmatrix}
         x_1 \\[2pt]
         x_2
         \end{bmatrix}
         \le 0,
         \quad
         A =
         \begin{bmatrix}
         1 & -1 \\[2pt]
         -1 & -2
         \end{bmatrix}.
         \end{aligned}
    \]


    Returns:
         Problem: the problem model.
    """
    xs = TensorVariable(
        name="x",
        symbol="X",
        variable_type=VariableTypeEnum.real,
        shape=[2, 1],
        lowerbounds=-5.0,
        upperbounds=5.0,
        initial_values=0.1,
    )

    y = Variable(
        name="y",
        symbol="y",
        variable_type=VariableTypeEnum.real,
        lowerbound=-10.0,
        upperbound=10.0,
        initial_value=0.1,
    )

    a = TensorConstant(name="A", symbol="A", shape=[2, 2], values=[[1.0, -1.0], [-1.0, -2.0]])

    one = Constant(name="one", symbol="one", value=1.0)

    f_1_expr = "X[1, 1]**2 + X[2, 1]**2 + y**2"
    f_2_expr = "(X[1, 1] - 2)**2 + (X[2, 1] - one)**2 + (y - one)**2"

    g_1_expr = "X[1, 1]**2 + X[2, 1] + y - 2"
    big_g_expr = "A @ X"

    f_1 = Objective(
        name="f1",
        symbol="f_1",
        func=f_1_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=0.0,
        nadir=150.0,
        is_twice_differentiable=True,
    )

    f_2 = Objective(
        name="f2",
        symbol="f_2",
        func=f_2_expr,
        ideal=0.0,
        nadir=206.0,
        objective_type=ObjectiveTypeEnum.analytical,
        is_twice_differentiable=True,
    )

    g_1 = Constraint(
        name="g1", symbol="g_1", cons_type=ConstraintTypeEnum.LTE, func=g_1_expr, is_twice_differentiable=True
    )

    big_g = Constraint(
        name="big_g",
        symbol="G",
        cons_type=ConstraintTypeEnum.LTE,
        func=big_g_expr,
        is_twice_differentiable=True,
        is_linear=True,
        is_convex=True,
    )

    return Problem(
        name="Multi-valued-constraint problem",
        description="Problem for testing problems with multi-valued constraints.",
        constants=[a, one],
        variables=[xs, y],
        constraints=[g_1, big_g],
        objectives=[f_1, f_2],
    )
