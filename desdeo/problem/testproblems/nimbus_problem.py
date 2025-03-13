from desdeo.problem.schema import (
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)

def nimbus_test_problem() -> Problem:
    r"""Defines the test problem utilized in the article describing Synchronous NIMBUS.

    Defines the following multiobjective optimization problem:

    \begin{align}
        &\max_{\mathbf{x}} & f_1(\mathbf{x}) &= x_1 x_2\\
        &\min_{\mathbf{x}} & f_2(\mathbf{x}) &= (x_1 - 4)^2 + x_2^2\\
        &\min_{\mathbf{x}} & f_3(\mathbf{x}) &= -x_1 - x_2\\
        &\min_{\mathbf{x}} & f_4(\mathbf{x}) &= x_1 - x_2\\
        &\min_{\mathbf{x}} & f_5(\mathbf{x}) &= 50 x_1^4 + 10 x_2^4 \\
        &\min_{\mathbf{x}} & f_6(\mathbf{x}) &= 30 (x_1 - 5)^4 + 100 (x_2 - 3)^4\\
        &\text{s.t.,}     && 1 \leq x_i \leq 3\quad i=\{1,2\},
    \end{align}

    with the following ideal point
    $\mathbf{z}^\star = \left[9.0, 2.0, -6.0, -2.0, 60.0, 480.0 \right]$ and nadir point
    $\mathbf{z}^\text{nad} = \left[ 1.0, 18.0, -2.0, 2.0, 4860.0, 9280.0 \right]$.

    References:
        Miettinen, K., & Mäkelä, M. M. (2006). Synchronous approach in
            interactive multiobjective optimization. European Journal of Operational
            Research, 170(3), 909–922. https://doi.org/10.1016/j.ejor.2004.07.052


    Returns:
        Problem: the NIMBUS test problem.
    """
    variables = [
        Variable(
            name="x_1",
            symbol="x_1",
            variable_type=VariableTypeEnum.real,
            initial_value=1.0,
            lowerbound=1.0,
            upperbound=3.0,
        ),
        Variable(
            name="x_2",
            symbol="x_2",
            variable_type=VariableTypeEnum.real,
            initial_value=1.0,
            lowerbound=1.0,
            upperbound=3.0,
        ),
    ]

    f_1_expr = "x_1 * x_2"
    f_2_expr = "(x_1 - 4)**2 + x_2**2"
    f_3_expr = "-x_1 - x_2"
    f_4_expr = "x_1 - x_2"
    f_5_expr = "50 * x_1**4 + 10 * x_2**4"
    f_6_expr = "30 * (x_1 - 5)**4 + 100*(x_2 - 3)**4"

    objectives = [
        Objective(
            name="Objective 1",
            symbol="f_1",
            func=f_1_expr,
            maximize=True,
            objective_type=ObjectiveTypeEnum.analytical,
            ideal=9.0,
            nadir=1.0,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
        Objective(
            name="Objective 2",
            symbol="f_2",
            func=f_2_expr,
            maximize=False,
            objective_type=ObjectiveTypeEnum.analytical,
            ideal=2.0,
            nadir=18.0,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
        Objective(
            name="Objective 3",
            symbol="f_3",
            func=f_3_expr,
            maximize=False,
            objective_type=ObjectiveTypeEnum.analytical,
            ideal=-6.0,
            nadir=-2.0,
            is_convex=True,
            is_linear=True,
            is_twice_differentiable=True,
        ),
        Objective(
            name="Objective 4",
            symbol="f_4",
            func=f_4_expr,
            maximize=False,
            objective_type=ObjectiveTypeEnum.analytical,
            ideal=-2.0,
            nadir=2.0,
            is_convex=True,
            is_linear=True,
            is_twice_differentiable=True,
        ),
        Objective(
            name="Objective 5",
            symbol="f_5",
            func=f_5_expr,
            maximize=False,
            objective_type=ObjectiveTypeEnum.analytical,
            ideal=60.0,
            nadir=4860.0,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
        Objective(
            name="Objective 6",
            symbol="f_6",
            func=f_6_expr,
            maximize=False,
            objective_type=ObjectiveTypeEnum.analytical,
            ideal=480.0,
            nadir=9280.0,
            is_convex=False,
            is_linear=False,
            is_twice_differentiable=True,
        ),
    ]

    return Problem(
        name="NIMBUS test problem",
        description="The test problem used in the Synchronous NIMBUS article",
        variables=variables,
        objectives=objectives,
    )
