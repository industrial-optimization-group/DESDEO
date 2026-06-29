"""Contains CTP problems."""

import math

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


def _ctp_g_expr(n_variables: int) -> str:
    """Builds the ZDT-style g function string shared by all CTP problems.

    The original chapter leaves g(x) unspecified (it used Rastrigin's function in its
    experiments). For consistency across the DESDEO CTP suite we use the same linear g as
    in :func:`ctp1`, namely g(x) = 1 + (9 / (n - 1)) * sum_{i=2}^{n} x_i, whose minimum is 1.
    """
    g_sum = " + ".join([f"x_{i}" for i in range(2, n_variables + 1)])
    return f"(1 + (9 / ({n_variables} - 1)) * ({g_sum}))"


def _ctp_constraint_func(f2_expr: str, theta: float, a: float, b: float, c: float, d: float, e: float) -> str:
    r"""Builds the constraint string for the generic CTP2-CTP8 constraint (eq. 5 of the chapter).

    The chapter writes the constraint in the >= 0 form

    .. math::
        c(x) = \cos(\theta)(f_2 - e) - \sin(\theta) f_1
               - a\,\left|\sin\!\big(b\pi(\sin(\theta)(f_2 - e) + \cos(\theta) f_1)^c\big)\right|^d \ge 0,

    with f_1 = x_1. DESDEO constraints use the <= 0 convention, so the returned string is the
    negation of the left-hand side above, i.e. it is <= 0 exactly when the chapter constraint holds.
    """
    sin_t = math.sin(theta)
    cos_t = math.cos(theta)
    pi = math.pi

    # f_2 shifted by e, and f_1 = x_1
    f2e = f"(({f2_expr}) - ({e}))"
    f1 = "x_1"

    # left-hand side: cos(theta)(f_2 - e) - sin(theta) f_1
    left = f"(({cos_t}) * {f2e} - ({sin_t}) * {f1})"
    # inner argument of the sine: sin(theta)(f_2 - e) + cos(theta) f_1
    inner = f"(({sin_t}) * {f2e} + ({cos_t}) * {f1})"
    # periodic right-hand side: a |sin(b pi inner^c)|^d
    rhs = f"({a}) * Abs(Sin(({b}) * {pi} * ({inner})**({c})))**({d})"

    # chapter form left - rhs >= 0  =>  DESDEO LTE form: rhs - left <= 0
    return f"{rhs} - {left}"


def _ctp_problem(name: str, description: str, n_variables: int, constraint_params: list[tuple]) -> Problem:
    """Builds a CTP2-CTP8 style problem from a list of constraint parameter tuples.

    Each entry of ``constraint_params`` is a ``(theta, a, b, c, d, e)`` tuple defining one
    instance of the generic CTP constraint (eq. 5 of the chapter). The objectives are
    f_1(x) = x_1 and f_2(x) = g(x)(1 - f_1(x) / g(x)).
    """
    n = n_variables

    f1_expr = "x_1"
    g_expr = _ctp_g_expr(n)
    f2_expr = f"{g_expr} * (1 - {f1_expr} / ({g_expr}))"

    variables = [
        Variable(
            name=f"x_{i}",
            symbol=f"x_{i}",
            variable_type=VariableTypeEnum.real,
            lowerbound=0.0,
            upperbound=1.0,
        )
        for i in range(1, n + 1)
    ]

    objective_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f1_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    objective_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f2_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    constraints = [
        Constraint(
            name=f"g_{idx}",
            symbol=f"g_{idx}",
            cons_type=ConstraintTypeEnum.LTE,
            func=_ctp_constraint_func(f2_expr, *params),
            is_linear=False,
            is_convex=False,
            # the constraint contains an absolute value, so it is not twice differentiable
            is_twice_differentiable=False,
        )
        for idx, params in enumerate(constraint_params, start=1)
    ]

    return Problem(
        name=name,
        description=description,
        variables=variables,
        objectives=[objective_1, objective_2],
        constraints=constraints,
        is_convex=False,
        is_linear=False,
        is_twice_differentiable=False,
    )


