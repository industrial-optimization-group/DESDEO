import numpy as np

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)

def re21(f: float = 10.0, sigma: float = 10.0, e: float = 2.0 * 1e5, l: float = 200.0) -> Problem:
    r"""Defines the four bar truss design problem.

    The objective functions and constraints for the four bar truss design problem are defined as follows:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = L(2x_1 + \sqrt{2}x_2 + \sqrt{x_3} + x_4) \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \frac{FL}{E}\left(\frac{2}{x_1} + \frac{2\sqrt{2}}{x_2}
        - \frac{2\sqrt{2}}{x_3} + \frac{2}{x_4}\right) \\
        &\text{s.t.,}   & \frac{F}{\sigma} \leq x_1 & \leq 3\frac{F}{\sigma},\\
        & & \sqrt{2}\frac{F}{\sigma} \leq x_2 & \leq 3\frac{F}{\sigma},\\
        & & \sqrt{2}\frac{F}{\sigma} \leq x_3 & \leq 3\frac{F}{\sigma},\\
        & & \frac{F}{\sigma} \leq x_4 & \leq 3\frac{F}{\sigma},
    \end{align}

    where $x_1, x_4 \in [a, 3a]$, $x_2, x_3 \in [\sqrt{2}a, 3a]$, and $a = F/\sigma$.
    The parameters are defined as $F = 10$ $kN$, $E = 2e^5$ $kN/cm^2$, $L = 200$ $cm$, and $\sigma = 10$ $kN/cm^2$.

    References:
        Cheng, F. Y., & Li, X. S. (1999). Generalized center method for multiobjective engineering optimization.
            Engineering Optimization, 31(5), 641-661.

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective
            optimization problem suite. Applied soft computing, 89, 106078.
            https://doi.org/10.1016/j.asoc.2020.106078.

        https://github.com/ryojitanabe/reproblems/blob/master/reproblem_python_ver/reproblem.py

    Args:
        f (float, optional): Force (kN). Defaults to 10.0.
        sigma (float. optional): Stress (kN/cm^2). Defaults to 10.0.
        e (float, optional): Young modulus? (kN/cm^2). Defaults to 2.0 * 1e5.
        l (float, optional): Length (cm). Defaults to 200.0.

    Returns:
        Problem: an instance of the four bar truss design problem.
    """
    a = f / sigma

    x_1 = Variable(
        name="x_1",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=a,
        upperbound=3 * a,
        initial_value=2 * a,
    )
    x_2 = Variable(
        name="x_2",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=np.sqrt(2.0) * a,
        upperbound=3 * a,
        initial_value=2 * a,
    )
    x_3 = Variable(
        name="x_3",
        symbol="x_3",
        variable_type=VariableTypeEnum.real,
        lowerbound=np.sqrt(2.0) * a,
        upperbound=3 * a,
        initial_value=2 * a,
    )
    x_4 = Variable(
        name="x_4",
        symbol="x_4",
        variable_type=VariableTypeEnum.real,
        lowerbound=a,
        upperbound=3 * a,
        initial_value=2 * a,
    )

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f"{l} * ((2 * x_1) + {np.sqrt(2.0)} * x_2 + Sqrt(x_3) + x_4)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f"({(f * l) / e} * ((2.0 / x_1) + (2.0 * {np.sqrt(2.0)} / x_2) - (2.0 * {np.sqrt(2.0)} / x_3) + (2.0 / x_4)))",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )

    return Problem(
        name="RE21",
        description="the four bar truss design problem",
        variables=[x_1, x_2, x_3, x_4],
        objectives=[f_1, f_2],
    )


