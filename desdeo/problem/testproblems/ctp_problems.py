"""Contains CTP problems."""

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


def ctp1(n_variables: int) -> Problem:
    r"""Defines the CTP1 test problem.

    The problem has a variable number of decision variables and two objective functions to be minimized as
    follows:

    \begin{align*}
        \min\quad f_1(\textbf{x})
        &= x_1 \\[1ex]
        \min\quad f_2(\textbf{x})
        &= g(\textbf{x})
        \exp\!\left(
        -\frac{f_1(\textbf{x})}{g(\textbf{x})}
        \right) \\[1ex]
        g(\textbf{x})
        &= 1 + \frac{9}{n-1}\sum_{i=2}^{n} x_i \\[1ex]
        g_1(\mathbf{x})
        &= 0.858\,\exp(-0.541\,x_1) - f_2(\textbf{x})
        \le 0 \\[1ex]
        g_2(\mathbf{x})
        &= 0.728\,\exp(-0.295\,x_1) - f_2(\textbf{x})
        \le 0 \\[1ex] 0
        &\le x_i \le 1,
        \qquad i = 1,\ldots,n.
    \end{align*}

    where $f_1$ and $f_2$ are objective functions, $x_1,\dots,x_n$ are decision variable, $n$
    is the number of decision variables,
    and $g_1$ and $g_2$ are auxiliary functions.
    """
    n = n_variables

    # function f_1
    f1_expr = "x_1"

    # function g
    g_expr_1 = f"1 + (9 / ({n} - 1))"
    g_expr_2 = "(" + " + ".join([f"x_{i}" for i in range(2, n + 1)]) + ")"
    g_expr = g_expr_1 + " * " + g_expr_2

    # function f_2
    f_2_expr = f"{g_expr} * Exp(-{f1_expr} / ({g_expr}))"

    variables = [
        Variable(
            name=f"x_{i}",
            symbol=f"x_{i}",
            variable_type=VariableTypeEnum.real,
            lowerbound=0.0,
            upperbound=1.0,
        )
        for i in range(1, n_variables + 1)
    ]

    objective_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="x_1",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    objective_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f_2_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    constraint_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"0.858 * Exp(-0.541 * x_1) - ({f_2_expr})",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    constraint_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"0.728 * Exp(-0.295 * x_1) - ({f_2_expr})",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="ctp1",
        description="The CTP1 test problem.",
        variables=variables,
        objectives=[objective_1, objective_2],
        constraints=[constraint_1, constraint_2],
        is_convex=True,
        is_linear=False,
        is_twice_differentiable=True,
    )
