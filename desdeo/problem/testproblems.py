"""Pre-defined multiobjective optimization problems.

Pre-defined problems for, e.g.,
testing and illustration purposed are defined here.
"""

import numpy as np

from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


def binh_and_korn(maximize: tuple[bool] = (False, False)) -> Problem:
    """Create a pydantic dataclass representation of the Binh and Korn problem.

    The function has two objective functions, two variables, and two constraint functions.
    For testing purposes, it can be chosen whether the firs and second objective should
    be maximized instead.

    Arguments:
        maximize (tuple[bool]): whether the first or second objective should be
            maximized or not. Defaults to (False, False).

    References:
        Binh T. and Korn U. (1997) MOBES: A Multiobjective Evolution Strategy for Constrained Optimization Problems.
            In: Proceedings of the Third International Conference on Genetic Algorithms. Czech Republic. pp. 176-182.
    """
    # These constants are for demonstrative purposes.
    constant_1 = Constant(name="Four", symbol="c_1", value=4)
    constant_2 = Constant(name="Five", symbol="c_2", value=5)

    variable_1 = Variable(
        name="The first variable", symbol="x_1", variable_type="real", lowerbound=0, upperbound=5, initial_value=2.5
    )
    variable_2 = Variable(
        name="The second variable", symbol="x_2", variable_type="real", lowerbound=0, upperbound=3, initial_value=1.5
    )

    objective_1 = Objective(
        name="Objective 1",
        symbol="f_1",
        func=f"{'-' if maximize[0] else ''}(c_1 * x_1**2 + c_1*x_2**2)",
        # func=["Add", ["Multiply", "c_1", ["Square", "x_1"]], ["Multiply", "c_1", ["Square", "x_2"]]],
        maximize=maximize[0],
        ideal=0,
        nadir=140 if not maximize[0] else -140,
    )
    objective_2 = Objective(
        name="Objective 2",
        symbol="f_2",
        # func=["Add", ["Square", ["Subtract", "x_1", "c_2"]], ["Square", ["Subtract", "x_2", "c_2"]]],
        func=f"{'-' if maximize[1] else ''}((x_1 - c_2)**2 + (x_2 - c_2)**2)",
        maximize=maximize[1],
        ideal=0,
        nadir=50 if not maximize[0] else -50,
    )

    constraint_1 = Constraint(
        name="Constraint 1",
        symbol="g_1",
        cons_type="<=",
        func=["Add", ["Square", ["Subtract", "x_1", "c_2"]], ["Square", "x_2"], -25],
    )

    constraint_2 = Constraint(
        name="Constraint 2",
        symbol="g_2",
        cons_type="<=",
        func=["Add", ["Negate", ["Square", ["Subtract", "x_1", 8]]], ["Negate", ["Square", ["Add", "x_2", 3]]], 7.7],
    )

    return Problem(
        name="The Binh and Korn function",
        description="The two-objective problem used in the paper by Binh and Korn.",
        constants=[constant_1, constant_2],
        variables=[variable_1, variable_2],
        objectives=[objective_1, objective_2],
        constraints=[constraint_1, constraint_2],
    )