def ctp1(n_variables: int) -> Problem:
    r"""Defines the CTP1 test problem.

    The problem has a variable number of decision variables and two objective functions to be minimized as
    follows:

    \begin{align*}
        \min\quad f_1(\textbf{x})
        &= x_1 \\[1ex]
        \min\quad f_2(\textbf{x})
        &= g(\textbf{x})
        \exp\!\left(
        -\frac{f_1(\textbf{x})}{g(\textbf{x})}
        \right) \\[1ex]
        g(\textbf{x})
        &= 1 + \frac{9}{n-1}\sum_{i=2}^{n} x_i \\[1ex]
        g_1(\mathbf{x})
        &= 0.858\,\exp(-0.541\,x_1) - f_2(\textbf{x})
        \le 0 \\[1ex]
        g_2(\mathbf{x})
        &= 0.728\,\exp(-0.295\,x_1) - f_2(\textbf{x})
        \le 0 \\[1ex] 0
        &\le x_i \le 1,
        \qquad i = 1,\ldots,n.
    \end{align*}

    where $f_1$ and $f_2$ are objective functions, $x_1,\dots,x_n$ are decision variable, $n$
    is the number of decision variables,
    and $g_1$ and $g_2$ are auxiliary functions.
    """
    n = n_variables

    # function f_1
    f1_expr = "x_1"

    # function g
    g_expr_1 = f"1 + (9 / ({n} - 1))"
    g_expr_2 = "(" + " + ".join([f"x_{i}" for i in range(2, n + 1)]) + ")"
    g_expr = g_expr_1 + " * " + g_expr_2

    # function f_2
    f_2_expr = f"{g_expr} * Exp(-{f1_expr} / ({g_expr}))"

    variables = [
        Variable(
            name=f"x_{i}",
            symbol=f"x_{i}",
            variable_type=VariableTypeEnum.real,
            lowerbound=0.0,
            upperbound=1.0,
        )
        for i in range(1, n_variables + 1)
    ]

    objective_1 = Objective(
        name="f_1",
        symbol="f_1",
        func="x_1",
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    objective_2 = Objective(
        name="f_2",
        symbol="f_2",
        func=f_2_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    constraint_1 = Constraint(
        name="g_1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"0.858 * Exp(-0.541 * x_1) - ({f_2_expr})",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    constraint_2 = Constraint(
        name="g_2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        func=f"0.728 * Exp(-0.295 * x_1) - ({f_2_expr})",
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="ctp1",
        description="The CTP1 test problem.",
        variables=variables,
        objectives=[objective_1, objective_2],
        constraints=[constraint_1, constraint_2],
        is_convex=True,
        is_linear=False,
        is_twice_differentiable=True,
    )


def ctp2(n_variables: int) -> Problem:
    r"""Defines the CTP2 test problem.

    A variable number of decision variables and two objective functions to be minimized:

    \begin{align*}
        \min\quad f_1(\mathbf{x}) &= x_1 \\[1ex]
        \min\quad f_2(\mathbf{x}) &= g(\mathbf{x})\left(1 - \frac{f_1(\mathbf{x})}{g(\mathbf{x})}\right) \\[1ex]
        g(\mathbf{x}) &= 1 + \frac{9}{n - 1}\sum_{i=2}^{n} x_i \\[1ex]
        \text{s.t.}\quad
        &\cos(\theta)(f_2 - e) - \sin(\theta) f_1
        \ge a\left|\sin\!\big(b\pi(\sin(\theta)(f_2 - e) + \cos(\theta) f_1)^c\big)\right|^d \\[1ex]
        &0 \le x_i \le 1, \qquad i = 1,\ldots,n,
    \end{align*}

    with parameters $\theta = -0.2\pi$, $a = 0.2$, $b = 10$, $c = 1$, $d = 6$, $e = 1$. The single
    constraint makes the unconstrained Pareto front infeasible except in a number of disconnected
    regions. The g function is not specified in the original chapter; the ZDT-style g above is used
    for consistency across the DESDEO CTP suite.
    """
    return _ctp_problem(
        name="ctp2",
        description="The CTP2 test problem.",
        n_variables=n_variables,
        constraint_params=[(-0.2 * math.pi, 0.2, 10.0, 1.0, 6.0, 1.0)],
    )


def ctp3(n_variables: int) -> Problem:
    r"""Defines the CTP3 test problem.

    Same structure as :func:`ctp2` but with constraint parameters $\theta = -0.2\pi$, $a = 0.1$,
    $b = 10$, $c = 1$, $d = 0.5$, $e = 1$. The smaller $d$ shrinks each disconnected feasible region
    so that each one degenerates towards a single Pareto-optimal solution.
    """
    return _ctp_problem(
        name="ctp3",
        description="The CTP3 test problem.",
        n_variables=n_variables,
        constraint_params=[(-0.2 * math.pi, 0.1, 10.0, 1.0, 0.5, 1.0)],
    )


def ctp4(n_variables: int) -> Problem:
    r"""Defines the CTP4 test problem.

    Same structure as :func:`ctp2` but with constraint parameters $\theta = -0.2\pi$, $a = 0.75$,
    $b = 10$, $c = 1$, $d = 0.5$, $e = 1$. The larger $a$ stretches the infeasible "tunnels" far away
    from the Pareto-optimal region, making it the hardest of the front-difficulty CTP problems.
    """
    return _ctp_problem(
        name="ctp4",
        description="The CTP4 test problem.",
        n_variables=n_variables,
        constraint_params=[(-0.2 * math.pi, 0.75, 10.0, 1.0, 0.5, 1.0)],
    )


def ctp5(n_variables: int) -> Problem:
    r"""Defines the CTP5 test problem.

    Same structure as :func:`ctp2` but with constraint parameters $\theta = -0.2\pi$, $a = 0.1$,
    $b = 10$, $c = 2$, $d = 0.5$, $e = 1$. With $c \ne 1$ the discrete Pareto-optimal solutions are
    scattered non-uniformly along the front.
    """
    return _ctp_problem(
        name="ctp5",
        description="The CTP5 test problem.",
        n_variables=n_variables,
        constraint_params=[(-0.2 * math.pi, 0.1, 10.0, 2.0, 0.5, 1.0)],
    )


def ctp6(n_variables: int) -> Problem:
    r"""Defines the CTP6 test problem.

    Same structure as :func:`ctp2` but with constraint parameters $\theta = 0.1\pi$, $a = 40$,
    $b = 0.5$, $c = 1$, $d = 2$, $e = -2$. Here the infeasibility spans the entire search space as a
    series of infeasible bands; an algorithm must cross several of them to reach the feasible island
    holding the Pareto-optimal front.
    """
    return _ctp_problem(
        name="ctp6",
        description="The CTP6 test problem.",
        n_variables=n_variables,
        constraint_params=[(0.1 * math.pi, 40.0, 0.5, 1.0, 2.0, -2.0)],
    )


def ctp7(n_variables: int) -> Problem:
    r"""Defines the CTP7 test problem.

    Same structure as :func:`ctp2` but with constraint parameters $\theta = -0.05\pi$, $a = 40$,
    $b = 5$, $c = 1$, $d = 6$, $e = 0$. The infeasible bands run along the Pareto-optimal region,
    splitting the unconstrained front into a disconnected set of continuous regions.
    """
    return _ctp_problem(
        name="ctp7",
        description="The CTP7 test problem.",
        n_variables=n_variables,
        constraint_params=[(-0.05 * math.pi, 40.0, 5.0, 1.0, 6.0, 0.0)],
    )


def ctp8(n_variables: int) -> Problem:
    r"""Defines the CTP8 test problem.

    Same structure as :func:`ctp2` but with two simultaneous constraints, combining the
    entire-search-space difficulties of :func:`ctp6` and :func:`ctp7`:

    - constraint 1: $\theta = 0.1\pi$, $a = 40$, $b = 0.5$, $c = 1$, $d = 2$, $e = -2$;
    - constraint 2: $\theta = -0.05\pi$, $a = 40$, $b = 2$, $c = 1$, $d = 6$, $e = 0$.

    A solution must satisfy both constraints, leaving the feasible Pareto-optimal region as a small
    number of disconnected patches. Note: the original chapter only sketches CTP8 as a "combination
    of two or more" constraints without listing parameters; the values above are the standard ones
    from Deb (2001).
    """
    return _ctp_problem(
        name="ctp8",
        description="The CTP8 test problem.",
        n_variables=n_variables,
        constraint_params=[
            (0.1 * math.pi, 40.0, 0.5, 1.0, 2.0, -2.0),
            (-0.05 * math.pi, 40.0, 2.0, 1.0, 6.0, 0.0),
        ],
    )
