"""Contains implementations of ZDT problems."""

from math import pi

from desdeo.problem.schema import (
    ExtraFunction,
    Objective,
    Problem,
    Variable,
)


def zdt1(number_of_variables: int) -> Problem:
    r"""Defines the ZDT1 test problem.

    The problem has a variable number of decision variables and two objective functions to be minimized as
    follows:

    \begin{align*}
        \min\quad f_1(\textbf{x}) &= x_1 \\
        \min\quad f_2(\textbf{x}) &= g(\textbf{x}) \cdot h(f_1(\textbf{x}), g(\textbf{x}))\\
        g(\textbf{x}) &= 1 + \frac{9}{n-1} \sum_{i=2}^{n} x_i \\
        h(f_1, g) &= 1 - \sqrt{\frac{f_1}{g}}, \\
    \end{align*}

    where $f_1$ and $f_2$ are objective functions, $x_1,\dots,x_n$ are decision variable, $n$
    is the number of decision variables,
    and $g$ and $h$ are auxiliary functions.
    """
    n = number_of_variables

    # function f_1
    f1_symbol = "f_1"
    f1_expr = "x_1"

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
        Objective(
            name="f_1",
            symbol=f1_symbol,
            func=f1_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=True,
            is_linear=True,
            is_twice_differentiable=True,
        ),
        Objective(
            name="f_2",
            symbol=f2_symbol,
            func=f2_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=True,
            is_linear=False,
            is_twice_differentiable=True,
        ),
    ]

    extras = [
        ExtraFunction(
            name="g", symbol=g_symbol, func=g_expr, is_convex=True, is_linear=True, is_twice_differentiable=True
        ),
        ExtraFunction(
            name="h", symbol=h_symbol, func=h_expr, is_convex=True, is_linear=False, is_twice_differentiable=True
        ),
    ]

    return Problem(
        name="zdt1",
        description="The ZDT1 test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
        is_convex=True,
        is_linear=False,
        is_twice_differentiable=True,
    )


