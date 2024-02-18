"""Fixtures used across tests are defined here."""
import polars as pl
import pytest

from desdeo.problem import Problem, Variable, VariableTypeEnum, Objective, ObjectiveTypeEnum, DiscreteDefinition


@pytest.fixture
def dtlz2_5x_3f_data_based():
    n_var = 5
    n_obj = 3

    df = pl.read_csv("./tests/data/DTLZ2_5x_3f.csv")

    variables = [
        Variable(
            name=f"x{i}",
            symbol=f"x{i}",
            lowerbound=0.0,
            upperbound=1.0,
            initial_value=1.0,
            variable_type=VariableTypeEnum.real,
        )
        for i in range(1, n_var + 1)
    ]

    objectives = [
        Objective(
            name=f"f{i}",
            symbol=f"f{i}",
            func=None,
            maximize=False,
            ideal=0,
            nadir=1.0,
            objective_type=ObjectiveTypeEnum.data_based,
        )
        for i in range(1, n_obj + 1)
    ]

    variable_dict = df[[f"f{i}" for i in range(1, n_obj + 1)]].to_dict(as_series=False)
    objective_dict = df[[f"x{i}" for i in range(1, n_var + 1)]].to_dict(as_series=False)

    return Problem(
        name="DTLZ2",
        description="DTLZ2 with 5 vars and 3 objs, representation.",
        variables=variables,
        objectives=objectives,
        discrete_definition=DiscreteDefinition(variable_values=variable_dict, objective_values=objective_dict),
    )