def re22() -> Problem:
    r"""The reinforced concrete beam design problem.

    The objective functions and constraints for the reinforced concrete beam design problem are defined as follows:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = 29.4x_1 + 0.6x_2x_3 \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \sum_{i=1}^2 \max\{g_i(\mathbf{x}), 0\} \\
        &\text{s.t.,}   & g_1(\mathbf{x}) & = x_1x_3 - 7.735\frac{x_1^2}{x_2} - 180 \geq 0,\\
        & & g_2(\mathbf{x}) & = 4 - \frac{x_3}{x_2} \geq 0.
    \end{align}

    References:
        Amir, H. M., & Hasegawa, T. (1989). Nonlinear mixed-discrete structural optimization.
            Journal of Structural Engineering, 115(3), 626-646.

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective
            optimization problem suite. Applied soft computing, 89, 106078.
            https://doi.org/10.1016/j.asoc.2020.106078.

        https://github.com/ryojitanabe/reproblems/blob/master/reproblem_python_ver/reproblem.py

    Returns:
        Problem: an instance of the reinforced concrete beam design problem.
    """
    x_2 = Variable(
        name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=20, initial_value=10
    )
    x_3 = Variable(
        name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=40, initial_value=20
    )

    # x_1 pre-defined discrete values
    feasible_values = np.array(
        [
            0.20,
            0.31,
            0.40,
            0.44,
            0.60,
            0.62,
            0.79,
            0.80,
            0.88,
            0.93,
            1.0,
            1.20,
            1.24,
            1.32,
            1.40,
            1.55,
            1.58,
            1.60,
            1.76,
            1.80,
            1.86,
            2.0,
            2.17,
            2.20,
            2.37,
            2.40,
            2.48,
            2.60,
            2.64,
            2.79,
            2.80,
            3.0,
            3.08,
            3.10,
            3.16,
            3.41,
            3.52,
            3.60,
            3.72,
            3.95,
            3.96,
            4.0,
            4.03,
            4.20,
            4.34,
            4.40,
            4.65,
            4.74,
            4.80,
            4.84,
            5.0,
            5.28,
            5.40,
            5.53,
            5.72,
            6.0,
            6.16,
            6.32,
            6.60,
            7.11,
            7.20,
            7.80,
            7.90,
            8.0,
            8.40,
            8.69,
            9.0,
            9.48,
            10.27,
            11.0,
            11.06,
            11.85,
            12.0,
            13.0,
            14.0,
            15.0,
        ]
    )

    variables = [x_2, x_3]

    # forming a set of variables and a constraint to make sure x_1 is from the set of feasible values
    x_1_eprs = []
    for i in range(len(feasible_values)):
        x = Variable(
            name=f"x_1_{i}", symbol=f"x_1_{i}", variable_type=VariableTypeEnum.binary, lowerbound=0, upperbound=1
        )
        variables.append(x)
        expr = f"x_1_{i} * {feasible_values[i]}"
        x_1_eprs.append(expr)
    x_1_eprs = " + ".join(x_1_eprs)

    sum_expr = [f"x_1_{i}" for i in range(len(feasible_values))]
    sum_expr = " + ".join(sum_expr) + " - 1"

    x_1_con = Constraint(
        name="x_1_con", symbol="x_1_con", cons_type=ConstraintTypeEnum.EQ, func=sum_expr, is_linear=True
    )

    g_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"- (({x_1_eprs}) * x_3 - 7.735 * (({x_1_eprs})**2 / x_2) - 180)",
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    g_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func="-(4 - x_3 / x_2)",
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f"29.4 * ({x_1_eprs}) + 0.6 * x_2 * x_3",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f"Max(({x_1_eprs}) * x_3 - 7.735 * (({x_1_eprs})**2 / x_2) - 180, 0) + Max(4 - x_3 / x_2, 0)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=False,
    )
    return Problem(
        name="re22",
        description="The reinforced concrete beam design problem",
        variables=variables,
        objectives=[f_1, f_2],
        constraints=[g_1, g_2, x_1_con],
    )


def re23() -> Problem:
    r"""The pressure vessel design problem.

    The objective functions and constraints for the pressure vessel design problem are defined as follows:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = 0.6224x_1x_3x_4 + 1.7781x_2x_3^2 + 3.1661x_1^2x_4 + 19.84x_1^2x_3 \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \sum_{i=1}^3 \max\{g_i(\mathbf{x}), 0\} \\
        &\text{s.t.,}   & g_1(\mathbf{x}) & = -x_1 + 0.0193x_3 \leq 0,\\
        & & g_2(\mathbf{x}) & = -x_2 + 0.00954x_3 \leq 0, \\
        & & g_3(\mathbf{x}) & = -\pi x_3^2x_4 - \frac{4}{3}\pi x_3^3 + 1\,296\,000 \leq 0.
    \end{align}

    References:
        Kannan, B. K., & Kramer, S. N. (1994). An augmented Lagrange multiplier based method
            for mixed integer discrete continuous optimization and its applications to mechanical design.

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective
            optimization problem suite. Applied soft computing, 89, 106078.
            https://doi.org/10.1016/j.asoc.2020.106078.

        https://github.com/ryojitanabe/reproblems/blob/master/reproblem_python_ver/reproblem.py

    Returns:
        Problem: an instance of the pressure vessel design problem.
    """
    x_1 = Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.integer, lowerbound=1, upperbound=100)
    x_2 = Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.integer, lowerbound=1, upperbound=100)
    x_3 = Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=10, upperbound=200)
    x_4 = Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=10, upperbound=240)

    # variables x_1 and x_2 are integer multiples of 0.0625
    x_1_exprs = "(0.0625 * x_1)"
    x_2_exprs = "(0.0625 * x_2)"

    g_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"-({x_1_exprs} - 0.0193 * x_3)",
        is_linear=True,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    g_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"-({x_2_exprs} - 0.00954 * x_3)",
        is_linear=True,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    g_3 = Constraint(
        name="g_3",
        symbol="g_3",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"-({np.pi} * x_3**2 * x_4 + (4/3) * {np.pi} * x_3**3 - 1296000)",
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f"0.6224 * {x_1_exprs} * x_3 * x_4 + (1.7781 * {x_2_exprs} * x_3**2) + (3.1661 * {x_1_exprs}**2 * x_4) + (19.84 * {x_1_exprs}**2 * x_3)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f"Max({x_1_exprs} - 0.0193 * x_3, 0) + Max({x_2_exprs} - 0.00954 * x_3, 0) + Max({np.pi} * x_3**2 * x_4 + (4/3) * {np.pi} * x_3**3 - 1296000, 0)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=False,
    )
    return Problem(
        name="re23",
        description="The pressure vessel design problem",
        variables=[x_1, x_2, x_3, x_4],
        objectives=[f_1, f_2],
        constraints=[g_1, g_2, g_3],
    )


