"""The vehicle crash worthiness multiobjective optimization problem."""

from desdeo.problem.schema import (
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


def vehicle_crashworthiness() -> Problem:
    r"""Defines the vehicle crash worthiness design problem.

    Five decision variables describing the thickness of reinforced members
    (in mm) drive three minimized objectives: the frontal mass of the
    vehicle (kg), the collision acceleration experienced by passengers
    (m/s^2), and the toe board intrusion in the offset frontal crash (mm).
    Each $x_i$ is bounded in $[1, 3]$. The objective functions are the
    polynomial surrogate models from Liao et al. 2008.

    References:
        Liao, X., Li, Q., Yang, X., Zhang, W. & Li, W. (2007).
            Multiobjective optimization for crash safety design of vehicles
            using stepwise regression model. Structural and Multidisciplinary
            Optimization, 35(6), 561-569.
            https://doi.org/10.1007/s00158-007-0163-x

    Returns:
        Problem: an instance of the vehicle crash worthiness problem.
    """
    variables = [
        Variable(
            name=f"x_{i}",
            symbol=f"x_{i}",
            variable_type=VariableTypeEnum.real,
            lowerbound=1.0,
            upperbound=3.0,
            initial_value=2.0,
        )
        for i in range(1, 6)
    ]

    f_1_expr = "1640.2823 + 2.3573285 * x_1 + 2.3220035 * x_2 + 4.5688768 * x_3 + 7.7213633 * x_4 + 4.4559504 * x_5"
    f_2_expr = (
        "6.5856"
        " + 1.15 * x_1"
        " - 1.0427 * x_2"
        " + 0.9738 * x_3"
        " + 0.8364 * x_4"
        " - 0.3695 * x_1 * x_4"
        " + 0.0861 * x_1 * x_5"
        " + 0.3628 * x_2 * x_4"
        " - 0.1106 * x_1**2"
        " - 0.3437 * x_3**2"
        " + 0.1764 * x_4**2"
    )
    f_3_expr = (
        "-0.0551"
        " + 0.0181 * x_1"
        " + 0.1024 * x_2"
        " + 0.0421 * x_3"
        " - 0.0073 * x_1 * x_2"
        " + 0.024 * x_2 * x_3"
        " - 0.0118 * x_2 * x_4"
        " - 0.0204 * x_3 * x_4"
        " - 0.008 * x_3 * x_5"
        " - 0.0241 * x_2**2"
        " + 0.0109 * x_4**2"
    )

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f_1_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        maximize=False,
        ideal=1600.0,
        nadir=1700.0,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f_2_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        maximize=False,
        ideal=6.0,
        nadir=12.0,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func=f_3_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        maximize=False,
        ideal=0.038,
        nadir=0.30,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="vehicle_crashworthiness",
        description="The vehicle crash worthiness design problem (Liao et al. 2008).",
        variables=variables,
        objectives=[f_1, f_2, f_3],
    )
