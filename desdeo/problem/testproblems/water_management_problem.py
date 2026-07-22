"""Contains implementation of water management problem."""

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


def water_management(six_obj=False) -> Problem:
    r"""Water resource planning problem.

    The constraints and objective functions for the water management problem are defined as follows:

    \begin{align}
        \min\quad f_1(\mathbf{x})
        &= 106780.37(x_2 + x_3) + 61704.67 \\
        \min\quad f_2(\mathbf{x})
        &= 3000x_1 \\
        \min\quad f_3(\mathbf{x})
        &= \frac{305700 \cdot 2289 x_2} {(0.06 \cdot 2289)^{0.65}} \\
        \min\quad f_4(\mathbf{x})
        &= 250 \cdot 2289 \cdot \exp(-39.75x_2 + 9.9x_3 + 2.74) \\
        \min\quad f_5(\mathbf{x})
        &= 25\left( \frac{1.39}{x_1x_2} + 4940x_3 - 80 \right) \\
        g_1(\mathbf{x})
        &= \frac{0.00139}{x_1 x_2} + 4.94x_3 - 0.08 \leq 1.00 \\
        g_2(\mathbf{x})
        &= \frac{0.000306}{x_1 x_2} + 1.082x_3 - 0.0986 \leq 1.00 \\
        g_3(\mathbf{x})
        &= \frac{12.307}{x_1 x_2} + 49408.24x_3 + 4051.02 \leq 50000.00 \\
        g_4(\mathbf{x})
        &= \frac{2.098}{x_1 x_2} + 8046.33x_3 - 696.71 \leq 16000.00 \\
        g_5(\mathbf{x})
        &= \frac{2.138}{x_1 x_2} + 7883.39x_3 - 705.04 \leq 10000.00 \\
        g_6(\mathbf{x})
        &= \frac{0.417}{x_1 x_2} + 1721.26x_3 - 136.54 \leq 2000.00 \\
        g_7(\mathbf{x})
        &= \frac{0.164}{x_1 x_2} + 631.13x_3 - 54.48 \leq 550.00 \\
        \mathbf{x}^{L} &\leq \mathbf{x} \leq \mathbf{x}^{U},
    \end{align}

    where the lower and upper bounds on the variables are

    \[
    \mathbf{x}^{L} = (0.01,\,0.01,\,0.01),
    \qquad
    \mathbf{x}^{U} = (0.45,\,0.10,\,0.10).
    \]

    Arguments:
            six_obj (bool): If False, use the original 5 objectives. If true, use the sum of contraint violations as
                the 6th objective. Default is False.

    References:
        Ray, T., Tai, K., & Seow, K. C. (2001). Multiobjective design optimization by an evolutionary algorithm.
        Engineering Optimization, 33(4), 399-424. (Section 4.4.)

    Returns:
        Problem: an instance of the water management problem.
    """
    x_1 = Variable(
        name="x_1",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.01,
        upperbound=0.45,
        initial_value=0.2,
    )

    x_2 = Variable(
        name="x_2",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.01,
        upperbound=0.10,
        initial_value=0.05,
    )

    x_3 = Variable(
        name="x_3",
        symbol="x_3",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.01,
        upperbound=0.10,
        initial_value=0.05,
    )

    # Constraints

    g_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func="0.00139 / (x_1 * x_2) + 4.94 * x_3 - 0.08 - 1.00",
        is_linear=False,
    )

    g_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func="0.000306 / (x_1 * x_2) + 1.082 * x_3 - 0.0986 - 1.00",
        is_linear=False,
    )

    g_3 = Constraint(
        name="g_3",
        symbol="g_3",
        cons_type=ConstraintTypeEnum.LTE,
        func="12.307 / (x_1 * x_2) + 49408.24 * x_3 + 4051.02 - 50000.00",
        is_linear=False,
    )

    g_4 = Constraint(
        name="g_4",
        symbol="g_4",
        cons_type=ConstraintTypeEnum.LTE,
        func="2.098 / (x_1 * x_2) + 8046.33 * x_3 - 696.71 - 16000.00",
        is_linear=False,
    )

    g_5 = Constraint(
        name="g_5",
        symbol="g_5",
        cons_type=ConstraintTypeEnum.LTE,
        func="2.138 / (x_1 * x_2) + 7883.39 * x_3 - 705.04 - 10000.00",
        is_linear=False,
    )

    g_6 = Constraint(
        name="g_6",
        symbol="g_6",
        cons_type=ConstraintTypeEnum.LTE,
        func="0.417 / (x_1 * x_2) + 1721.26 * x_3 - 136.54 - 2000.00",
        is_linear=False,
    )

    g_7 = Constraint(
        name="g_7",
        symbol="g_7",
        cons_type=ConstraintTypeEnum.LTE,
        func="0.164 / (x_1 * x_2) + 631.13 * x_3 - 54.48 - 550.00",
        is_linear=False,
    )

    # Objectives

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="106780.37 * (x_2 + x_3) + 61704.67",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=True,
        is_twice_differentiable=True,
    )

    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func="3000 * x_1",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func="(305700 * 2289.0 * x_2)/((0.06*2289)**0.65)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=True,
        is_twice_differentiable=True,
    )

    f_4 = Objective(
        name="f_4",
        symbol="f_4",
        func="250 * 2289 * Exp(-39.75 * x_2 + 9.9 * x_3 + 2.74)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=True,
        is_twice_differentiable=True,
    )

    f_5 = Objective(
        name="f_5",
        symbol="f_5",
        func="25 * ((1.39 / (x_1 * x_2)) + 4940 * x_3 - 80)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=True,
        is_twice_differentiable=True,
    )

    objectives = [f_1, f_2, f_3, f_4, f_5]
    if six_obj:
        big_func = (
            "Max(0.00139 / (x_1 * x_2) + 4.94 * x_3 - 0.08 - 1.00, 0)"
            " + Max(0.000306 / (x_1 * x_2) + 1.082 * x_3 - 0.0986 - 1.00, 0)"
            " + Max(12.307 / (x_1 * x_2) + 49408.24 * x_3 + 4051.02 - 50000.00, 0)"
            " + Max(2.098 / (x_1 * x_2) + 8046.33 * x_3 - 696.71 - 16000.00, 0)"
            " + Max(2.138 / (x_1 * x_2) + 7883.39 * x_3 - 705.04 - 10000.00, 0)"
            " + Max(0.417 / (x_1 * x_2) + 1721.26 * x_3 - 136.54 - 2000.00, 0)"
            " + Max(0.164 / (x_1 * x_2) + 631.13 * x_3 - 54.48 - 550.00, 0)"
        )
        f_6 = Objective(
            name="f_6",
            symbol="f_6",
            func=big_func,
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=False,
            is_convex=True,
            is_twice_differentiable=False,
        )
        objectives.append(f_6)

    return Problem(
        name="water_management_problem",
        description="Water resource planning problem",
        variables=[x_1, x_2, x_3],
        objectives=objectives,
        constraints=[
            g_1,
            g_2,
            g_3,
            g_4,
            g_5,
            g_6,
            g_7,
        ],
    )