def re24() -> Problem:
    r"""The hatch cover design problem.

    The objective functions and constraints for the hatch cover design problem are defined as follows:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = x_1 + 120x_2 \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \sum_{i=1}^4 \max\{g_i(\mathbf{x}), 0\} \\
        &\text{s.t.,}   & g_1(\mathbf{x}) & = 1.0 - \frac{\sigma_b}{\sigma_{b,max}} \geq 0,\\
        & & g_2(\mathbf{x}) & = 1.0 - \frac{\tau}{\tau_{max}} \geq 0, \\
        & & g_3(\mathbf{x}) & = 1.0 - \frac{\delta}{\delta_{max}} \geq 0, \\
        & & g_4(\mathbf{x}) & = 1.0 - \frac{\sigma_b}{\sigma_{k}} \geq 0,
    \end{align}

    where $x_1 \in [0.5, 4]$ and $x_2 \in [4, 50]$. The parameters are defined as $\sigma_{b,max} = 700 kg/cm^2$,
    $\tau_{max} = 450 kg/cm$, $\delta_{max} = 1.5 cm$, $\sigma_k = Ex_1^2/100 kg/cm^2$,
    $\sigma_b = 4500/(x_1x_2) kg/cm^2$, $\tau = 1800/x_2 kg/cm^2$, $\delta = 56.2 \times 10^4/(Ex_1x_2^2)$,
    and $E = 700\,000 kg/cm^2$.

    References:
        Amir, H. M., & Hasegawa, T. (1989). Nonlinear mixed-discrete structural optimization.
            Journal of Structural Engineering, 115(3), 626-646.

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective
            optimization problem suite. Applied soft computing, 89, 106078.
            https://doi.org/10.1016/j.asoc.2020.106078.

        https://github.com/ryojitanabe/reproblems/blob/master/reproblem_python_ver/reproblem.py

    Returns:
        Problem: an instance of the hatch cover design problem.
    """
    x_1 = Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.5, upperbound=4)
    x_2 = Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=4, upperbound=50)

    sigma_b = "(4500 / (x_1 * x_2))"
    sigma_k = "((700000 * x_1**2) / 100)"
    tau = "(1800 / x_2)"
    delta = "(56.2 * 10**4 / (700000 * x_1 * x_2**2))"

    g_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"-(1 - {sigma_b} / 700)",
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    g_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"-(1 - {tau} / 450)",
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    g_3 = Constraint(
        name="g_3",
        symbol="g_3",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"-(1 - {delta} / 1.5)",
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    g_4 = Constraint(
        name="g_4",
        symbol="g_4",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"-(1 - {sigma_b} / {sigma_k})",
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="x_1 + 120 * x_2",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f"Max(-(1 - {sigma_b} / 700), 0) + Max(-(1 - {tau} / 450), 0) + Max(-(1 - {delta} / 1.5), 0) + Max(-(1 - {sigma_b} / {sigma_k}), 0)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=False,
    )
    return Problem(
        name="re24",
        description="The hatch cover design problem",
        variables=[x_1, x_2],
        objectives=[f_1, f_2],
        constraints=[g_1, g_2, g_3, g_4],
    )