def river_pollution_problem(five_objective_variant: bool = True) -> Problem:
    """Create a pydantic dataclass representation of the river pollution problem with either five or four variables.

    The objective functions "DO city", "DO municipality", and
    "BOD deviation" are to be minimized, while "ROI fishery" and "ROI city" are to be
    maximized. If the four variant problem is used, the the "BOD deviation" objective
    function is not present.

    Args:
        five_objective_variant (bool, optional): Whether to use to five
            objective function variant of the problem or not. Defaults to True.

    Returns:
        Problem: the river pollution problem.

    References:
        Narula, Subhash C., and HRoland Weistroffer. "A flexible method for
            nonlinear multicriteria decision-making problems." IEEE Transactions on
            Systems, Man, and Cybernetics 19.4 (1989): 883-887.

        Miettinen, Kaisa, and Marko M. Mäkelä. "Interactive method NIMBUS for
            nondifferentiable multiobjective optimization problems." Multicriteria
            Analysis: Proceedings of the XIth International Conference on MCDM, 1–6
            August 1994, Coimbra, Portugal. Berlin, Heidelberg: Springer Berlin
            Heidelberg, 1997.
    """
    variable_1 = Variable(
        name="BOD", symbol="x_1", variable_type="real", lowerbound=0.3, upperbound=1.0, initial_value=0.65
    )
    variable_2 = Variable(
        name="DO", symbol="x_2", variable_type="real", lowerbound=0.3, upperbound=1.0, initial_value=0.65
    )

    f_1 = "-4.07 - 2.27 * x_1"
    f_2 = "-2.60 - 0.03 * x_1 - 0.02 * x_2 - 0.01 / (1.39 - x_1**2) - 0.30 / (1.39 - x_2**2)"
    f_3 = "8.21 - 0.71 / (1.09 - x_1**2)"
    f_4 = "0.96 - 0.96 / (1.09 - x_2**2)"
    f_5 = "Max(Abs(x_1 - 0.65), Abs(x_2 - 0.65))"

    objective_1 = Objective(name="DO city", symbol="f_1", func=f_1, maximize=False, ideal=-6.34, nadir=-4.75)
    objective_2 = Objective(name="DO municipality", symbol="f_2", func=f_2, maximize=False, ideal=-3.44, nadir=-2.85)
    objective_3 = Objective(name="ROI fishery", symbol="f_3", func=f_3, maximize=True, ideal=7.5, nadir=0.32)
    objective_4 = Objective(name="ROI city", symbol="f_4", func=f_4, maximize=True, ideal=0, nadir=-9.70)
    objective_5 = Objective(name="BOD deviation", symbol="f_5", func=f_5, maximize=False, ideal=0, nadir=0.35)

    objectives = (
        [objective_1, objective_2, objective_3, objective_4, objective_5]
        if five_objective_variant
        else [objective_1, objective_2, objective_3, objective_4]
    )

    return Problem(
        name="The river pollution problem",
        description="The river pollution problem to maximize return of investments and minimize pollution.",
        variables=[variable_1, variable_2],
        objectives=objectives,
    )


def simple_test_problem() -> Problem:
    """Defines a simple problem suitable for testing purposes."""
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type="real", lowerbound=0, upperbound=10, initial_value=5),
        Variable(name="x_2", symbol="x_2", variable_type="real", lowerbound=0, upperbound=10, initial_value=5),
    ]

    constants = [Constant(name="c", symbol="c", value=4.2)]

    f_1 = "x_1 + x_2"
    f_2 = "x_2**3"
    f_3 = "x_1 + x_2"
    f_4 = "Max(Abs(x_1 - x_2), c)"  # c = 4.2
    f_5 = "(-x_1) * (-x_2)"

    objectives = [
        Objective(name="f_1", symbol="f_1", func=f_1, maximize=False),  # min!
        Objective(name="f_2", symbol="f_2", func=f_2, maximize=True),  # max!
        Objective(name="f_3", symbol="f_3", func=f_3, maximize=True),  # max!
        Objective(name="f_4", symbol="f_4", func=f_4, maximize=False),  # min!
        Objective(name="f_5", symbol="f_5", func=f_5, maximize=True),  # max!
    ]

    return Problem(
        name="Simple test problem.",
        description="A simple problem for testing purposes.",
        constants=constants,
        variables=variables,
        objectives=objectives,
    )


def zdt1(number_of_variables: int) -> Problem:
    """Defines the ZDT1 test problem."""
    n = number_of_variables

    # function f_1
    f1_symbol = "f_1"
    f1_expr = "1 * x_1"

    # function g
    g_symbol = "g"
    g_expr_1 = f"1 + (9 / ({n} - 1))"
    g_expr_2 = "(" + " + ".join([f"x_{i}" for i in range(2, n + 1)]) + ")"
    g_expr = g_expr_1 + " * " + g_expr_2

    # function h(f, g)
    h_symbol = "h"
    h_expr = f"1 - Sqrt(({f1_expr}) / ({g_expr}))"

    # function f_2
    f2_symbol = "f_2"
    f2_expr = f"{g_symbol} * {h_symbol}"

    variables = [
        Variable(name=f"x_{i}", symbol=f"x_{i}", variable_type="real", lowerbound=0, upperbound=1, initial_value=0.5)
        for i in range(1, n + 1)
    ]

    objectives = [
        Objective(name="f_1", symbol=f1_symbol, func=f1_expr, maximize=False, ideal=0, nadir=1),
        Objective(name="f_2", symbol=f2_symbol, func=f2_expr, maximize=False, ideal=0, nadir=1),
    ]

    extras = [
        ExtraFunction(name="g", symbol=g_symbol, func=g_expr),
        ExtraFunction(name="h", symbol=h_symbol, func=h_expr),
    ]

    return Problem(
        name="zdt1",
        description="The ZDT1 test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
    )


