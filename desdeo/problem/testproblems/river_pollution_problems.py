"""Variants of the river pollution problem are defined here."""

from pathlib import Path

import polars as pl

from desdeo.problem.schema import (
    DiscreteRepresentation,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    TensorConstant,
    Variable,
    VariableTypeEnum,
)


def river_pollution_problem(*, five_objective_variant: bool = True) -> Problem:
    r"""Create a pydantic dataclass representation of the river pollution problem with either five or four variables.

    The objective functions "DO city" ($f_1$), "DO municipality" ($f_2), and
    "ROI fishery" ($f_3$) and "ROI city" ($f_4$) are to be
    maximized. If the four variant problem is used, the the "BOD deviation" objective
    function ($f_5$) is not present, but if it is, it is to be minimized.
    The problem is defined as follows:

    \begin{align*}
    \max f_1(x) &= 4.07 + 2.27 x_1 \\
    \max f_2(x) &= 2.60 + 0.03 x_1 + 0.02 x_2 + \frac{0.01}{1.39 - x_1^2} + \frac{0.30}{1.39 - x_2^2} \\
    \max f_3(x) &= 8.21 - \frac{0.71}{1.09 - x_1^2} \\
    \max f_4(x) &= 0.96 - \frac{0.96}{1.09 - x_2^2} \\
    \min f_5(x) &= \max(|x_1 - 0.65|, |x_2 - 0.65|) \\
    \text{s.t.}\quad    & 0.3 \leq x_1 \leq 1.0,\\
                        & 0.3 \leq x_2 \leq 1.0,\\
    \end{align*}

    where the fifth objective is part of the problem definition only if
    `five_objective_variant = True`.

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
            Analysis: Proceedings of the XIth International Conference on MCDM, 1-6
            August 1994, Coimbra, Portugal. Berlin, Heidelberg: Springer Berlin
            Heidelberg, 1997.
    """
    variable_1 = Variable(
        name="BOD", symbol="x_1", variable_type="real", lowerbound=0.3, upperbound=1.0, initial_value=0.65
    )
    variable_2 = Variable(
        name="DO", symbol="x_2", variable_type="real", lowerbound=0.3, upperbound=1.0, initial_value=0.65
    )

    f_1 = "4.07 + 2.27 * x_1"
    f_2 = "2.60 + 0.03 * x_1 + 0.02 * x_2 + 0.01 / (1.39 - x_1**2) + 0.30 / (1.39 - x_2**2)"
    f_3 = "8.21 - 0.71 / (1.09 - x_1**2)"
    f_4 = "0.96 - 0.96 / (1.09 - x_2**2)"
    f_5 = "Max(Abs(x_1 - 0.65), Abs(x_2 - 0.65))"

    objective_1 = Objective(
        name="DO city",
        symbol="f_1",
        func=f_1,
        maximize=True,
        ideal=6.34,
        nadir=4.75,
        is_convex=True,
        is_linear=True,
        is_twice_differentiable=True,
    )
    objective_2 = Objective(
        name="DO municipality",
        symbol="f_2",
        func=f_2,
        maximize=True,
        ideal=3.44,
        nadir=2.85,
        is_convex=False,
        is_linear=False,
        is_twice_differentiable=True,
    )
    objective_3 = Objective(
        name="ROI fishery",
        symbol="f_3",
        func=f_3,
        maximize=True,
        ideal=7.5,
        nadir=0.32,
        is_convex=True,
        is_linear=False,
        is_twice_differentiable=True,
    )
    objective_4 = Objective(
        name="ROI city",
        symbol="f_4",
        func=f_4,
        maximize=True,
        ideal=0,
        nadir=-9.70,
        is_convex=True,
        is_linear=False,
        is_twice_differentiable=True,
    )
    objective_5 = Objective(
        name="BOD deviation",
        symbol="f_5",
        func=f_5,
        maximize=False,
        ideal=0,
        nadir=0.35,
        is_convex=False,
        is_linear=False,
        is_twice_differentiable=False,
    )

    objectives = (
        [objective_1, objective_2, objective_3, objective_4, objective_5]
        if five_objective_variant
        else [objective_1, objective_2, objective_3, objective_4]
    )

    return Problem(
        name="The river pollution problem",
        description="The river pollution problem to maximize return of investments (ROI) and dissolved oxygen (DO).",
        variables=[variable_1, variable_2],
        objectives=objectives,
    )


