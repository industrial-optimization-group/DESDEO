"""Defines a Car-side impact problem with two different variants."""

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


def car_side_impact(three_obj: bool = True) -> Problem:
    r"""The Car-side impact problem with two possible version of the problem with three or four objectives.

    The constraints and objective functions for the car side-impact problem are defined as follows:

    \begin{align}
        \min\quad f_1(\textbf{x})
        &= 1.98 + 4.9x_1 + 6.67x_2 + 6.98x_3 + 4.01x_4
        + 1.78x_5 + 0.00001x_6 + 2.73x_7 \\
        \min\quad f_2(\textbf{x})
        &= 4.72 - 0.5x_4 - 0.19x_2x_3 \\
        \min\quad f_3(\textbf{x})
        &= 0.5 * (V_{MBP} + V_{FD}) \\
        \min\quad f_4(\textbf{x})
        &= \max(1.16 - 0.3717x_2x_4 - 0.0092928x_3 - 1.0, 0) \\
        &+ \max(0.261 - 0.0159x_1x_2 - 0.06486x_1 - 0.019x_2x_7
        + 0.0144x_3x_5 + 0.0154464x_6 - 0.32, 0) \\
        &+ \max(0.214 + 0.00817x_5 - 0.045195x_1 - 0.0135168x_1 + 0.03099x_2x_6 - 0.018x_2x_7
        + 0.007176x_3 + 0.023232x_3 - 0.00364x_5x_6 - 0.018x_2^2 - 0.32) \\
        &+ \max(0.74 - 0.61x_2 - 0.031296x_3 - 0.031872x_7 + 0.227x_2^2 - 0.32,0) \\
        &+ \max(28.98 + 3.818x_3 - 4.2x_1x_2 + 1.27296x_6 - 2.68065x_7 - 32.0,0) \\
        &+ \max(33.86 + 2.95x_3 - 5.057x_1x_2 - 3.795x_2 - 3.4431x_7 + 1.45728 - 32.0,0) \\
        &+ \max(46.36 - 9.9x_2 - 4.4505x_1 - 32.0,0) \\
        &+ \max(4.72 - 0.5x_4 - 0.19x_2x_3 - 4.0, 0) \\
        &+ \max(10.58 - 0.674x_1x_2 - 0.67275x_2 - 9.9, 0) \\
        &+ \max(16.45 - 0.489x_3x_7 - 0.843x_5x_6 - 15.7, 0) \\
        g_1(\mathbf{x})
        &= 1.16 - 0.3717x_2x_4 - 0.0092928x_3 \leq 1.0 \\
        g_2(\mathbf{x})
        &= 0.261 - 0.0159x_1x_2 - 0.06486x_1
        - 0.019x_2x_7 + 0.0144x_3x_5
        + 0.0154464x_6 \leq 0.32 \\
        g_3(\mathbf{x})
        &= 0.214 + 0.00817x_5 - 0.045195x_1
        - 0.0135168x_1 + 0.03099x_2x_6
        - 0.018x_2x_7 + 0.007176x_3
        + 0.023232x_3 - 0.00364x_5x_6
        - 0.018x_2^2 \leq 0.32 \\
        g_4(\mathbf{x})
        &= 0.74 - 0.61x_2 - 0.031296x_3
        - 0.031872x_7 + 0.227x_2^2
        \leq 0.32 \\
        g_5(\mathbf{x})
        &= 28.98 + 3.818x_3
        - 4.2x_1x_2
        + 1.27296x_6
        - 2.68065x_7
        \leq 32.0 \\
        g_6(\mathbf{x})
        &= 33.86 + 2.95x_3
        - 5.057x_1x_2
        - 3.795x_2
        - 3.4431x_7
        + 1.45728
        \leq 32.0 \\
        g_7(\mathbf{x})
        &= 46.36 - 9.9x_2 - 4.4505x_1
        \leq 32.0 \\
        g_8(\mathbf{x})
        &= 4.72 - 0.5x_4 - 0.19x_2x_3
        \leq 4.0 \\
        g_9(\mathbf{x})
        &= 10.58 - 0.674x_1x_2 - 0.67275x_2
        \leq 9.9 \\
        g_{10}(\mathbf{x})
        &= 16.45 - 0.489x_3x_7 - 0.843x_5x_6
        \leq 15.7

        \mathbf{x}^{L} \leq \mathbf{x} \leq \mathbf{x}^{U},

        where

        \[
        \mathbf{x}^{L} = (0.5,\,0.45,\,0.5,\,0.5,\,0.875,\,0.4,\,0.4),
        \]

        \[
        \mathbf{x}^{U} = (1.5,\,1.35,\,1.5,\,1.5,\,2.625,\,1.2,\,1.2).
        \]
    \end{align}

    Arguments:
        three_obj (bool): If true, utilize three objectives version.
            If false, utilize four objectives version. Default is true.


    Returns:
        Problem: A problem instance representing the Car-side impact problem.

    References:
        Jain, H., & Deb, K. (2014). An evolutionary many-objective optimization algorithm using
        reference-point based nondominated sorting approach, part II. IEEE TEVC, 18(4), 602-622.

        Three objective problem from:

        Jain, H. & Deb, K. (2014). An Evolutionary Many-Objective Optimization Algorithm
        Using Reference-Point Based Nondominated Sorting Approach, Part II: Handling Constraints
        and Extending to an Adaptive Approach. IEEE transactions on evolutionary computation,
        18(4), 602-622.

        Optional fourth objective from:

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world
        multi-objective optimization problem suite.
        Applied soft computing, 89, 106078.

        Variable names from:

        Deb, K., Gupta, S., Daum, D., Branke, J., Mall, A. & Padmanabhan, D. (2009).
        Reliability-Based Optimization Using Evolutionary Algorithms.
        IEEE transactions on evolutionary computation, 13(5), 1054-1074.
    """
    x_1 = Variable(
        name="x_1",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.5,
        upperbound=1.5,
    )

    x_2 = Variable(
        name="x_2",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.45,
        upperbound=1.35,
    )

    x_3 = Variable(
        name="x_3",
        symbol="x_3",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.5,
        upperbound=1.5,
    )

    x_4 = Variable(
        name="x_4",
        symbol="x_4",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.5,
        upperbound=1.5,
    )

    x_5 = Variable(
        name="x_5",
        symbol="x_5",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.875,
        upperbound=2.625,
    )

    x_6 = Variable(
        name="x_6",
        symbol="x_6",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.4,
        upperbound=1.2,
    )

    x_7 = Variable(
        name="x_7",
        symbol="x_7",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.4,
        upperbound=1.2,
    )

    g_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func="1.16 - 0.3717 * x_2 * x_4 - 0.0092928 * x_3 - 1.0",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func=(
            "0.261"
            " - 0.0159 * x_1 * x_2"
            " - 0.06486 * x_1"
            " - 0.019 * x_2 * x_7"
            " + 0.0144 * x_3 * x_5"
            " + 0.0154464 * x_6"
            " - 0.32"
        ),
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_3 = Constraint(
        name="g_3",
        symbol="g_3",
        cons_type=ConstraintTypeEnum.LTE,
        func=(
            "0.214"
            " + 0.00817 * x_5"
            " - 0.045195 * x_1"
            " - 0.0135168 * x_1"
            " + 0.03099 * x_2 * x_6"
            " - 0.018 * x_2 * x_7"
            " + 0.007176 * x_3"
            " + 0.023232 * x_3"
            " - 0.00364 * x_5 * x_6"
            " - 0.018 * x_2**2"
            " - 0.32"
        ),
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_4 = Constraint(
        name="g_4",
        symbol="g_4",
        cons_type=ConstraintTypeEnum.LTE,
        func="0.74 - 0.61 * x_2 - 0.031296 * x_3 - 0.031872 * x_7 + 0.227 * x_2**2 - 0.32",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_5 = Constraint(
        name="g_5",
        symbol="g_5",
        cons_type=ConstraintTypeEnum.LTE,
        func="28.98 + 3.818 * x_3 - 4.2 * x_1 * x_2 + 1.27296 * x_6 - 2.68065 * x_7 - 32.0",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_6 = Constraint(
        name="g_6",
        symbol="g_6",
        cons_type=ConstraintTypeEnum.LTE,
        func="33.86 + 2.95 * x_3 - 5.057 * x_1 * x_2 - 3.795 * x_2 - 3.4431 * x_7 + 1.45728 - 32.0",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_7 = Constraint(
        name="g_7",
        symbol="g_7",
        cons_type=ConstraintTypeEnum.LTE,
        func="46.36 - 9.9 * x_2 - 4.4505 * x_1 - 32.0",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_8 = Constraint(
        name="g_8",
        symbol="g_8",
        cons_type=ConstraintTypeEnum.LTE,
        func="4.72 - 0.5 * x_4 - 0.19 * x_2 * x_3 - 4.0",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_9 = Constraint(
        name="g_9",
        symbol="g_9",
        cons_type=ConstraintTypeEnum.LTE,
        func="10.58 - 0.674 * x_1 * x_2 - 0.67275 * x_2 - 9.9",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    g_10 = Constraint(
        name="g_10",
        symbol="g_10",
        cons_type=ConstraintTypeEnum.LTE,
        func="16.45 - 0.489 * x_3 * x_7 - 0.843 * x_5 * x_6 - 15.7",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="1.98 + 4.9 * x_1 + 6.67 * x_2 + 6.98 * x_3 + 4.01 * x_4 + 1.78 * x_5 + 0.00001 * x_6 + 2.73 * x_7",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func="4.72 - 0.5 * x_4 - 0.19 * x_2 * x_3",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func="0.5 * ((10.58 - 0.674 * x_1 * x_2 - 0.67275 * x_2) + (16.45 - 0.489 * x_3 * x_7 - 0.843 * x_5 * x_6))",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    if three_obj:
        objectives = [f_1, f_2, f_3]

    else:
        # If three_obj is false, then problem is with 4 objectives.

        f_4 = Objective(
            name="f_4",
            symbol="f_4",
            func=(
                "Max(1.16 - 0.3717 * x_2 * x_4 - 0.0092928 * x_3 - 1.0, 0)"
                " + Max(0.261 - 0.0159 * x_1 * x_2 - 0.06486 * x_1 - 0.019 * x_2 * x_7"
                " + 0.0144 * x_3 * x_5 + 0.0154464 * x_6 - 0.32, 0)"
                " + Max(0.214 + 0.00817 * x_5 - 0.045195 * x_1 - 0.0135168 * x_1 + 0.03099 * x_2 * x_6"
                " - 0.018 * x_2 * x_7 + 0.007176 * x_3 + 0.023232 * x_3 - 0.00364 * x_5 * x_6"
                " - 0.018 * x_2**2 - 0.32, 0)"
                " + Max(0.74 - 0.61 * x_2 - 0.031296 * x_3 - 0.031872 * x_7 + 0.227 * x_2**2 - 0.32, 0)"
                " + Max(28.98 + 3.818 * x_3 - 4.2*x_1 * x_2 + 1.27296 * x_6 - 2.68065 * x_7 - 32.0, 0)"
                " + Max(33.86 + 2.95 * x_3 - 5.057 * x_1 * x_2 - 3.795 * x_2 - 3.4431 * x_7"
                " + 1.45728 - 32.0, 0)"
                " + Max(46.36 - 9.9 * x_2 - 4.4505 * x_1 - 32.0, 0)"
                " + Max(4.72 - 0.5 * x_4 - 0.19 * x_2 * x_3 - 4.0, 0)"
                " + Max(10.58 - 0.674 * x_1 * x_2 - 0.67275 * x_2 - 9.9, 0)"
                " + Max(16.45 - 0.489 * x_3 * x_7 - 0.843 * x_5 * x_6 - 15.7, 0)"
            ),
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=False,
            is_convex=False,
            is_twice_differentiable=False,
        )

        objectives = [f_1, f_2, f_3, f_4]

    return Problem(
        name="The car-side impact",
        description="The car-side impact problem",
        variables=[x_1, x_2, x_3, x_4, x_5, x_6, x_7],
        objectives=objectives,
        constraints=[g_1, g_2, g_3, g_4, g_5, g_6, g_7, g_8, g_9, g_10],
    )
