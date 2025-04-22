from pathlib import Path

import polars as pl

from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)

def spanish_sustainability_problem():
    """Implements the Spanish sustainability problem."""
    coefficients_dict = {
        "social_linear": {
            "x_1": -0.0108,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.185,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.00855,
            "x_10": 0.0,
            "x_11": 0.0,
        },
        "social_quadratic": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": 0.0,
        },
        "social_cubic": {
            "x_1": 0.0,
            "x_2": 9.79e-07,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": 0.0,
        },
        "social_log": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": 0.0,
        },
        "economical_linear": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.38,
            "x_5": 0.0281,
            "x_6": 0.0,
            "x_7": 0.00826,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": 0.0,
        },
        "economical_quadratic": {
            "x_1": -0.000316,
            "x_2": 3.18e-05,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.000662,
            "x_9": 0.0,
            "x_10": 1.81e-05,
            "x_11": 0.0,
        },
        "economical_cubic": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": 0.0,
        },
        "economical_log": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.121,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": -0.262,
        },
        "enviro_linear": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": -0.00122,
            "x_11": 0.0,
        },
        "enviro_quadratic": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": 0.0,
            "x_7": -0.000245,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": 1.2e-05,
        },
        "enviro_cubic": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": 0.0,
            "x_6": -2.37e-06,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": 0.0,
        },
        "enviro_log": {
            "x_1": 0.0,
            "x_2": 0.0,
            "x_3": 0.0,
            "x_4": 0.0,
            "x_5": -0.329,
            "x_6": 0.0,
            "x_7": 0.0,
            "x_8": 0.0,
            "x_9": 0.0,
            "x_10": 0.0,
            "x_11": 0.0,
        },
        "lower_bounds": {
            "x_1": 1,
            "x_2": 60,
            "x_3": 1,
            "x_4": 1,
            "x_5": 1,
            "x_6": 1,
            "x_7": 1,
            "x_8": 1,
            "x_9": 40,
            "x_10": 75,
            "x_11": 80,
        },
        "upper_bounds": {
            "x_1": 40,
            "x_2": 90,
            "x_3": 25,
            "x_4": 3,
            "x_5": 40,
            "x_6": 15,
            "x_7": 30,
            "x_8": 25,
            "x_9": 70,
            "x_10": 105,
            "x_11": 120,
        },
    }

    social_cte_value = -0.46
    economical_cte_value = 0.12
    enviro_cte_value = 2.92

    coefficients = (
        pl.DataFrame(coefficients_dict)
        .transpose(include_header=True, column_names=["coefficients"])
        .unnest("coefficients")
    )

    variable_names = [f"x_{i}" for i in range(1, 12)]
    n_variables = len(variable_names)

    # Define constants
    # For the social indicator
    social_linear = TensorConstant(
        name="Linear coefficients for the social indicator",
        symbol="beta_social",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "social_linear").row(0)[1:]),
    )

    social_quadratic = TensorConstant(
        name="Quadratic coefficients for the social indicator",
        symbol="gamma_social",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "social_quadratic").row(0)[1:]),
    )

    social_cubic = TensorConstant(
        name="Cubic coefficients for the social indicator",
        symbol="delta_social",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "social_cubic").row(0)[1:]),
    )

    social_log = TensorConstant(
        name="Logarithmic coefficients for the social indicator",
        symbol="omega_social",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "social_log").row(0)[1:]),
    )

    social_c = Constant(
        name="Constant coefficient for the social indicator", symbol="cte_social", value=social_cte_value
    )

    # For the economical indicator
    economical_linear = TensorConstant(
        name="Linear coefficients for the economical indicator",
        symbol="beta_economical",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "economical_linear").row(0)[1:]),
    )

    economical_quadratic = TensorConstant(
        name="Quadratic coefficients for the economical indicator",
        symbol="gamma_economical",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "economical_quadratic").row(0)[1:]),
    )

    economical_cubic = TensorConstant(
        name="Cubic coefficients for the economical indicator",
        symbol="delta_economical",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "economical_cubic").row(0)[1:]),
    )

    economical_log = TensorConstant(
        name="Logarithmic coefficients for the economical indicator",
        symbol="omega_economical",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "economical_log").row(0)[1:]),
    )

    economical_c = Constant(
        name="Constant coefficient for the economical indicator", symbol="cte_economical", value=economical_cte_value
    )

    # For the environmental indicator
    enviro_linear = TensorConstant(
        name="Linear coefficients for the environmental indicator",
        symbol="beta_enviro",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "enviro_linear").row(0)[1:]),
    )

    enviro_quadratic = TensorConstant(
        name="Quadratic coefficients for the environmental indicator",
        symbol="gamma_enviro",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "enviro_quadratic").row(0)[1:]),
    )

    enviro_cubic = TensorConstant(
        name="Cubic coefficients for the environmental indicator",
        symbol="delta_enviro",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "enviro_cubic").row(0)[1:]),
    )

    enviro_log = TensorConstant(
        name="Logarithmic coefficients for the environmental indicator",
        symbol="omega_enviro",
        shape=[n_variables],
        values=list(coefficients.filter(pl.col("column") == "enviro_log").row(0)[1:]),
    )

    enviro_c = Constant(
        name="Constant coefficient for the environmental indicator", symbol="cte_enviro", value=enviro_cte_value
    )

    constants = [
        social_linear,
        social_quadratic,
        social_cubic,
        social_log,
        social_c,
        economical_linear,
        economical_quadratic,
        economical_cubic,
        economical_log,
        economical_c,
        enviro_linear,
        enviro_quadratic,
        enviro_cubic,
        enviro_log,
        enviro_c,
    ]

    # Define variables
    x = TensorVariable(
        name="Variables 'x_1' through 'x_11' defined as a vector.",
        symbol="X",
        variable_type=VariableTypeEnum.real,
        shape=[n_variables],
        lowerbounds=list(coefficients.filter(pl.col("column") == "lower_bounds").row(0)[1:]),
        upperbounds=list(coefficients.filter(pl.col("column") == "upper_bounds").row(0)[1:]),
        initial_values=1.0,
    )

    variables = [x]

    # Define objective functions
    # Social
    f1_expr = "cte_social + X @ beta_social + (X**2) @ gamma_social + (X**3) @ delta_social + Ln(X) @ omega_social"

    f1 = Objective(
        name="Societal indicator",
        symbol="f1",
        func=f1_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=1.17,
        nadir=1.15,
        maximize=True,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    # economical
    f2_expr = (
        "cte_economical + beta_economical @ X + gamma_economical @ (X**2) + delta_economical @ (X**3) "
        "+ omega_economical @ Ln(X)"
    )

    f2 = Objective(
        name="economical indicator",
        symbol="f2",
        func=f2_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=1.98,
        nadir=0.63,
        maximize=True,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    # Environmental
    f3_expr = "cte_enviro + beta_enviro @ X + gamma_enviro @ (X**2) + delta_enviro @ (X**3) " "+ omega_enviro @ Ln(X)"

    f3 = Objective(
        name="Environmental indicator",
        symbol="f3",
        func=f3_expr,
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=2.93,
        nadir=1.52,
        maximize=True,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    objectives = [f1, f2, f3]

    # Define constraints

    con_1_expr = "(18844.09 * X[3] + 31749.1) - X[9]**3"
    con_1 = Constraint(
        name="Independent X[3], dependent X[9]. Less than part.",
        symbol="con_1",
        func=con_1_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_2_expr = "X[9]**3 - (25429.65 * X[3] + 114818.5)"
    con_2 = Constraint(
        name="Independent X[3], dependent X[9]. More than part.",
        symbol="con_2",
        func=con_2_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_3_expr = "(0.0696724 * X[3] + 0.4026487) - X[4]"
    con_3 = Constraint(
        name="Independent X[3], dependent X[4]. Less than part.",
        symbol="con_3",
        func=con_3_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    con_4_expr = "X[4] - (0.1042275 * X[3] + 0.8385217)"
    con_4 = Constraint(
        name="Independent X[3], dependent X[4]. More than part.",
        symbol="con_4",
        func=con_4_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    con_5_expr = "(2.90e-06 * X[9]**3 + 0.2561155) - X[4]"
    con_5 = Constraint(
        name="Independent X[9]^3, dependent X[4]. Less than part.",
        symbol="con_5",
        func=con_5_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_6_expr = "X[4] - (4.07e-06 * X[9]**3 + 0.6763224)"
    con_6 = Constraint(
        name="Independent X[9]^3, dependent X[4]. More than part.",
        symbol="con_6",
        func=con_6_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_7_expr = "(-0.0121761 * X[6] + 4.272166) - Ln(X[9])"
    con_7 = Constraint(
        name="Independent X[6], dependent Ln(X[9]). Less than part.",
        symbol="con_7",
        func=con_7_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_8_expr = "Ln(X[9]) - (-0.0078968 * X[6] + 4.387051)"
    con_8 = Constraint(
        name="Independent X[6], dependent Ln(X[9]). More than part.",
        symbol="con_8",
        func=con_8_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_9_expr = "(-0.6514348 * Ln(X[1]) + 5.368645) - Ln(X[9])"
    con_9 = Constraint(
        name="Independent Ln(X[1]), dependent Ln(X[9]). Less than part.",
        symbol="con_9",
        func=con_9_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_10_expr = "Ln(X[9]) - (-0.3965489 * Ln(X[1]) + 6.174052)"
    con_10 = Constraint(
        name="Independent Ln(X[1]), dependent Ln(X[9]). More than part.",
        symbol="con_10",
        func=con_10_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_11_expr = "(-1.660054 * Ln(X[1]) + 3.524567) - Ln(X[4])"
    con_11 = Constraint(
        name="Independent Ln(X[1]), dependent Ln(X[4]). Less than part.",
        symbol="con_11",
        func=con_11_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_12_expr = "Ln(X[4]) - (-1.045873 * Ln(X[1]) + 5.4653)"
    con_12 = Constraint(
        name="Independent Ln(X[1]), dependent Ln(X[4]). More than part.",
        symbol="con_12",
        func=con_12_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_13_expr = "(54.36616 * X[1] - 1525.248) - X[6]**2"
    con_13 = Constraint(
        name="Independent X[1], dependent X[6]^2. Less than part.",
        symbol="con_13",
        func=con_13_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_14_expr = "X[6]**2 - (90.89275 * X[1] - 581.0572)"
    con_14 = Constraint(
        name="Independent X[1], dependent X[6]^2. More than part.",
        symbol="con_14",
        func=con_14_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_15_expr = "(0.5171291 * X[1]**3 + 4384.214) - X[7]**3"
    con_15 = Constraint(
        name="Independent X[1]^3, dependent X[7]^3. Less than part.",
        symbol="con_15",
        func=con_15_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_16_expr = "X[7]**3 - (0.7551735 * X[1]**3 + 13106.71)"
    con_16 = Constraint(
        name="Independent X[1]^3, dependent X[7]^3. More than part.",
        symbol="con_16",
        func=con_16_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_17_expr = "(-9.537996 * Ln(X[3]) + 36.99891) - X[7]"
    con_17 = Constraint(
        name="Independent Ln(X[3]), dependent X[7]. Less than part.",
        symbol="con_17",
        func=con_17_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_18_expr = "X[7] - (-5.908175 * Ln(X[3]) + 44.97534)"
    con_18 = Constraint(
        name="Independent Ln(X[3]), dependent X[7]. More than part.",
        symbol="con_18",
        func=con_18_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_19_expr = "(-1.233805 * Ln(X[9]) + 6.303354) - Ln(X[7])"
    con_19 = Constraint(
        name="Independent Ln(X[9]), dependent Ln(X[7]). Less than part.",
        symbol="con_19",
        func=con_19_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_20_expr = "Ln(X[7]) - (-0.7622909 * Ln(X[9]) + 8.251018)"
    con_20 = Constraint(
        name="Independent Ln(X[9]), dependent Ln(X[7]). More than part.",
        symbol="con_20",
        func=con_20_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_21_expr = "(0.0701477 * X[10] + 4.270586) - X[8]"
    con_21 = Constraint(
        name="Independent X[10], dependent X[8]. Less than part.",
        symbol="con_21",
        func=con_21_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    con_22_expr = "X[8] - (0.1216334 * X[10] + 6.975359)"
    con_22 = Constraint(
        name="Independent X[10], dependent X[8]. More than part.",
        symbol="con_22",
        func=con_22_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    con_23_expr = "(-11.7387 * Ln(X[4]) + 25.75422) - X[7]"
    con_23 = Constraint(
        name="Independent Ln(X[4]), dependent X[7]. Less than part.",
        symbol="con_23",
        func=con_23_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_24_expr = "X[7] - (-6.886529 * Ln(X[4]) + 28.89969)"
    con_24 = Constraint(
        name="Independent Ln(X[4]), dependent X[7]. More than part.",
        symbol="con_24",
        func=con_24_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_25_expr = "(-1217.427 * Ln(X[4]) + 773.2538) - X[6]**2"
    con_25 = Constraint(
        name="Independent Ln(X[4]), dependent X[6]^2. Less than part.",
        symbol="con_25",
        func=con_25_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_26_expr = "X[6]**2 - (-677.1691 * Ln(X[4]) + 1123.481)"
    con_26 = Constraint(
        name="Independent Ln(X[4]), dependent X[6]^2. More than part.",
        symbol="con_26",
        func=con_26_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_27_expr = "(-0.0793273 * X[1] + 3.300731) - Ln(X[3])"
    con_27 = Constraint(
        name="Independent X[1], dependent Ln(X[3]). Less than part.",
        symbol="con_27",
        func=con_27_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_28_expr = "Ln(X[3]) - (-0.0516687 * X[1] + 4.015687)"
    con_28 = Constraint(
        name="Independent X[1], dependent Ln(X[3]). More than part.",
        symbol="con_28",
        func=con_28_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_29_expr = "(-6.32e-06 * X[2]**3 + 3.694027) - Ln(X[6])"
    con_29 = Constraint(
        name="Independent X[2]^3, dependent Ln(X[6]). Less than part.",
        symbol="con_29",
        func=con_29_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_30_expr = "Ln(X[6]) - (-3.72e-06 * X[2]**3 + 4.566568)"
    con_30 = Constraint(
        name="Independent X[2]^3, dependent Ln(X[6]). More than part.",
        symbol="con_30",
        func=con_30_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_31_expr = "(-19.18876 * Ln(X[3]) + 44.91148) - X[6]"
    con_31 = Constraint(
        name="Independent Ln(X[3]), dependent X[6]. Less than part.",
        symbol="con_31",
        func=con_31_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_32_expr = "X[6] - (-12.08424 * Ln(X[3]) + 60.52347)"
    con_32 = Constraint(
        name="Independent Ln(X[3]), dependent X[6]. More than part.",
        symbol="con_32",
        func=con_32_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_33_expr = "(0.6393434 * Ln(X[4]) + 1.433712) - Ln(X[8])"
    con_33 = Constraint(
        name="Independent Ln(X[4]), dependent Ln(X[8]). Less than part.",
        symbol="con_33",
        func=con_33_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_34_expr = "Ln(X[8]) - (1.1418 * Ln(X[4]) + 1.759434)"
    con_34 = Constraint(
        name="Independent Ln(X[4]), dependent Ln(X[8]). More than part.",
        symbol="con_34",
        func=con_34_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_f1_1_expr = "-1.0*f1"
    con_f1_1 = Constraint(
        name="f1 greater than zero",
        symbol="con_f1_1",
        func=con_f1_1_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_f1_2_expr = "f1 - 4.0"
    con_f1_2 = Constraint(
        name="f1 less than four",
        symbol="con_f1_2",
        func=con_f1_2_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_f2_1_expr = "-1.0*f2"
    con_f2_1 = Constraint(
        name="f2 greater than zero",
        symbol="con_f2_1",
        func=con_f2_1_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_f2_2_expr = "f2 - 4.0"
    con_f2_2 = Constraint(
        name="f2 less than four",
        symbol="con_f2_2",
        func=con_f2_2_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_f3_1_expr = "-1.0*f3"
    con_f3_1 = Constraint(
        name="f3 greater than zero",
        symbol="con_f3_1",
        func=con_f3_1_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    con_f3_2_expr = "f3 - 4.0"
    con_f3_2 = Constraint(
        name="f3 less than four",
        symbol="con_f3_2",
        func=con_f3_2_expr,
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    constraints = [
        con_1,
        con_2,
        con_3,
        con_4,
        con_5,
        con_6,
        con_7,
        con_8,
        con_9,
        con_10,
        con_11,
        con_12,
        con_13,
        con_14,
        con_15,
        con_16,
        con_17,
        con_18,
        con_19,
        con_20,
        con_21,
        con_22,
        con_23,
        con_24,
        con_25,
        con_26,
        con_27,
        con_28,
        con_29,
        con_30,
        con_31,
        con_32,
        con_33,
        con_34,
        con_f1_1,
        con_f1_2,
        con_f2_1,
        con_f2_2,
        con_f3_1,
        con_f3_2,
    ]

    return Problem(
        name="Spanish sustainability problem.",
        description="Defines a sustainability problem with three indicators: societal, economical, and environmental.",
        constants=constants,
        variables=variables,
        objectives=objectives,
        constraints=constraints,
    )


def spanish_sustainability_problem_discrete():
    """Implements the Spanish sustainability problem using Pareto front representation."""
    filename = "datasets/sustainability_spanish.csv"
    varnames = [f"x{i}" for i in range(1, 12)]
    objNames = {"f1": "social", "f2": "economic", "f3": "environmental"}

    path = Path(__file__).parent.parent.parent.parent / filename
    data = pl.read_csv(path, has_header=True)

    data = data.rename({"social": "f1", "economic": "f2", "environmental": "f3"})

    variables = [
        Variable(
            name=varname,
            symbol=varname,
            variable_type=VariableTypeEnum.real,
            lowerbound=data[varname].min(),
            upperbound=data[varname].max(),
            initial_value=data[varname].mean(),
        )
        for varname in varnames
    ]

    objectives = [
        Objective(
            name=objNames[objname],
            symbol=objname,
            objective_type=ObjectiveTypeEnum.data_based,
            ideal=data[objname].max(),
            nadir=data[objname].min(),
            maximize=True,
        )
        for objname in objNames
    ]

    discrete_def = DiscreteRepresentation(
        variable_values=data[varnames].to_dict(),
        objective_values=data[[obj.symbol for obj in objectives]].to_dict(),
    )

    return Problem(
        name="Spanish sustainability problem (Discrete)",
        description="Defines a sustainability problem with three indicators: social, ecological, and environmental.",
        variables=variables,
        objectives=objectives,
        discrete_representation=discrete_def,
    )
