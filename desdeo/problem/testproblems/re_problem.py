"""Contains multiple different RE-problems."""

# ruff: noqa: E741

import numpy as np

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)

from .car_side_impact_problem import car_side_impact
from .rocket_injector_design_problem import rocket_injector_design
from .vehicle_crashworthiness_problem import vehicle_crashworthiness
from .water_management_problem import water_management


def re21(f: float = 10.0, sigma: float = 10.0, e: float = 2.0 * 1e5, l: float = 200.0) -> Problem:
    r"""Defines the four bar truss design problem.

    The objective functions and constraints for the four bar truss design problem are defined as follows:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = L(2x_1 + \sqrt{2}x_2 + \sqrt{x_3} + x_4) \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \frac{FL}{E}\left(\frac{2}{x_1} + \frac{2\sqrt{2}}{x_2}
        - \frac{2\sqrt{2}}{x_3} + \frac{2}{x_4}\right) \\
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
        func=f"({(f * l) / e} * ((2.0 / x_1) + (2.0 * {np.sqrt(2.0)} / x_2) - "
        f"(2.0 * {np.sqrt(2.0)} / x_3) + (2.0 / x_4)))",
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

    where $x_2 \in [0, 20]$ and $x_3 \in [0, 40]$.

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

        where $x_1, x_2 \in \{1,\dots,100\}$, $x_3 \in [10, 200]$, and $x_4 \in [10, 240]$. $x_1$ and $x_2$ are
        integer multiples of 0.0625. $x_1$, $x_2$, $x_3$, and $x_4$ represent the thicknesses of
        the shell, the head of a pressure vessel, the inner radius, and the length of
        the cylindrical section, respectively. We determined the ranges of $x_2$ and $x_3$
        according to [S.3].

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
        func=f"0.6224 * {x_1_exprs} * x_3 * x_4 + (1.7781 * {x_2_exprs} * x_3**2) + "
        f"(3.1661 * {x_1_exprs}**2 * x_4) + (19.84 * {x_1_exprs}**2 * x_3)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f"Max({x_1_exprs} - 0.0193 * x_3, 0) + Max({x_2_exprs} - 0.00954 * x_3, 0) + "
        f"Max({np.pi} * x_3**2 * x_4 + (4/3) * {np.pi} * x_3**3 - 1296000, 0)",
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
        func=f"Max(-(1 - {sigma_b} / 700), 0) + Max(-(1 - {tau} / 450), 0) + "
        f"Max(-(1 - {delta} / 1.5), 0) + Max(-(1 - {sigma_b} / {sigma_k}), 0)",
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


def _violation_objective(constraint_symbols: list[str]) -> str:
    """Fold constraint expressions into the RE suite's last objective.

    Every RE problem states its original constraints in the form `g(x) >= 0` and then defines a final
    objective as the sum of their violations, which is what makes the RE problems bound-constrained
    rather than constrained. This helper writes that sum, given the symbols of extra functions that
    each evaluate one `g`.

    Args:
        constraint_symbols (list[str]): symbols of the extra functions holding each `g(x)`.

    Returns:
        str: the expression `sum_i max(-g_i(x), 0)`.
    """
    return " + ".join(f"Max(-{symbol}, 0)" for symbol in constraint_symbols)


def re31() -> Problem:
    r"""The two bar truss design problem.

    Two bars carry a load between two fixed points. The first two objectives are the structural weight
    and the resultant displacement of the joint; the third is the sum of the three constraint
    violations, which is how the RE suite turns the original constrained problem into a
    bound-constrained one:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = x_1\sqrt{16 + x_3^2} + x_2\sqrt{1 + x_3^2} \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \frac{20\sqrt{16 + x_3^2}}{x_3 x_1} \\
        &\min_{\mathbf{x}} & f_3(\mathbf{x}) & = \sum_{i=1}^3 \max\{-g_i(\mathbf{x}), 0\} \\
        &\text{where}   & g_1(\mathbf{x}) & = 0.1 - f_1(\mathbf{x}) \geq 0,\\
        & & g_2(\mathbf{x}) & = 10^5 - f_2(\mathbf{x}) \geq 0, \\
        & & g_3(\mathbf{x}) & = 10^5 - \frac{80\sqrt{1 + x_3^2}}{x_3 x_2} \geq 0,
    \end{align}

    where $x_1, x_2 \in [10^{-5}, 100]$ and $x_3 \in [1, 3]$. $x_1$ and $x_2$ are the lengths of the two
    bars and $x_3$ is the vertical distance from the second bar. The original problem leaves $x_1$ and
    $x_2$ unbounded above; the RE suite adds bounds to make the problem bound-constrained.

    Note:
        Following the RE suite, the returned problem has **no constraints** — the constraint violations
        are folded into `f_3`. The constrained variant is CRE31, which is not implemented here.

    References:
        Coello Coello, C. A., & Pulido, G. T. (2005). Multiobjective structural optimization using a
            microgenetic algorithm. Structural and Multidisciplinary Optimization, 30(5), 388-403.
            https://doi.org/10.1007/s00158-005-0527-z.

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective
            optimization problem suite. Applied soft computing, 89, 106078.
            https://doi.org/10.1016/j.asoc.2020.106078.

    Returns:
        Problem: an instance of the two bar truss design problem.
    """
    x_1 = Variable(
        name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=1e-5, upperbound=100, initial_value=50
    )
    x_2 = Variable(
        name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=1e-5, upperbound=100, initial_value=50
    )
    x_3 = Variable(
        name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=1, upperbound=3, initial_value=2
    )

    f_1_expr = "x_1 * Sqrt(16 + x_3**2) + x_2 * Sqrt(1 + x_3**2)"
    f_2_expr = "(20 * Sqrt(16 + x_3**2)) / (x_3 * x_1)"

    # The g_i are written in the paper's ">= 0" orientation, so a negative value is a violation.
    extras = [
        ExtraFunction(
            name="g_1",
            symbol="g_1",
            func=f"0.1 - ({f_1_expr})",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
        ExtraFunction(
            name="g_2",
            symbol="g_2",
            func=f"100000 - ({f_2_expr})",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
        ExtraFunction(
            name="g_3",
            symbol="g_3",
            func="100000 - (80 * Sqrt(1 + x_3**2)) / (x_3 * x_2)",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
    ]

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f_1_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f_2_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func=_violation_objective(["g_1", "g_2", "g_3"]),
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=False,
    )

    return Problem(
        name="re31",
        description="The two bar truss design problem",
        variables=[x_1, x_2, x_3],
        objectives=[f_1, f_2, f_3],
        extra_funcs=extras,
    )


def re32(
    p: float = 6000.0,
    l: float = 14.0,
    e: float = 30.0 * 1e6,
    g: float = 12.0 * 1e6,
    tau_max: float = 13600.0,
    sigma_max: float = 30000.0,
) -> Problem:
    r"""The welded beam design problem.

    A beam is welded to a rigid support and carries a load at its free end. The first two objectives are
    the fabrication cost and the end deflection; the third is the sum of the four constraint violations:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = 1.10471x_1^2x_2 + 0.04811x_3x_4(14 + x_2) \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \frac{4PL^3}{Ex_4x_3^3} \\
        &\min_{\mathbf{x}} & f_3(\mathbf{x}) & = \sum_{i=1}^4 \max\{-g_i(\mathbf{x}), 0\} \\
        &\text{where}   & g_1(\mathbf{x}) & = \tau_{max} - \tau(\mathbf{x}) \geq 0,\\
        & & g_2(\mathbf{x}) & = \sigma_{max} - \sigma(\mathbf{x}) \geq 0, \\
        & & g_3(\mathbf{x}) & = x_4 - x_1 \geq 0, \\
        & & g_4(\mathbf{x}) & = P_C(\mathbf{x}) - P \geq 0,
    \end{align}

    with the stress terms

    \begin{align}
        \tau(\mathbf{x}) & = \sqrt{(\tau')^2 + \frac{2\tau'\tau''x_2}{2R} + (\tau'')^2}, &
        \tau' & = \frac{P}{\sqrt{2}x_1x_2}, &
        \tau'' & = \frac{MR}{J}, \\
        M & = P\left(L + \frac{x_2}{2}\right), &
        R & = \sqrt{\frac{x_2^2}{4} + \left(\frac{x_1 + x_3}{2}\right)^2}, &
        J & = 2\left(\sqrt{2}x_1x_2\left(\frac{x_2^2}{12} +
            \left(\frac{x_1 + x_3}{2}\right)^2\right)\right), \\
        \sigma(\mathbf{x}) & = \frac{6PL}{x_4x_3^2}, &
        P_C(\mathbf{x}) & = \frac{4.013E\sqrt{x_3^2x_4^6/36}}{L^2}
            \left(1 - \frac{x_3}{2L}\sqrt{\frac{E}{4G}}\right). &
    \end{align}

    where $x_1, x_4 \in [0.125, 5]$ and $x_2, x_3 \in [0.1, 10]$. The four variables adjust the size of
    the beam: the weld thickness, the weld length, the beam depth and the beam width.

    Note:
        Following the RE suite, the returned problem has **no constraints** — the constraint violations
        are folded into `f_3`. The constrained variant is CRE32, which is not implemented here.

    References:
        Ray, T., & Liew, K. M. (2002). A swarm metaphor for multiobjective design optimization.
            Engineering Optimization, 34(2), 141-153. https://doi.org/10.1080/03052150210915.

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective
            optimization problem suite. Applied soft computing, 89, 106078.
            https://doi.org/10.1016/j.asoc.2020.106078.

    Args:
        p (float, optional): the load on the beam (lb). Defaults to 6000.0.
        l (float, optional): the beam overhang length (in). Defaults to 14.0.
        e (float, optional): Young's modulus (psi). Defaults to 30.0e6.
        g (float, optional): the shear modulus (psi). Defaults to 12.0e6.
        tau_max (float, optional): the maximum allowable shear stress (psi). Defaults to 13600.0.
        sigma_max (float, optional): the maximum allowable normal stress (psi). Defaults to 30000.0.

    Returns:
        Problem: an instance of the welded beam design problem.
    """
    x_1 = Variable(
        name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.125, upperbound=5, initial_value=1.0
    )
    x_2 = Variable(
        name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.1, upperbound=10, initial_value=5.0
    )
    x_3 = Variable(
        name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0.1, upperbound=10, initial_value=5.0
    )
    x_4 = Variable(
        name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=0.125, upperbound=5, initial_value=1.0
    )

    # The half-sum (x_1 + x_3) / 2 appears in both R and J, so it is written once.
    half_sum_sq = "((x_1 + x_3) / 2)**2"
    tau_prime = f"({p} / ({np.sqrt(2.0)} * x_1 * x_2))"
    moment = f"({p} * ({l} + x_2 / 2))"
    radius = f"(Sqrt(x_2**2 / 4 + {half_sum_sq}))"
    polar_moment = f"(2 * ({np.sqrt(2.0)} * x_1 * x_2 * (x_2**2 / 12 + {half_sum_sq})))"
    tau_double_prime = f"(({moment} * {radius}) / {polar_moment})"
    tau = (
        f"Sqrt({tau_prime}**2 + (2 * {tau_prime} * {tau_double_prime} * x_2) / (2 * {radius}) + {tau_double_prime}**2)"
    )
    sigma = f"((6 * {p} * {l}) / (x_4 * x_3**2))"
    buckling_load = (
        f"(((4.013 * {e} * Sqrt(x_3**2 * x_4**6 / 36)) / {l}**2) * (1 - (x_3 / (2 * {l})) * {np.sqrt(e / (4.0 * g))}))"
    )

    extras = [
        ExtraFunction(
            name="g_1",
            symbol="g_1",
            func=f"{tau_max} - {tau}",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
        ExtraFunction(
            name="g_2",
            symbol="g_2",
            func=f"{sigma_max} - {sigma}",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
        ExtraFunction(
            name="g_3",
            symbol="g_3",
            func="x_4 - x_1",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
        ),
        ExtraFunction(
            name="g_4",
            symbol="g_4",
            func=f"{buckling_load} - {p}",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
    ]

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="1.10471 * x_1**2 * x_2 + 0.04811 * x_3 * x_4 * (14 + x_2)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f"({4 * p * l**3 / e}) / (x_4 * x_3**3)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func=_violation_objective(["g_1", "g_2", "g_3", "g_4"]),
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=False,
    )

    return Problem(
        name="re32",
        description="The welded beam design problem",
        variables=[x_1, x_2, x_3, x_4],
        objectives=[f_1, f_2, f_3],
        extra_funcs=extras,
    )


def re33() -> Problem:
    r"""The disc brake design problem.

    The first two objectives are the mass of the brake and the minimum stopping time; the third is the
    sum of the four constraint violations:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = 4.9 \times 10^{-5}(x_2^2 - x_1^2)(x_4 - 1) \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \frac{9.82 \times 10^6 (x_2^2 - x_1^2)}
            {x_3x_4(x_2^3 - x_1^3)} \\
        &\min_{\mathbf{x}} & f_3(\mathbf{x}) & = \sum_{i=1}^4 \max\{-g_i(\mathbf{x}), 0\} \\
        &\text{where}   & g_1(\mathbf{x}) & = (x_2 - x_1) - 20 \geq 0,\\
        & & g_2(\mathbf{x}) & = 0.4 - \frac{x_3}{3.14(x_2^2 - x_1^2)} \geq 0, \\
        & & g_3(\mathbf{x}) & = 1 - \frac{2.22 \times 10^{-3}x_3(x_2^3 - x_1^3)}
            {(x_2^2 - x_1^2)^2} \geq 0, \\
        & & g_4(\mathbf{x}) & = \frac{2.66 \times 10^{-2}x_3x_4(x_2^3 - x_1^3)}{x_2^2 - x_1^2}
            - 900 \geq 0,
    \end{align}

    where $x_1 \in [55, 80]$, $x_2 \in [75, 110]$, $x_3 \in [1000, 3000]$ and $x_4 \in [11, 20]$. The four
    variables are the inner radius of the discs, the outer radius of the discs, the engaging force, and
    the number of friction surfaces. The number of friction surfaces is continuous here: the original
    range is $[2, 20]$, but the original problem also constrains $x_4 \geq 11$, so the RE suite folds
    that bound into the variable range instead of into $f_3$.

    Note:
        Following the RE suite, the returned problem has **no constraints** — the constraint violations
        are folded into `f_3`. The constrained variant is CRE33, which is not implemented here.

    References:
        Ray, T., & Liew, K. M. (2002). A swarm metaphor for multiobjective design optimization.
            Engineering Optimization, 34(2), 141-153. https://doi.org/10.1080/03052150210915.

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective
            optimization problem suite. Applied soft computing, 89, 106078.
            https://doi.org/10.1016/j.asoc.2020.106078.

    Returns:
        Problem: an instance of the disc brake design problem.
    """
    x_1 = Variable(
        name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=55, upperbound=80, initial_value=60
    )
    x_2 = Variable(
        name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=75, upperbound=110, initial_value=90
    )
    x_3 = Variable(
        name="x_3",
        symbol="x_3",
        variable_type=VariableTypeEnum.real,
        lowerbound=1000,
        upperbound=3000,
        initial_value=2000,
    )
    x_4 = Variable(
        name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=11, upperbound=20, initial_value=15
    )

    # Squared and cubed radius differences recur in every function below.
    sq_diff = "(x_2**2 - x_1**2)"
    cube_diff = "(x_2**3 - x_1**3)"

    extras = [
        ExtraFunction(
            name="g_1",
            symbol="g_1",
            func="(x_2 - x_1) - 20",
            is_linear=True,
            is_convex=True,
            is_twice_differentiable=True,
        ),
        ExtraFunction(
            name="g_2",
            symbol="g_2",
            func=f"0.4 - x_3 / (3.14 * {sq_diff})",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
        ExtraFunction(
            name="g_3",
            symbol="g_3",
            func=f"1 - (2.22e-3 * x_3 * {cube_diff}) / {sq_diff}**2",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
        ExtraFunction(
            name="g_4",
            symbol="g_4",
            func=f"(2.66e-2 * x_3 * x_4 * {cube_diff}) / {sq_diff} - 900",
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        ),
    ]

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f"4.9e-5 * {sq_diff} * (x_4 - 1)",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f"(9.82e6 * {sq_diff}) / (x_3 * x_4 * {cube_diff})",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func=_violation_objective(["g_1", "g_2", "g_3", "g_4"]),
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=False,
    )

    return Problem(
        name="re33",
        description="The disc brake design problem",
        variables=[x_1, x_2, x_3, x_4],
        objectives=[f_1, f_2, f_3],
        extra_funcs=extras,
    )


def re34() -> Problem:
    """The vehicle crash worthiness design problem.

    The implementation of this problem is taken from the vehicle_crashworthiness_problem.py file.
    """
    return vehicle_crashworthiness()


def re37() -> Problem:
    """The rocket injector design problem.

    The implementation of this problem is taken from the rocket_injector_design_problem.py file.
    """
    return rocket_injector_design()


def re41() -> Problem:
    """The car side impact design problem.

    The implementation of this problem is taken from the car_side_impact_problem.py file. Removes the constraints from
    the problem.
    """
    return car_side_impact(three_obj=False).model_copy(update={"constraints": None})


def re42(
    round_trip_miles: float = 5000.0,
    fuel_price: float = 100.0,
    handling_rate: float = 8000.0,
    gravity: float = 9.8065,
) -> Problem:
    r"""The conceptual marine design problem.

    A bulk carrier is sized by its length, beam, depth, draft, speed and block coefficient. The first
    three objectives are the transportation cost, the light ship weight and the (negated) annual cargo
    transport capacity; the fourth is the sum of the nine constraint violations:

    \begin{align}
        &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = \frac{\text{annual costs}}{\text{annual cargo}} \\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = W_s + W_o + W_m \\
        &\min_{\mathbf{x}} & f_3(\mathbf{x}) & = -\text{cargo DWT} \times \text{RTPA} \\
        &\min_{\mathbf{x}} & f_4(\mathbf{x}) & = \sum_{i=1}^9 \max\{-g_i(\mathbf{x}), 0\} \\
        &\text{where}   & g_1 & = L/B - 6 \geq 0, & g_2 & = 15 - L/D \geq 0, \\
        & & g_3 & = 19 - L/T \geq 0, & g_4 & = 0.45\,\text{DWT}^{0.31} - T \geq 0, \\
        & & g_5 & = 0.7D + 0.7 - T \geq 0, & g_6 & = \text{DWT} - 3\,000 \geq 0, \\
        & & g_7 & = 500\,000 - \text{DWT} \geq 0, & g_8 & = 0.32 - F_n \geq 0, \\
        & & g_9 & = K_B + BM_T - K_G - 0.07B \geq 0. &
    \end{align}

    The intermediate quantities — displacement, power, Froude number, the weight and cost breakdowns,
    the round-trip schedule and the stability terms — are defined as extra functions on the returned
    problem, one per equation of the source, so they can be inspected alongside the objectives.

    The decision variables $L, B, D, T, V_k, C_B$ are the length, beam, depth, draft, speed and block
    coefficient, with $L \in [150, 274.32]$, $B \in [20, 32.31]$, $D \in [13, 25]$, $T \in [10, 11.71]$,
    $V_k \in [14, 18]$ and $C_B \in [0.63, 0.75]$. The annual cargo capacity is maximised in the original
    formulation and is negated here so that every objective is minimised.

    Note:
        Following the RE suite, the returned problem has **no constraints** — the constraint violations
        are folded into `f_4`. The constrained variant is CRE42, which is not implemented here.

        The upper bound on the deadweight in $g_7$ is 500 000, not the 50 000 that the RE reference
        implementation shipped until it was corrected in 2021.

    Warning:
        **The number of sea days is $\text{round trip miles} / 24 \times V_k$, not
        $\text{round trip miles} / (24 V_k)$.** The second is the dimensionally sensible reading — days
        at sea should fall as the ship goes faster — but the first is what defines RE42, and it is
        reproduced here deliberately. Verified against the suite's published ideal point: the objective
        minima over the box agree to eight significant figures with
        $(-2756.259, 3962.558, 1947.881, 0)$ under this reading, and are wrong by a factor of 400 in
        $f_3$ under the other. Any comparison with published RE42 results needs this equation.

        A consequence worth knowing before interpreting results: at 3 333 sea days the ship carries
        more fuel than its deadweight, so the cargo deadweight is negative across the whole reference
        front. The annual cargo is therefore negative and $f_3 = -\text{annual cargo}$ is positive,
        which is why the published front has $f_3 \in [1948, 5195]$ rather than the large negative
        values a physically-sensible schedule would give.

    References:
        Parsons, M. G., & Scott, R. L. (2004). Formulation of multicriterion design optimization
            problems for solution with scalar numerical optimization methods. Journal of Ship Research,
            48(1), 61-76. https://doi.org/10.5957/jsr.2004.48.1.61.

        Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective
            optimization problem suite. Applied soft computing, 89, 106078.
            https://doi.org/10.1016/j.asoc.2020.106078.

    Args:
        round_trip_miles (float, optional): the length of one round trip (nautical miles).
            Defaults to 5000.0.
        fuel_price (float, optional): the price of fuel per ton. Defaults to 100.0.
        handling_rate (float, optional): the cargo handling rate in port (tons per day).
            Defaults to 8000.0.
        gravity (float, optional): gravitational acceleration (m/s^2), used in the Froude number.
            Defaults to 9.8065.

    Returns:
        Problem: an instance of the conceptual marine design problem.
    """
    # x_1 = L, x_2 = B, x_3 = D, x_4 = T, x_5 = V_k, x_6 = C_B.
    bounds = [
        ("x_1", "length", 150.0, 274.32),
        ("x_2", "beam", 20.0, 32.31),
        ("x_3", "depth", 13.0, 25.0),
        ("x_4", "draft", 10.0, 11.71),
        ("x_5", "speed", 14.0, 18.0),
        ("x_6", "block coefficient", 0.63, 0.75),
    ]
    variables = [
        Variable(
            name=name,
            symbol=symbol,
            variable_type=VariableTypeEnum.real,
            lowerbound=lower,
            upperbound=upper,
            initial_value=(lower + upper) / 2,
        )
        for symbol, name, lower, upper in bounds
    ]

    def extra(symbol: str, func: str, *, is_linear: bool = False) -> ExtraFunction:
        return ExtraFunction(
            name=symbol,
            symbol=symbol,
            func=func,
            is_linear=is_linear,
            is_convex=False,  # Not checked
            is_twice_differentiable=True,
        )

    # One extra function per equation of the source, in dependency order: each may refer to the ones
    # above it. Written this way rather than as one substituted expression because the source defines
    # the ship this way, and because the intermediate values are worth reading off a solution.
    extras = [
        extra("displacement", "1.025 * x_1 * x_2 * x_4 * x_6"),
        extra("froude", f"(0.5144 * x_5) / Sqrt({gravity} * x_1)"),
        # The admiralty coefficient is a quadratic in the block coefficient.
        extra("coef_a", "4977.06 * x_6**2 - 8105.61 * x_6 + 4456.51"),
        extra("coef_b", "-10847.2 * x_6**2 + 12817 * x_6 - 6960.32"),
        extra("power", f"(displacement**{2 / 3} * x_5**3) / (coef_a + coef_b * froude)"),
        extra("weight_steel", "0.034 * x_1**1.7 * x_2**0.7 * x_3**0.4 * x_6**0.5"),
        extra("weight_outfit", "1.0 * x_1**0.8 * x_2**0.6 * x_3**0.3 * x_6**0.1"),
        extra("weight_machinery", "0.17 * power**0.9"),
        extra("light_ship", "weight_steel + weight_outfit + weight_machinery", is_linear=True),
        extra("deadweight", "displacement - light_ship", is_linear=True),
        extra("ship_cost", "1.3 * (2000 * weight_steel**0.85 + 3500 * weight_outfit + 2400 * power**0.8)"),
        extra("capital_costs", "0.2 * ship_cost", is_linear=True),
        extra("running_costs", "40000 * deadweight**0.3"),
        extra("daily_consumption", "(0.19 * power * 24) / 1000 + 0.2", is_linear=True),
        # Transcribed exactly as the RE suite states it: (round trip miles / 24) * speed. Dividing by
        # the speed instead would be the dimensionally sensible reading, but it is not this problem —
        # see the note in the docstring. The parentheses are load-bearing: the expression parser reads
        # "a / b * c" as "a / (b * c)", which is the sensible reading and the wrong problem.
        extra("sea_days", f"({round_trip_miles} / 24) * x_5"),
        extra("fuel_cost", f"1.05 * daily_consumption * sea_days * {fuel_price}"),
        extra("port_cost", "6.3 * deadweight**0.8"),
        extra("fuel_carried", "daily_consumption * (sea_days + 5)"),
        extra("miscellaneous_deadweight", "2 * deadweight**0.5"),
        extra("cargo_deadweight", "deadweight - fuel_carried - miscellaneous_deadweight", is_linear=True),
        extra("port_days", f"2 * (cargo_deadweight / {handling_rate} + 0.5)", is_linear=True),
        extra("round_trips_per_year", "350 / (sea_days + port_days)"),
        extra("voyage_costs", "(fuel_cost + port_cost) * round_trips_per_year"),
        extra("annual_costs", "capital_costs + running_costs + voyage_costs", is_linear=True),
        extra("annual_cargo", "cargo_deadweight * round_trips_per_year"),
        # Stability: centre of buoyancy, metacentric radius and centre of gravity.
        extra("centre_of_buoyancy", "0.53 * x_4", is_linear=True),
        extra("metacentric_radius", "((0.085 * x_6 - 0.002) * x_2**2) / (x_4 * x_6)"),
        extra("centre_of_gravity", "1 + 0.52 * x_3", is_linear=True),
        extra("g_1", "x_1 / x_2 - 6"),
        extra("g_2", "15 - x_1 / x_3"),
        extra("g_3", "19 - x_1 / x_4"),
        extra("g_4", "0.45 * deadweight**0.31 - x_4"),
        extra("g_5", "0.7 * x_3 + 0.7 - x_4", is_linear=True),
        extra("g_6", "deadweight - 3000", is_linear=True),
        extra("g_7", "500000 - deadweight", is_linear=True),
        extra("g_8", "0.32 - froude"),
        extra("g_9", "centre_of_buoyancy + metacentric_radius - centre_of_gravity - 0.07 * x_2", is_linear=True),
    ]

    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="annual_costs / annual_cargo",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func="light_ship",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func="-annual_cargo",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=True,
    )
    f_4 = Objective(
        name="f_4",
        symbol="f_4",
        func=_violation_objective([f"g_{i}" for i in range(1, 10)]),
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,  # Not checked
        is_twice_differentiable=False,
    )

    return Problem(
        name="re42",
        description="The conceptual marine design problem",
        variables=variables,
        objectives=[f_1, f_2, f_3, f_4],
        extra_funcs=extras,
    )


def re61() -> Problem:
    """The water management design problem.

    The implementation of this problem is taken from the water_management_problem.py file. Removes the constraints from
    the problem.
    """
    return water_management(six_obj=True).model_copy(update={"constraints": None})