def simple_data_problem() -> Problem:
    """Defines a simple problem with only data-based objective functions."""
    constants = [Constant(name="c", symbol="c", value=1000)]

    n_var = 5
    variables = [
        Variable(
            name=f"y_{i}",
            symbol=f"y_{i}",
            variable_type=VariableTypeEnum.real,
            lowerbound=-50.0,
            upperbound=50.0,
            initial_value=0.1,
        )
        for i in range(1, n_var + 1)
    ]

    n_objectives = 3
    # only the first objective is to be maximized, the rest are to be minimized
    objectives = [
        Objective(
            name=f"g_{i}",
            symbol=f"g_{i}",
            func=None,
            objective_type=ObjectiveTypeEnum.data_based,
            maximize=i == 1,
            ideal=3000 if i == 1 else -60.0 if i == 3 else 0,
            nadir=0 if i == 1 else 15 - 2.0 if i == 3 else 15,
        )
        for i in range(1, n_objectives + 1)
    ]

    constraints = [Constraint(name="cons 1", symbol="c_1", cons_type=ConstraintTypeEnum.EQ, func="y_1 + y_2 - c")]

    data_len = 10
    var_data = {f"y_{i}": [i * 0.5 + j for j in range(data_len)] for i in range(1, n_var + 1)}
    obj_data = {
        "g_1": [sum(var_data[f"y_{j}"][i] for j in range(1, n_var + 1)) ** 2 for i in range(data_len)],
        "g_2": [max(var_data[f"y_{j}"][i] for j in range(1, n_var + 1)) for i in range(data_len)],
        "g_3": [-sum(var_data[f"y_{j}"][i] for j in range(1, n_var + 1)) for i in range(data_len)],
    }

    discrete_def = DiscreteRepresentation(variable_values=var_data, objective_values=obj_data)

    return Problem(
        name="Simple data problem",
        description="Simple problem with all objectives being data-based. Has constraints and a constant also.",
        constants=constants,
        variables=variables,
        objectives=objectives,
        constraints=constraints,
        discrete_representation=discrete_def,
    )


def momip_ti2() -> Problem:
    """Defines the mixed-integer multiobjective optimization problem test instance 2 (TI2).

    The problem has four variables, two continuous and two integer. The Pareto optimal solutions
    hold for solutions with x_1^2 + x_^2 = 0.25 and (x_3, x_4) = {(0, -1), (-1, 0)}.

    References:
        Eichfelder, G., Gerlach, T., & Warnow, L. (n.d.). Test Instances for
            Multiobjective Mixed-Integer Nonlinear Optimization.
    """
    x_1 = Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real)
    x_2 = Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real)
    x_3 = Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.integer)
    x_4 = Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.integer)

    f_1 = Objective(
        name="f_1", symbol="f_1", func="x_1 + x_3", objective_type=ObjectiveTypeEnum.analytical, maximize=False
    )
    f_2 = Objective(
        name="f_2", symbol="f_2", func="x_2 + x_4", objective_type=ObjectiveTypeEnum.analytical, maximize=False
    )

    con_1 = Constraint(name="g_1", symbol="g_1", cons_type=ConstraintTypeEnum.LTE, func="x_1**2 + x_2**2 - 0.25")
    con_2 = Constraint(name="g_2", symbol="g_2", cons_type=ConstraintTypeEnum.LTE, func="x_3**2 + x_4**2 - 1")

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
    )
    f_2 = Objective(
        name="f_2",
        symbol="f_2",
        func="-(x_2 + x_5)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=3,
        nadir=-3,
        maximize=True,
    )
    f_3 = Objective(
        name="f_3",
        symbol="f_3",
        func="x_3 + x_6",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=-3,
        nadir=3,
        maximize=False,
    )

    con_1 = Constraint(name="g_1", symbol="g_1", cons_type=ConstraintTypeEnum.LTE, func="x_1**2 + x_2**2 + x_3**2 - 1")
    con_2 = Constraint(name="g_2", symbol="g_2", cons_type=ConstraintTypeEnum.LTE, func="x_4**2 + x_5**2 + x_6**2 - 1")

    return Problem(
        name="MOMIP Test Instance 7",
        description="Test instance 17",
        variables=[x_1, x_2, x_3, x_4, x_5, x_6],
        constraints=[con_1, con_2],
        objectives=[f_1, f_2, f_3],
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

def simple_linear_test_problem() -> Problem:
    """Defines a simple single objective linear problem suitable for testing purposes."""
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type="real", lowerbound=-10, upperbound=10, initial_value=5),
        Variable(name="x_2", symbol="x_2", variable_type="real", lowerbound=-10, upperbound=10, initial_value=5),
    ]

    constants = [Constant(name="c", symbol="c", value=4.2)]

    f_1 = "x_1 + x_2"

    objectives = [
        Objective(name="f_1", symbol="f_1", func=f_1, maximize=False),  # min!
    ]

    con_1 = Constraint(name="g_1", symbol="g_1", cons_type=ConstraintTypeEnum.LTE, func="c - x_1")
    con_2 = Constraint(name="g_2", symbol="g_2", cons_type=ConstraintTypeEnum.LTE, func="0.5*x_1 - x_2")

    return Problem(
        name="Simple linear test problem.",
        description="A simple problem for testing purposes.",
        constants=constants,
        variables=variables,
        constraints=[con_1, con_2],
        objectives=objectives,
    )