def zdt2(n_variables: int) -> Problem:
    r"""Defines the ZDT2 test problem.

    The problem has a variable number of decision variables and two objective functions to be minimized as
    follows:

    \begin{align*}
        \min\quad f_1(\textbf{x}) &= x_1 \\
        \min\quad f_2(\textbf{x}) &= g(\textbf{x}) \cdot h(f_1(\textbf{x}), g(\textbf{x}))\\
        g(\textbf{x}) &= 1 + \frac{9}{n-1} \sum_{i=2}^{n} x_i \\
        h(f_1, g) &= 1 - \left({\frac{f_1}{g}}\right)^2, \\
    \end{align*}

    where $f_1$ and $f_2$ are objective functions, $x_1,\dots,x_n$ are decision variable, $n$
    is the number of decision variables,
    and $g$ and $h$ are auxiliary functions.
    """
    n = n_variables

    # function f_1
    f1_symbol = "f_1"
    f1_expr = "x_1"

    # function g
    g_symbol = "g"
    g_expr_1 = f"1 + (9 / ({n} - 1))"
    g_expr_2 = "(" + " + ".join([f"x_{i}" for i in range(2, n + 1)]) + ")"
    g_expr = g_expr_1 + " * " + g_expr_2

    # function h(f, g)
    h_symbol = "h"
    h_expr = f"1 - (({f1_expr}) / ({g_expr})) ** 2"

    # function f_2
    f2_symbol = "f_2"
    f2_expr = f"{g_symbol} * {h_symbol}"

    variables = [
        Variable(name=f"x_{i}", symbol=f"x_{i}", variable_type="real", lowerbound=0, upperbound=1, initial_value=0.5)
        for i in range(1, n + 1)
    ]

    objectives = [
        Objective(
            name="f_1",
            symbol=f1_symbol,
            func=f1_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=True,
            is_linear=True,
            is_twice_differentiable=True,
        ),
        Objective(
            name="f_2",
            symbol=f2_symbol,
            func=f2_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
    ]

    extras = [
        ExtraFunction(
            name="g", symbol=g_symbol, func=g_expr, is_convex=True, is_linear=True, is_twice_differentiable=True
        ),
        ExtraFunction(
            name="h", symbol=h_symbol, func=h_expr, is_convex=False, is_linear=False, is_twice_differentiable=True
        ),
    ]

    return Problem(
        name="zdt2",
        description="The ZDT2 test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
        is_convex=False,
        is_linear=False,
        is_twice_differentiable=True,
    )


def zdt3(
    n_variables: int,
) -> Problem:
    r"""Defines the ZDT3 test problem.

    The problem has a variable number of decision variables and two objective functions to be minimized as
    follows:

    \begin{align*}
        \min\quad f_1(x) &= x_1 \\
        \min\quad f_2(x) &= g(\textbf{x}) \cdot h(f_1(\textbf{x}), g(\textbf{x}))\\
        g(\textbf{x}) &= 1 + \frac{9}{n-1} \sum_{i=2}^{n} x_i \\
         h(f_1, g) &= 1 - \sqrt{\frac{f_1}{g}} - \frac{f_1}{g} \sin(10\pi f_1)), \\
    \end{align*}

    where $f_1$ and $f_2$ are objective functions, $x_1,\dots,x_n$ are decision variables, $n$
    is the number of decision variables,
    and $g$ and $h$ are auxiliary functions.
    """
    n = n_variables

    # function f_1
    f1_symbol = "f_1"
    f1_expr = "x_1"

    # function g
    g_symbol = "g"
    g_expr_1 = f"1 + (9 / ({n} - 1))"
    g_expr_2 = "(" + " + ".join([f"x_{i}" for i in range(2, n + 1)]) + ")"
    g_expr = g_expr_1 + " * " + g_expr_2

    # function h(f, g)
    h_symbol = "h"
    h_expr = f"1 - Sqrt(({f1_expr}) / ({g_expr})) - (({f1_expr}) / ({g_expr})) * Sin (10 * {pi} * {f1_expr}) "

    # function f_2
    f2_symbol = "f_2"
    f2_expr = f"{g_symbol} * {h_symbol}"

    variables = [
        Variable(name=f"x_{i}", symbol=f"x_{i}", variable_type="real", lowerbound=0, upperbound=1, initial_value=0.5)
        for i in range(1, n + 1)
    ]

    objectives = [
        Objective(
            name="f_1",
            symbol=f1_symbol,
            func=f1_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=True,
            is_linear=True,
            is_twice_differentiable=True,
        ),
        Objective(
            name="f_2",
            symbol=f2_symbol,
            func=f2_expr,
            maximize=False,
            ideal=-1,
            nadir=1,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
    ]

    extras = [
        ExtraFunction(
            name="g", symbol=g_symbol, func=g_expr, is_convex=True, is_linear=True, is_twice_differentiable=True
        ),
        ExtraFunction(
            name="h", symbol=h_symbol, func=h_expr, is_convex=False, is_linear=False, is_twice_differentiable=True
        ),
    ]

    return Problem(
        name="zdt3",
        description="The ZDT3 test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
        is_convex=False,
        is_linear=False,
        is_twice_differentiable=True,
    )


def zdt4(number_of_variables: int) -> Problem:
    r"""Defines the ZDT4 test problem.

    The problem has a variable number of decision variables and two objective functions to be minimized as
    follows:

    \begin{align*}
        \min\quad f_1(\textbf{x}) &= x_1 \\
        \min\quad f_2(\text{x}) &=g(\text{x})\cdot\left(h\right) \\
        g(\text{x}) &=1+10\left(n-1\right)+\sum_{i=2}^n\left[x_i^2-10\cos\left(4\pi\cdot x_i\right)\right]\\
        h(f_1{,}g) &=1-\sqrt{\frac{f_1}{g}}, \\
    \end{align*}

    where $f_1$ and $f_2$ are objective functions, $x_1,\dots,x_n$ are decision variables, $n$
    is the number of decision variables,
    and $g$ and $h$ are auxiliary functions.
    """
    n = number_of_variables

    # function f_1
    f1_symbol = "f_1"
    f1_expr = "x_1"

    # function g
    g_symbol = "g"
    g_expr_1 = f"1 + 10 * ({n} - 1)"
    g_expr_2 = "(" + " + ".join([f"x_{i}**2 - 10 * Cos(4 * {pi} * x_{i})" for i in range(2, n + 1)]) + ")"
    g_expr = g_expr_1 + " + " + g_expr_2

    # function h(f, g)
    h_symbol = "h"
    h_expr = f"1 - Sqrt(({f1_expr}) / ({g_expr}))"

    # function f_2
    f2_symbol = "f_2"
    f2_expr = f"{g_symbol} * {h_symbol}"

    variables = [
        Variable(name=f"x_{1}", symbol=f"x_{1}", variable_type="real", lowerbound=0, upperbound=1, initial_value=0.5),
    ] + [
        Variable(name=f"x_{i}", symbol=f"x_{i}", variable_type="real", lowerbound=-5, upperbound=5, initial_value=0)
        for i in range(2, n + 1)
    ]

    objectives = [
        Objective(
            name="f_1",
            symbol=f1_symbol,
            func=f1_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=True,
            is_linear=True,
            is_twice_differentiable=True,
        ),
        Objective(
            name="f_2",
            symbol=f2_symbol,
            func=f2_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=True,
            is_linear=False,
            is_twice_differentiable=True,
        ),
    ]

    extras = [
        ExtraFunction(
            name="g", symbol=g_symbol, func=g_expr, is_convex=True, is_linear=True, is_twice_differentiable=True
        ),
        ExtraFunction(
            name="h", symbol=h_symbol, func=h_expr, is_convex=True, is_linear=False, is_twice_differentiable=True
        ),
    ]

    return Problem(
        name="zdt4",
        description="The ZDT4 test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
        is_convex=True,
        is_linear=False,
        is_twice_differentiable=True,
    )


def zdt6(number_of_variables: int) -> Problem:
    r"""Defines the ZDT6 test problem.

    The problem has a variable number of decision variables and two objective functions to be minimized as
    follows:

    \begin{align*}
        \min\quad f_1(\textbf{x}) &= 1 -\exp(-4x_1)\sin^{6}(6\pi x_1) \\
        \min\quad f_2(\textbf{x}) &= g(\textbf{x})\left[1-\left(\frac{f_1(\textbf{x})}
        {g(\textbf{x})}\right)^{2}\right] \\
        g(\textbf{x}) &= 1 + 9\left(\frac{\sum_{i=2}^{n} x_i}{n-1}\right)^{0.25}
    \end{align*}

    where $f_1$ and $f_2$ are objective functions, $x_1,\dots,x_n$ are decision variables,
    $n$ is the number of decision variables, and  $g$ is the auxillary function.
    """
    n = number_of_variables

    f1_symbol = "f_1"
    f1_expr = f"1 - Exp(-4*x_1)*(Sin(6*{pi}*x_1))**6"

    g_symbol = "g"
    g_expr_1 = " + ".join([f"x_{i}" for i in range(2, n + 1)])
    g_expr = f"1 + 9 * ((({g_expr_1}) / ({n} -  1)) ** 0.25)"

    f2_symbol = "f_2"
    f2_expr = f"{g_symbol} * (1 - ({f1_symbol} / {g_symbol})**2)"

    variables = [
        Variable(name=f"x_{i}", symbol=f"x_{i}", variable_type="real", lowerbound=0, upperbound=1, initial_value=0.5)
        for i in range(1, n + 1)
    ]

    objectives = [
        Objective(
            name="f_1",
            symbol=f1_symbol,
            func=f1_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
        Objective(
            name="f_2",
            symbol=f2_symbol,
            func=f2_expr,
            maximize=False,
            ideal=0,
            nadir=1,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
    ]

    extras = [
        ExtraFunction(
            name="g", symbol=g_symbol, func=g_expr, is_convex=False, is_linear=False, is_twice_differentiable=True
        ),
    ]

    return Problem(
        name="zdt6",
        description="The ZDT6 test problem.",
        variables=variables,
        objectives=objectives,
        extra_funcs=extras,
    )
