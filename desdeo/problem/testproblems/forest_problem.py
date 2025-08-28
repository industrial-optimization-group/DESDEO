from pathlib import Path

import numpy as np
import polars as pl

from desdeo.problem.schema import (
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


def forest_problem(
    simulation_results: str = "./tests/data/alternatives_290124.csv",
    treatment_key: str = "./tests/data/alternatives_key_290124.csv",
    holding: int = 1,
    comparing: bool = False,
) -> Problem:
    r"""Defines a test forest problem that has TensorConstants and TensorVariables.

    The problem has TensorConstants V, W and P as vectors taking values from a data file and
    TensorVariables X_n, where n is the number of units in the data, as vectors matching the constants in shape.
    The variables are binary and each variable vector X_i has one variable with the value 1 while others have value 0.
    The variable with the value 1 for each vector X_i represents the optimal plan for the corresponding unit i.
    The three objective functions f_1, f_2, f_3 represent the net present value, wood volume at the end of
    the planning period, and the profit from harvesting.
    All of the objective functions are to be maximized.
    The problem is defined as follows:

    \begin{align}
        \max_{\mathbf{x}} & \quad \sum_{j=1}^N\sum_{i \in I_j} v_{ij} x_{ij} & \\
        & \quad \sum_{j=1}^N\sum_{i \in I_j} w_{ij} x_{ij} & \\
        & \quad \sum_{j=1}^N\sum_{i \in I_j} p_{ij} x_{ij} & \\
        \text{s.t.} & \quad \sum\limits_{i \in I_j} x_{ij} = 1, & \forall j = 1 \ldots N \\
        & \quad x_{ij}\in \{0,1\}& \forall j = 1 \ldots N, ~\forall i\in I_j,
    \end{align}

    where $x_{ij}$ are decision variables representing the choice of implementing management plan $i$ in stand $j$,
    and $I_j$ is the set of available management plans for stand $j$. For each plan $i$ in stand $j$
    the net present value, wood volume at the end of the planning period, and the profit from harvesting
    are represented by $v_{ij}$, $w_{ij}$, and $p_{ij}$ respectively.

    Args:
        simulation_results (str): Location of the simulation results file.
        treatment_key (str): Location of the file with the treatment information.
        holding (int, optional): The number of the holding to be optimized. Defaults to 1.
        comparing (bool, optional): This is only used for testing the method.
            If comparing == True, the results are nonsense. Defaults to False.

    Returns:
        Problem: An instance of the test forest problem.
    """
    df = pl.read_csv(simulation_results, schema_overrides={"unit": pl.Float64})
    df_key = pl.read_csv(treatment_key, schema_overrides={"unit": pl.Float64})

    df_joined = df.join(df_key, on=["holding", "unit", "schedule"], how="left")

    selected_df = df_joined.filter(pl.col("holding") == holding).select(
        [
            "unit",
            "schedule",
            "npv_5_percent",
            "stock_2025",
            "stock_2035",
            "harvest_value_period_2025",
            "harvest_value_period_2030",
            "harvest_value_period_2035",
            "treatment",
        ]
    )
    unique_units = selected_df.unique(["unit"], maintain_order=True).get_column("unit")
    n_units = len(unique_units)
    unique_schedules = selected_df.unique(["schedule"], maintain_order=True).get_column("schedule")
    n_schedules = len(unique_schedules)

    v_array = np.zeros((n_units, n_schedules))
    w_array = np.zeros((n_units, n_schedules))
    p_array = np.zeros((n_units, n_schedules))

    # This is not the fastest way to do this, but the code is probably more understandable
    for i in range(n_units):
        for j in range(n_schedules):
            unit = unique_units[i]
            schedule = unique_schedules[j]
            print(f"unit {unit} schedule {schedule}")
            if selected_df.filter((pl.col("unit") == unit) & (pl.col("schedule") == schedule)).height == 0:
                continue
            v_array[i][j] = (
                selected_df.filter((pl.col("unit") == unit) & (pl.col("schedule") == schedule))
                .select("npv_5_percent")
                .item()
            )
            w_array[i][j] = (
                selected_df.filter((pl.col("unit") == unit) & (pl.col("schedule") == schedule))
                .select("stock_2035")
                .item()
            )
            if comparing:
                w_array[i][j] -= (
                    selected_df.filter((pl.col("unit") == unit) & (pl.col("schedule") == schedule))
                    .select("stock_2025")
                    .item()
                )
            # The harvest values are not going to be discounted like this
            p_array[i][j] = sum(
                selected_df.filter((pl.col("unit") == unit) & (pl.col("schedule") == schedule))
                .select(["harvest_value_period_2025", "harvest_value_period_2030", "harvest_value_period_2035"])
                .row(0)
            )

    constants = []
    variables = []
    constraints = []
    f_1_func = []
    f_2_func = []
    f_3_func = []
    # define the constants V, W and P, decision variable X, constraints, and objective function expressions in one loop
    for i in range(n_units):
        # Constants V, W and P
        v = TensorConstant(
            name=f"V_{i + 1}",
            symbol=f"V_{i + 1}",
            shape=[np.shape(v_array)[1]],  # NOTE: vectors have to be of form [2] instead of [2,1] or [1,2]
            values=v_array[i].tolist(),
        )
        constants.append(v)
        w = TensorConstant(
            name=f"W_{i + 1}",
            symbol=f"W_{i + 1}",
            shape=[np.shape(w_array)[1]],  # NOTE: vectors have to be of form [2] instead of [2,1] or [1,2]
            values=w_array[i].tolist(),
        )
        constants.append(w)
        p = TensorConstant(
            name=f"P_{i + 1}",
            symbol=f"P_{i + 1}",
            shape=[np.shape(p_array)[1]],  # NOTE: vectors have to be of form [2] instead of [2,1] or [1,2]
            values=p_array[i].tolist(),
        )

        # Decision variable X
        constants.append(p)
        x = TensorVariable(
            name=f"X_{i + 1}",
            symbol=f"X_{i + 1}",
            variable_type=VariableTypeEnum.binary,
            shape=[np.shape(v_array)[1]],  # NOTE: vectors have to be of form [2] instead of [2,1] or [1,2]
            lowerbounds=np.shape(v_array)[1] * [0],
            upperbounds=np.shape(v_array)[1] * [1],
            initial_values=np.shape(v_array)[1] * [0],
        )
        variables.append(x)

        # Constraints
        con = Constraint(
            name=f"x_con_{i + 1}",
            symbol=f"x_con_{i + 1}",
            cons_type=ConstraintTypeEnum.EQ,
            func=f"Sum(X_{i + 1}) - 1",
            is_linear=True,
            is_convex=False,  # not checked
            is_twice_differentiable=True,
        )
        constraints.append(con)

        # Objective function expressions
        exprs = f"V_{i + 1}@X_{i + 1}"
        f_1_func.append(exprs)

        exprs = f"W_{i + 1}@X_{i + 1}"
        f_2_func.append(exprs)

        exprs = f"P_{i + 1}@X_{i + 1}"
        f_3_func.append(exprs)

    # form the objective function sums
    f_1_func = " + ".join(f_1_func)
    f_2_func = " + ".join(f_2_func)
    f_3_func = " + ".join(f_3_func)

    f_1 = Objective(
        name="Net present value",
        symbol="f_1",
        func=f_1_func,
        maximize=True,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=False,  # not checked
        is_twice_differentiable=True,
    )

    f_2 = Objective(
        name="Wood stock volume",
        symbol="f_2",
        func=f_2_func,
        maximize=True,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=False,  # not checked
        is_twice_differentiable=True,
    )

    f_3 = Objective(
        name="Harvest value",
        symbol="f_3",
        func=f_3_func,
        maximize=True,
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=False,  # not checked
        is_twice_differentiable=True,
    )

    return Problem(
        name="Forest problem",
        description="A test forest problem.",
        constants=constants,
        variables=variables,
        objectives=[f_1, f_2, f_3],
        constraints=constraints,
    )


def forest_problem_discrete() -> Problem:
    """Implements the forest problem using Pareto front representation.

    Returns:
        Problem: A problem instance representing the forest problem.
    """
    filename = "datasets/forest_holding_4.csv"

    path = Path(__file__).parent.parent.parent.parent / filename

    obj_names = ["stock", "harvest_value", "npv"]

    var_name = "index"

    data = pl.read_csv(
        path, has_header=True, columns=["stock", "harvest_value", "npv"], separator=";", decimal_comma=True
    )

    variables = [
        Variable(
            name=var_name,
            symbol=var_name,
            variable_type=VariableTypeEnum.integer,
            lowerbound=0,
            upperbound=len(data) - 1,
            initial_value=0,
        )
    ]

    objectives = [
        Objective(
            name=obj_name,
            symbol=obj_name,
            objective_type=ObjectiveTypeEnum.data_based,
            ideal=data[obj_name].max(),
            nadir=data[obj_name].min(),
            maximize=True,
        )
        for obj_name in obj_names
    ]

    discrete_def = DiscreteRepresentation(
        variable_values={"index": list(range(len(data)))},
        objective_values=data[[obj.symbol for obj in objectives]].to_dict(),
    )

    return Problem(
        name="Finnish Forest Problem (Discrete)",
        description="Defines a forest problem with three objectives: stock, harvest value, and net present value.",
        variables=variables,
        objectives=objectives,
        discrete_representation=discrete_def,
    )