def river_pollution_problem_discrete(*, five_objective_variant: bool = True) -> Problem:
    """Create a pydantic dataclass representation of the river pollution problem with either five or four variables.

    The objective functions "DO city" ($f_1$), "DO municipality" ($f_2), and
    "ROI fishery" ($f_3$) and "ROI city" ($f_4$) are to be
    maximized. If the four variant problem is used, the the "BOD deviation" objective
    function ($f_5$) is not present, but if it is, it is to be minimized.
    This version of the problem uses discrete representation of the variables and objectives and does not provide
    the analytical functions for the objectives.

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
            Analysis: Proceedings of the XIth International Conference on MCDM, 1-6
            August 1994, Coimbra, Portugal. Berlin, Heidelberg: Springer Berlin
            Heidelberg, 1997.
    """
    filename = "datasets/river_poll_4_objs.csv"
    true_var_names = {"x_1": "BOD", "x_2": "DO"}
    true_obj_names = {"f1": "DO city", "f2": "DO municipality", "f3": "ROI fishery", "f4": "ROI city"}
    if five_objective_variant:
        filename = "datasets/river_poll_5_objs.csv"
        true_obj_names["f5"] = "BOD deviation"

    path = Path(__file__).parent.parent.parent.parent / filename
    data = pl.read_csv(path, has_header=True)

    variables = [
        Variable(
            name=true_var_names[varName],
            symbol=varName,
            variable_type=VariableTypeEnum.real,
            lowerbound=0.3,
            upperbound=1.0,
            initial_value=0.65,
        )
        for varName in true_var_names
    ]
    maximize = {"f1": True, "f2": True, "f3": True, "f4": True, "f5": False}
    ideal = {objName: (data[objName].max() if maximize[objName] else data[objName].min()) for objName in true_obj_names}
    nadir = {objName: (data[objName].min() if maximize[objName] else data[objName].max()) for objName in true_obj_names}
    units = {"f1": "mg/L", "f2": "mg/L", "f3": "%", "f4": "%", "f5": "mg/L"}

    objectives = [
        Objective(
            name=true_obj_names[objName],
            symbol=objName,
            func=None,
            unit=units[objName],
            objective_type=ObjectiveTypeEnum.data_based,
            maximize=maximize[objName],
            ideal=ideal[objName],
            nadir=nadir[objName],
        )
        for objName in true_obj_names
    ]

    discrete_def = DiscreteRepresentation(
        variable_values=data[list(true_var_names.keys())].to_dict(),
        objective_values=data[list(true_obj_names.keys())].to_dict(),
    )

    return Problem(
        name="The river pollution problem (Discrete)",
        description="The river pollution problem to maximize return of investments (ROI) and dissolved oxygen (DO).",
        variables=variables,
        objectives=objectives,
        discrete_representation=discrete_def,
    )