def dtlz2(n_variables: int, n_objectives: int) -> Problem:
    r"""Defines the DTLZ2 test problem.

    The objective functions for DTLZ2 are defined as follows, for $i = 1$ to $M$:

    \begin{equation}
        \underset{\mathbf{x}}{\operatorname{min}}
        f_i(\mathbf{x}) = (1+g(\mathbf{x}_M)) \prod_{j=1}^{M-i} \cos\left(x_j \frac{\pi}{2}\right) \times
        \begin{cases}
        1 & \text{if } i=1 \\
        \sin\left(x_{(M-i+1)}\frac{\pi}{2}\right) & \text{otherwise},
        \end{cases}
    \end{equation}

    where

    \begin{equation}
    g(\mathbf{x}_M) = \sum_{x_i \in \mathbf{x}_M} \left( x_i - 0.5 \right)^2,
    \end{equation}

    and $\mathbf{x}_M$ represents the last $n-k$ dimensions of the decision vector.
    Pareto optimal solutions to the DTLZ2 problem consist of $x_i = 0.5$ for
    all $x_i \in\mathbf{x}_{M}$, and $\sum{i=1}^{M} f_i^2 = 1$.

    Args:
        n_variables (int): number of variables.
        n_objectives (int): number of objective functions.

    Returns:
        Problem: an instance of the DTLZ2 problem with `n_variables` variables and `n_objectives` objective
            functions.

    References:
        Deb, K., Thiele, L., Laumanns, M., Zitzler, E. (2005). Scalable Test
            Problems for Evolutionary Multiobjective Optimization. In: Abraham, A.,
            Jain, L., Goldberg, R. (eds) Evolutionary Multiobjective Optimization.
            Advanced Information and Knowledge Processing. Springer.
    """
    # function g
    g_symbol = "g"
    g_expr = " + ".join([f"(x_{i} - 0.5)**2" for i in range(n_objectives, n_variables + 1)])
    g_expr = "1 + " + g_expr

    objectives = []
    for m in range(1, n_objectives + 1):
        # function f_m
        prod_expr = " * ".join([f"Cos(0.5 * {np.pi} * x_{i})" for i in range(1, n_objectives - m + 1)])
        if m > 1:
            prod_expr += f"{' * ' if prod_expr != "" else ""}Sin(0.5 * {np.pi} * x_{n_objectives - m + 1})"
        if prod_expr == "":
            prod_expr = "1"  # When m == n_objectives, the product is empty, implying f_M = g.
        f_m_expr = f"({g_symbol}) * ({prod_expr})"

        objectives.append(
            Objective(
                name=f"f_{m}",
                symbol=f"f_{m}",
                func=f_m_expr,
                maximize=False,
                ideal=0,
                nadir=2,  # Assuming the range of g and the trigonometric functions
            )
        )

    variables = [
        Variable(
            name=f"x_{i}",
            symbol=f"x_{i}",
            variable_type=VariableTypeEnum.real,
            lowerbound=0,
            upperbound=1,
            initial_value=1.0,
        )
        for i in range(1, n_variables + 1)
    ]

    extras = [
        ExtraFunction(name="g", symbol=g_symbol, func=g_expr),
    ]

    return Problem(
        name="dtlz2",
        description="The DTLZ2 test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
    )


if __name__ == "__main__":
    problem = dtlz2(10, 3)
    print(problem.model_dump_json(indent=2))
