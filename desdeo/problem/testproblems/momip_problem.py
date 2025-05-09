from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


def momip_ti2() -> Problem:
    """Defines the mixed-integer multiobjective optimization problem test instance 2 (TI2).

    The problem has four variables, two continuous and two integer. The Pareto optimal solutions
    hold for solutions with x_1^2 + x_2^2 = 0.25 and (x_3, x_4) = {(0, -1), (-1, 0)}.

    References:
        Eichfelder, G., Gerlach, T., & Warnow, L. (n.d.). Test Instances for
            Multiobjective Mixed-Integer Nonlinear Optimization.
    """
    x_1 = Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=-1.0, upperbound=1.0)
    x_2 = Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=-1.0, upperbound=1.0)
    x_3 = Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.integer, lowerbound=-1, upperbound=1)
    x_4 = Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.integer, lowerbound=-1, upperbound=1)

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="x_1 + x_3",
        objective_type=ObjectiveTypeEnum.analytical,
        maximize=False,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func="x_2 + x_4",
        objective_type=ObjectiveTypeEnum.analytical,
        maximize=False,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    con_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func="x_1**2 + x_2**2 - 0.25",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )
    con_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func="x_3**2 + x_4**2 - 1",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="MOMIP Test Instance 2",
        description="Test instance 2",
        variables=[x_1, x_2, x_3, x_4],
        constraints=[con_1, con_2],
        objectives=[f_1, f_2],
    )


def momip_ti7() -> Problem:
    r"""Defines the mixed-integer multiobjective optimization problem test instance 7 (T7).

    The problem is defined as follows:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = x_1 + x_4 \\
        &\max_{\mathbf{x}} & f_2(\mathbf{x}) & = -(x_2 + x_5) \\
        &\min_{\mathbf{x}} & f_3(\mathbf{x}) & = x_3 + x_6 \\
        &\text{s.t.,}   & x_1^2 +x_2^2 + x_3^2 & \leq 1,\\
        &               & x_4^2 + x_5^2 + x_6^2 & \leq 1,\\
        &               & -1 \leq x_i \leq 1&\;\text{for}\;i=\{1,2,3\},\\
        &               & x_i \in \{-1, 0, 1\}&\;\text{for}\;i=\{4, 5, 6\}.
    \end{align}

    In the problem, $x_1, x_2, x_3$ are real-valued and $x_4, x_5, x_6$ are integer-valued. The problem
    is convex and differentiable.

    The Pareto optimal integer assignments are $(x_4, x_5, x_6) \in {(0,0,-1), (0, -1, 0), (-1,0,0)}$,
    and the real-valued assignments are $\{x_1, x_2, x_3 \in \mathbb{R}^3 |
    x_1^2 + x_2^2 + x_3^2 = 1, x_1 \leq 0, x_2 \leq 0, x_3 \leq 0\}$. Unlike in the original definition,
    $f_2$ is formulated to be maximized instead of minimized.

    References:
        Eichfelder, G., Gerlach, T., & Warnow, L. (n.d.). Test Instances for
            Multiobjective Mixed-Integer Nonlinear Optimization.
    """
    x_1 = Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real)
    x_2 = Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real)
    x_3 = Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real)
    x_4 = Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.integer, lowerbound=-1, upperbound=1)
    x_5 = Variable(name="x_5", symbol="x_5", variable_type=VariableTypeEnum.integer, lowerbound=-1, upperbound=1)
    x_6 = Variable(name="x_6", symbol="x_6", variable_type=VariableTypeEnum.integer, lowerbound=-1, upperbound=1)

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="x_1 + x_4",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=-3,
        nadir=3,
        maximize=False,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func="-(x_2 + x_5)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=3,
        nadir=-3,
        maximize=True,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func="x_3 + x_6",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=-3,
        nadir=3,
        maximize=False,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    con_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func="x_1**2 + x_2**2 + x_3**2 - 1",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )
    con_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func="x_4**2 + x_5**2 + x_6**2 - 1",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="MOMIP Test Instance 7",
        description="Test instance 17",
        variables=[x_1, x_2, x_3, x_4, x_5, x_6],
        constraints=[con_1, con_2],
        objectives=[f_1, f_2, f_3],
    )
