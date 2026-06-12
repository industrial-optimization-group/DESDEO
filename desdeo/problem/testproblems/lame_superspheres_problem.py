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

    where the angular terms are

    \begin{equation}
    \tilde{p}_1 =
    \prod_{j=1}^{M-1}
    \cos\left(x_j \frac{\pi}{2}\right)^{2/\gamma},
    \end{equation}

    and for $i > 1$

    \begin{equation}
    \tilde{p}_i =
    \left(
    \prod_{j=1}^{M-i}
    \cos\left(x_j \frac{\pi}{2}\right)
    \right)^{2/\gamma}
    \sin\left(
    x_{M-i+1}
    \frac{\pi}{2}
    \right)^{2/\gamma}.
    \end{equation}

    The distance function is

    \begin{equation}
    g(\mathbf{x}_M)
    =
    \sum_{x_i \in \mathbf{x}_M}
    \left(x_i - 0.5\right)^2.
    \end{equation}

    The parameter $\gamma$ controls the curvature of the Pareto front:

    - $\gamma = 2$ gives a spherical front.
    - $\gamma < 2$ gives a more convex front.
    - $\gamma > 2$ gives a more concave front.

    Args:
        n_variables: Number of variables.
        n_objectives: Number of objectives.
        gamma: Lamé exponent controlling front curvature.

    Returns:
        Problem: A Lamé superspheres test problem.

    References:
        Emmerich, M. T. M., & Deutz, A. H. (2007).
        Test Problems Based on Lamé Superspheres.
        EMO 2007, LNCS 4403, 922–936.
    """

    g_symbol = "g"
    g_expr = " + ".join(
        [f"(x_{i} - 0.5)**2" for i in range(n_objectives, n_variables + 1)]
    )

    objectives = []

    for m in range(1, n_objectives + 1):
        prod_expr = " * ".join(
            [
                f"Cos(0.5 * {np.pi} * x_{i})**({2 / gamma})"
                for i in range(1, n_objectives - m + 1)
            ]
        )

        if m > 1:
            prod_expr += (
                f"{' * ' if prod_expr != '' else ''}"
                f"Sin(0.5 * {np.pi} * x_{n_objectives - m + 1})**({2 / gamma})"
            )

        if prod_expr == "":
            prod_expr = "1"

        f_m_expr = f"(1 + {g_symbol}) * ({prod_expr})"

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