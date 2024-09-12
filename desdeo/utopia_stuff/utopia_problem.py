import math
import numpy as np
from pathlib import Path
import polars as pl

from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools.utils import available_solvers, payoff_table_method


def utopia_problem(problem_name: str = "Forest problem", holding: int = 1) -> tuple[Problem, dict]:
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
        \mbox{maximize~} & \sum_{j=1}^N\sum_{i \in I_j} v_{ij} x_{ij} & \\
        \mbox{maximize~} & \sum_{j=1}^N\sum_{i \in I_j} w_{ij} x_{ij} & \\
        \mbox{maximize~} & \sum_{j=1}^N\sum_{i \in I_j} p_{ij} x_{ij} & \\
        \nonumber\\
        \mbox{subject to~} &  \sum\limits_{i \in I_j} x_{ij} = 1, & \forall j = 1 \ldots N \\
        & x_{ij}\in \{0,1\}& \forall j = 1 \ldots N, ~\forall i\in I_j,
    \end{align}

    where $x_{ij}$ are decision variables representing the choice of implementing management plan $i$ in stand $j$,
    and $I_j$ is the set of available management plans for stand $j$. For each plan $i$ in stand $j$
    the net present value, wood volume at the end of the planning period, and the profit from harvesting
    are represented by $v_{ij}$, $w_{ij}$, and $p_{ij}$ respectively.

    Args:
        holding (int, optional): The number of the holding to be optimized. Defaults to 1.
        comparing (bool, optional): Determines if solutions are to be compared to those from the rahti app.
            Defaults to None.

    Returns:
        Problem: An instance of the test forest problem.
    """
    # TODO: remove this at some point
    comparing = False

    schedule_dict = {}

    df = pl.read_csv(Path("tests/data/alternatives_290124.csv"), dtypes={"unit": pl.Float64})
    df_key = pl.read_csv(Path("tests/data/alternatives_key_290124.csv"), dtypes={"unit": pl.Float64})

    selected_df_v = df.filter(pl.col("holding") == holding).select(["unit", "schedule", "npv_5_percent"])
    unique_units = selected_df_v.unique(["unit"], maintain_order=True).get_column("unit")
    selected_df_v.group_by(["unit", "schedule"])
    rows_by_key = selected_df_v.rows_by_key(key=["unit", "schedule"])
    v_array = np.zeros((selected_df_v["unit"].n_unique(), selected_df_v["schedule"].n_unique()))
    for i in range(np.shape(v_array)[0]):
        for j in range(np.shape(v_array)[1]):
            if (unique_units[i], j) in rows_by_key:
                v_array[i][j] = rows_by_key[(unique_units[i], j)][0]

    # determine whether the results are to be compared to those from the rahti app (for testing purposes)
    # if compared, the stock values are calculated by substacting the value after 2025 period from
    # the value after the 2035 period (in other words, last value - first value)
    if comparing:
        selected_df_w = df.filter(pl.col("holding") == holding).select(["unit", "schedule", "stock_2025", "stock_2035"])
        selected_df_w.group_by(["unit", "schedule"])
        rows_by_key = selected_df_w.rows_by_key(key=["unit", "schedule"])
        selected_df_key_w = df_key.select(["unit", "schedule", "treatment"])
        selected_df_key_w.group_by(["unit", "schedule"])
        rows_by_key_df_key = selected_df_key_w.rows_by_key(key=["unit", "schedule"])
        w_array = np.zeros((selected_df_w["unit"].n_unique(), selected_df_w["schedule"].n_unique()))
        for i in range(np.shape(w_array)[0]):
            for j in range(np.shape(w_array)[1]):
                if len(rows_by_key_df_key[(unique_units[i], j)]) == 0:
                    continue
                if (unique_units[i], j) in rows_by_key:
                    w_array[i][j] = rows_by_key[(unique_units[i], j)][0][1] - rows_by_key[(unique_units[i], j)][0][0]
    else:
        selected_df_w = df.filter(pl.col("holding") == holding).select(["unit", "schedule", "stock_2035"])
        selected_df_w.group_by(["unit", "schedule"])
        rows_by_key = selected_df_w.rows_by_key(key=["unit", "schedule"])
        selected_df_key_w = df_key.select(["unit", "schedule", "treatment"])
        selected_df_key_w.group_by(["unit", "schedule"])
        rows_by_key_df_key = selected_df_key_w.rows_by_key(key=["unit", "schedule"])
        w_array = np.zeros((selected_df_w["unit"].n_unique(), selected_df_w["schedule"].n_unique()))
        for i in range(np.shape(w_array)[0]):
            for j in range(np.shape(w_array)[1]):
                if len(rows_by_key_df_key[(unique_units[i], j)]) == 0:
                    continue
                if (unique_units[i], j) in rows_by_key:
                    w_array[i][j] = rows_by_key[(unique_units[i], j)][0]

    selected_df_p = df.filter(pl.col("holding") == holding).select(
        ["unit", "schedule", "harvest_value_period_2025", "harvest_value_period_2030", "harvest_value_period_2035"]
    )
    selected_df_p.group_by(["unit", "schedule"])
    rows_by_key = selected_df_p.rows_by_key(key=["unit", "schedule"])
    p_array = np.zeros((selected_df_p["unit"].n_unique(), selected_df_p["schedule"].n_unique()))
    for i in range(np.shape(p_array)[0]):
        for j in range(np.shape(p_array)[1]):
            if (unique_units[i], j) in rows_by_key:
                p_array[i][j] = sum(rows_by_key[(unique_units[i], j)][0])

    constants = []
    variables = []
    constraints = []
    f_1_func = []
    f_2_func = []
    f_3_func = []
    # define the constants V, W and P, decision variable X, constraints, and objective function expressions in one loop
    for i in range(np.shape(v_array)[0]):
        # Constants V, W and P
        v = TensorConstant(
            name=f"V_{i+1}",
            symbol=f"V_{i+1}",
            shape=[np.shape(v_array)[1]],  # NOTE: vectors have to be of form [2] instead of [2,1] or [1,2]
            values=v_array[i].tolist(),
        )
        constants.append(v)
        w = TensorConstant(
            name=f"W_{i+1}",
            symbol=f"W_{i+1}",
            shape=[np.shape(w_array)[1]],  # NOTE: vectors have to be of form [2] instead of [2,1] or [1,2]
            values=w_array[i].tolist(),
        )
        constants.append(w)
        p = TensorConstant(
            name=f"P_{i+1}",
            symbol=f"P_{i+1}",
            shape=[np.shape(p_array)[1]],  # NOTE: vectors have to be of form [2] instead of [2,1] or [1,2]
            values=p_array[i].tolist(),
        )
        constants.append(p)

        # Decision variable X
        x = TensorVariable(
            name=f"X_{i+1}",
            symbol=f"X_{i+1}",
            variable_type=VariableTypeEnum.binary,
            shape=[np.shape(v_array)[1]],  # NOTE: vectors have to be of form [2] instead of [2,1] or [1,2]
            lowerbounds=np.shape(v_array)[1] * [0],
            upperbounds=np.shape(v_array)[1] * [1],
            initial_values=np.shape(v_array)[1] * [0],
        )
        variables.append(x)

        # Fill out the dict with information about treatments associated with X_{i+1}
        treatment_list = (
            df_key.filter((pl.col("holding") == holding) & (pl.col("unit") == unique_units[i]))
            .get_column("treatment")
            .to_list()
        )
        schedule_dict[f"X_{i+1}"] = dict(zip(range(len(treatment_list)), treatment_list, strict=True))
        schedule_dict[f"X_{i+1}"]["unit"] = unique_units[i]

        # Constraints
        con = Constraint(
            name=f"x_con_{i+1}", symbol=f"x_con_{i+1}", cons_type=ConstraintTypeEnum.EQ, func=f"Sum(X_{i+1}) - 1"
        )
        constraints.append(con)

        # Objective function expressions
        exprs = f"V_{i+1}@X_{i+1}"
        f_1_func.append(exprs)

        exprs = f"W_{i+1}@X_{i+1}"
        f_2_func.append(exprs)

        exprs = f"P_{i+1}@X_{i+1}"
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

    # This is so bad, but we currently don't have a better way
    ideals, nadirs = payoff_table_method(
        problem=Problem(
            name=problem_name,
            description="A test forest problem.",
            constants=constants,
            variables=variables,
            objectives=[f_1, f_2, f_3],
            constraints=constraints,
        ),
        solver=available_solvers["gurobipy"],
    )

    print(ideals)
    print(nadirs)

    f_1 = Objective(
        name="Net present value",
        symbol="f_1",
        func=f_1_func,
        maximize=True,
        ideal=math.ceil(ideals["f_1"]),
        nadir=math.floor(nadirs["f_1"]),
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
        ideal=math.ceil(ideals["f_2"]),
        nadir=math.floor(nadirs["f_2"]),
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
        ideal=math.ceil(ideals["f_3"]),
        nadir=math.floor(nadirs["f_3"]),
        objective_type=ObjectiveTypeEnum.analytical,
        is_linear=True,
        is_convex=False,  # not checked
        is_twice_differentiable=True,
    )

    return Problem(
        name=problem_name,
        description="A test forest problem.",
        constants=constants,
        variables=variables,
        objectives=[f_1, f_2, f_3],
        constraints=constraints,
    ), schedule_dict