def river_pollution_scenario() -> Problem:
    r"""Defines the scenario-based uncertain variant of the river pollution problem.

    The river pollution problem considers a river close to a city.
    There are two sources of pollution: industrial pollution from a
    fishery and municipal waste from the city. Two treatment plants
    (in the fishery and the city) are responsible for managing the pollution.
    Pollution is reported in pounds of biochemical oxygen demanding material (BOD),
    and water quality is measured in dissolved oxygen concentration (DO).

    Cleaning water in the city increases the tax rate, and cleaning in the
    fishery reduces the return on investment. The problem is to improve
    the DO level in the city and at the municipality border (`f1` and `f2`, respectively),
    while, at the same time, maximizing the percent return on investment at the fishery (`f3`)
    and minimizing additions to the city tax (`f4`).

    Decision variables are:

    * `x1`: The proportional amount of BOD removed from water after the fishery (treatment plant 1).
    * `x2`: The proportional amount of BOD removed from water after the city (treatment plant 2).

    The original problem considered specific values for all parameters. However, in this formulation,
    some parameters are deeply uncertain, and only a range of plausible values is known for each.
    These deeply uncertain parameters are as follows:

    * `α ∈ [3, 4.24]`: Water quality index after the fishery.
    * `β ∈ [2.25, 2.4]`: BOD reduction rate at treatment plant 1 (after the fishery).
    * `δ ∈ [0.075, 0.092]`: BOD reduction rate at treatment plant 2 (after the city).
    * `ξ ∈ [0.067, 0.083]`: Effective rate of BOD reduction at treatment plant 1 after the city.
    * `η ∈ [1.2, 1.50]`: Parameter used to calculate the effective BOD reduction rate at the second treatment plant.
    * `r ∈ [5.1, 12.5]`: Investment return rate.

    The uncertain version of the river problem is formulated as follows:

    $$
    \\begin{equation}
    \\begin{array}{rll}
    \\text{maximize}   & f_1(\\mathbf{x}) = & \\alpha + \\left(\\log\\left(\\left(\\frac{\\beta}{2}
        - 1.14\\right)^2\\right) + \\beta^3\\right) x_1 \\\\
    \\text{maximize}   & f_2(\\mathbf{x}) = & \\gamma + \\delta x_1 + \\xi x_2 + \\frac{0.01}{\\eta - x_1^2}
        + \\frac{0.30}{\\eta - x_2^2} \\\\
    \\text{maximize}   & f_3(\\mathbf{x}) = & r - \\frac{0.71}{1.09 - x_1^2} \\\\
    \\text{minimize}   & f_4(\\mathbf{x}) = & -0.96 + \\frac{0.96}{1.09 - x_2^2} \\\\
    \\text{subject to} & & 0.3 \\leq x_1, x_2 \\leq 1.0.
    \\end{array}
    \\end{equation}
    $$

    where $\\gamma = \\log\\left(\\frac{\\alpha}{2} - 1\\right) + \\frac{\\alpha}{2} + 1.5$.

    Returns:
        Problem: the scenario-based river pollution problem.

    References:
        Narula, Subhash C., and HRoland Weistroffer. "A flexible method for
            nonlinear multicriteria decision-making problems." IEEE Transactions on
            Systems, Man, and Cybernetics 19.4 (1989): 883-887.

        Miettinen, Kaisa, and Marko M. Mäkelä. "Interactive method NIMBUS for
            nondifferentiable multiobjective optimization problems." Multicriteria
            Analysis: Proceedings of the XIth International Conference on MCDM, 1-6
            August 1994, Coimbra, Portugal. Berlin, Heidelberg: Springer Berlin
            Heidelberg, 1997.
    """  # noqa: RUF002
    num_scenarios = 6
    scenario_key_stub = "scenario"

    # defining scenario parameters
    alpha_values = [4.070, 3.868, 3.620, 3.372, 3.124, 4.116]
    beta_values = [2.270, 2.262, 2.278, 2.254, 2.270, 2.286]
    delta_values = [0.0800, 0.0869, 0.0835, 0.0903, 0.0801, 0.0767]
    xi_values = [0.0750, 0.0782, 0.0750, 0.0814, 0.0686, 0.0718]
    eta_values = [1.39, 1.47, 1.23, 1.35, 1.29, 1.41]
    r_values = [8.21, 10.28, 5.84, 11.76, 7.32, 8.80]

    # each scenario parameter is defined as its own tensor constant
    alpha_constant = TensorConstant(
        name="Water quality index after fishery", symbol="alpha", shape=[num_scenarios], values=alpha_values
    )
    beta_constant = TensorConstant(
        name="BOD reduction rate at treatment plant 1 (after the fishery)",
        symbol="beta",
        shape=[num_scenarios],
        values=beta_values,
    )
    delta_constant = TensorConstant(
        name="BOD reduction rate at treatment plant 2 (after the city)",
        symbol="delta",
        shape=[num_scenarios],
        values=delta_values,
    )
    xi_constant = TensorConstant(
        name="The effective rate of BOD reduction at treatment plant 1 (after the city)",
        symbol="xi",
        shape=[num_scenarios],
        values=xi_values,
    )
    eta_constant = TensorConstant(
        name="The effective rate of BOD reduction rate at plant 2 (after the fishery)",
        symbol="eta",
        shape=[num_scenarios],
        values=eta_values,
    )
    r_constant = TensorConstant(
        name="Investment return rate",
        symbol="r",
        shape=[num_scenarios],
        values=r_values,
    )

    constants = [alpha_constant, beta_constant, delta_constant, xi_constant, eta_constant, r_constant]

    # define variables
    x1 = Variable(
        name="BOD removed after fishery",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.3,
        upperbound=1.0,
    )

    x2 = Variable(
        name="BOD removed after city",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.3,
        upperbound=1.0,
    )

    variables = [x1, x2]

    # define objectives for each scenario
    objectives = []
    scenario_keys = []

    for i in range(num_scenarios):
        scenario_key = f"{scenario_key_stub}_{i + 1}"
        scenario_keys.append(scenario_key)

        gamma_expr = f"Ln(alpha[{i + 1}]/2 - 1) + alpha[{i + 1}]/2 + 1.5"

        f1_expr = f"alpha[{i + 1}] + (Ln((beta[{i + 1}]/2 - 1.14)**2) + beta[{i + 1}]**3)*x_1"
        f2_expr = (
            f"{gamma_expr} + delta[{i + 1}]*x_1 + xi[{i + 1}]*x_2 + 0.01/(eta[{i + 1}] - x_1**2) "
            f"+ 0.3/(eta[{i + 1}] - x_2**2)"
        )
        f3_expr = f"r[{i + 1}]  - 0.71/(1.09 - x_1**2)"

        # f1
        objectives.append(
            Objective(
                name="DO level city",
                symbol=f"f1_{i + 1}",
                scenario_keys=[scenario_key],
                func=f1_expr,
                objective_type=ObjectiveTypeEnum.analytical,
                maximize=True,
                is_linear=False,
                is_convex=False,
                is_twice_differentiable=True,
            )
        )

        # f2
        objectives.append(
            Objective(
                name="DO level fishery",
                symbol=f"f2_{i + 1}",
                scenario_keys=[scenario_key],
                func=f2_expr,
                objective_type=ObjectiveTypeEnum.analytical,
                maximize=True,
                is_linear=False,
                is_convex=False,
                is_twice_differentiable=True,
            )
        )

        # f3
        objectives.append(
            Objective(
                name="Return of investment",
                symbol=f"f3_{i + 1}",
                scenario_keys=[scenario_key],
                func=f3_expr,
                objective_type=ObjectiveTypeEnum.analytical,
                maximize=True,
                is_linear=False,
                is_convex=False,
                is_twice_differentiable=True,
            )
        )

    f4_expr = "-0.96 + 0.96/(1.09 - x_2**2)"

    # f4, by setting the scenario_key to None, the objective function is assumed to be part of all the scenarios.
    objectives.append(
        Objective(
            name="Addition to city tax",
            symbol="f4",
            scenario_keys=None,
            func=f4_expr,
            objective_type=ObjectiveTypeEnum.analytical,
            maximize=False,
            is_linear=False,
            is_convex=False,
            is_twice_differentiable=True,
        )
    )

    return Problem(
        name="Scenario-based river pollution problem",
        description="The scenario-based river pollution problem",
        constants=constants,
        variables=variables,
        objectives=objectives,
        scenario_keys=scenario_keys,
    )
