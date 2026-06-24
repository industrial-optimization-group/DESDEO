"""Contains Lamé superspheres test problems."""

import numpy as np

from desdeo.problem.schema import (
    ExtraFunction,
    Objective,
    Problem,
    Variable,
    VariableTypeEnum,
)


def lame_superspheres(
    n_variables: int,
    n_objectives: int,
    gamma: float = 2.0,
) -> Problem:
    r"""Defines the Lamé superspheres test problem.

    The objective functions for the Lamé superspheres problem are defined
    as follows, for $i = 1$ to $M$:

    \begin{equation}
    f_i(\mathbf{x})
    =
    (1 + g(\mathbf{x}_M))
    \tilde{p}_i(\mathbf{x}),
    \end{equation}

    where the hypersphere parametrization follows Eq. (10)

    \begin{equation}
    p_1 = \cos(\theta_1),
    \end{equation}

    \begin{equation}
    p_2 = \sin(\theta_1)\cos(\theta_2),
    \end{equation}

    \begin{equation}
    p_3 = \sin(\theta_1)\sin(\theta_2)\cos(\theta_3),
    \end{equation}

    \begin{equation}
    \vdots
    \end{equation}

    \begin{equation}
    p_M =
    \prod_{j=1}^{M-1}
    \sin(\theta_j).
    \end{equation}

    The Lamé supersphere coordinates are then obtained as

    \begin{equation}
    \tilde{p}_i = p_i^{2/\gamma}.
    \end{equation}

    The distance function is

    \begin{equation}
    g(\mathbf{x}_M)
    =
    \sqrt{
    \sum_{x_i \in \mathbf{x}_M}
    x_i^2
    }.
    \end{equation}

    The parameter $\gamma$ controls the curvature of the Pareto front:

    - $\gamma < 1$ gives a convex Pareto front.
    - $\gamma = 1$ gives a linear Pareto front.
    - $\gamma = 2$ gives a spherical (concave) Pareto front.
    - $\gamma > 2$ gives a more boxy, strongly concave Pareto front.

    Args:
        n_variables: Number of variables.
        n_objectives: Number of objectives.
        gamma: Lamé exponent controlling front curvature.

    Returns:
        Problem: A Lamé superspheres test problem.

    References:
        Emmerich, M. T. M., & Deutz, A. H. (2007).  Test Problems Based on Lamé
        Superspheres.  EMO 2007, LNCS 4403, 922-936.
    """
    if n_objectives < 2:  # noqa: PLR2004
        raise ValueError(f"n_objectives must be at least 2, got {n_objectives}.")

    if n_variables < n_objectives:
        raise ValueError(
            "n_variables must be greater than or equal to n_objectives "
            f"(need at least {n_objectives} variables), got {n_variables}."
        )

    g_symbol = "g"

    sum_expr = " + ".join([f"(x_{i})**2" for i in range(n_objectives, n_variables + 1)])

    g_expr = f"Sqrt({sum_expr})"
    objectives = []

    for m in range(1, n_objectives + 1):
        if m == 1:
            angular_expr = f"Cos(0.5 * {np.pi} * x_1)"

        elif m < n_objectives:
            factors = [f"Sin(0.5 * {np.pi} * x_{i})" for i in range(1, m)]

            factors.append(f"Cos(0.5 * {np.pi} * x_{m})")

            angular_expr = " * ".join(factors)

        else:
            angular_expr = " * ".join([f"Sin(0.5 * {np.pi} * x_{i})" for i in range(1, n_objectives)])

        f_m_expr = f"(1 + {g_symbol}) * (({angular_expr})**({2 / gamma}))"

        objectives.append(
            Objective(
                name=f"f_{m}",
                symbol=f"f_{m}",
                func=f_m_expr,
                maximize=False,
                ideal=0,
                nadir=1,
                is_convex=False,
                is_linear=False,
                is_twice_differentiable=True,
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
        ExtraFunction(
            name="g",
            symbol=g_symbol,
            func=g_expr,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
    ]

    return Problem(
        name="lame_superspheres",
        description="Lamé superspheres test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
    )
