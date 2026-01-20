"""A forest problem with discrete representation."""
from pathlib import Path

import polars as pl

from desdeo.problem.schema import (
    DiscreteRepresentation,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)


def dmitry_forest_problem_disc() -> Problem:
    """Implements the dmitry forest problem using Pareto front representation.

    Returns:
        Problem: A problem instance representing the forest problem.
    """
    path = Path(__file__)
    while not str(path).endswith("/DESDEO"):
        path = path.parent

    path = path / "tests/data/dmitry_discrete_repr/dmitry_forest_problem_non_dom_solns.csv"

    obj_names = ["Rev", "HA", "Carb", "DW"]

    var_name = "index"

    data = pl.read_csv(
        path, has_header=True, columns=["Rev", "HA", "Carb", "DW"], separator=",", #decimal_comma=True
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
        name="Dmitry Forest Problem (Discrete)",
        description="Defines a forest problem with four objectives: revenue, habitat availability, carbon storage, and deadwood.",
        variables=variables,
        objectives=objectives,
        discrete_representation=discrete_def,
        is_twice_differentiable=False,
    )
