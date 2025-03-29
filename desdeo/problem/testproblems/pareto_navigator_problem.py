from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)

def pareto_navigator_test_problem() -> Problem:
    r"""Defines the problem utilized in the (convex) Pareto navigator article.

    The problem is defined as follows:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = -x_1 - x_2 + 5 \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = 0.2(x_1^2 -10x_1 + x_2^2 - 4x_2 + 11) \\
        &\min_{\mathbf{x}} & f_3(\mathbf{x}) & = (5 - x_1)(x_2 - 11)\\
        &\text{s.t.,}   & 3x_1 + x_2 - 12 & \leq 0,\\
        &               & 2x_1 + x_2 - 9 & \leq 0,\\
        &               & x_1 + 2x_2 - 12 & \leq 0,\\
        &               & 0 \leq x_1 & \leq 4,\\
        &               & 0 \leq x_2 & \leq 6.
    \end{align}

    The problem comes with seven pre-defined Pareto optimal solutions that were
    utilized in the original article as well. From these, the ideal and nadir
    points of the problem are approximated also.

    References:
        Eskelinen, P., Miettinen, K., Klamroth, K., & Hakanen, J. (2010). Pareto
            navigator for interactive nonlinear multiobjective optimization. OR
            Spectrum, 32(1), 211-227.
    """
    x_1 = Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=4)
    x_2 = Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=6)

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="-x_1 - x_2 + 5",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=-2.0,
        nadir=5.0,
        maximize=False,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func="0.2*(x_1**2 - 10*x_1 + x_2**2 - 4*x_2 + 11)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=-3.1,
        nadir=4.60,
        maximize=False,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func="(5 - x_1) * (x_2 - 11)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=-55.0,
        nadir=-14.25,
        maximize=False,
    )

    con_1 = Constraint(name="g_1", symbol="g_1", func="3*x_1 + x_2 - 12", cons_type=ConstraintTypeEnum.LTE)
    con_2 = Constraint(name="g_2", symbol="g_2", func="2*x_1 + x_2 - 9", cons_type=ConstraintTypeEnum.LTE)
    con_3 = Constraint(name="g_3", symbol="g_3", func="x_1 + 2*x_2 - 12", cons_type=ConstraintTypeEnum.LTE)

    representation = DiscreteRepresentation(
        variable_values={"x_1": [0, 0, 0, 0, 0, 0, 0], "x_2": [0, 0, 0, 0, 0, 0, 0]},
        objective_values={
            "f_1": [-2.0, -1.0, 0.0, 1.38, 1.73, 2.48, 5.0],
            "f_2": [0.0, 4.6, -3.1, 0.62, 1.72, 1.45, 2.2],
            "f_3": [-18.0, -25.0, -14.25, -35.33, -38.64, -42.41, -55.0],
        },
        non_dominated=True,
    )

    return Problem(
        name="The (convex) Pareto navigator problem.",
        description="The test problem used in the (convex) Pareto navigator paper.",
        variables=[x_1, x_2],
        objectives=[f_1, f_2, f_3],
        constraints=[con_1, con_2, con_3],
        discrete_representation=representation,
    )
