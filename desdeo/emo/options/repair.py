"""JSON Schema for repair operator options."""

from collections.abc import Callable
from typing import Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from desdeo.problem import Problem
from desdeo.tools.utils import repair


class NoRepairOptions(BaseModel):
    """Options for No Repair."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: Literal["NoRepair"] = Field(default="NoRepair")
    """Do not apply any repair to the solutions."""


class ClipRepairOptions(BaseModel):
    """Options for Clip Repair."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: Literal["ClipRepair"] = Field(default="ClipRepair")
    """Clip the solutions to be within the variable bounds."""

    lower_bounds: dict[str, float] | None = None
    """Lower bounds for the decision variables. If none, the lower bounds from the problem will be used."""
    upper_bounds: dict[str, float] | None = None
    """Upper bounds for the decision variables. If none, the upper bounds from the problem will be used."""


RepairOptions = ClipRepairOptions | NoRepairOptions


def repair_constructor(options: RepairOptions, problem: Problem) -> Callable[[pl.DataFrame], pl.DataFrame]:
    """Get the repair operator based on the provided options.

    Args:
        options (RepairOptions): The repair options.
        problem (Problem): The optimization problem to solve.

    Returns:
        callable: The repair operator function.
    """
    if options.name == "NoRepair":
        return lambda x: x  # No repair, return input as is
    if options.name == "ClipRepair":
        if options.lower_bounds is None:
            lower_bounds = {var.symbol: var.lowerbound for var in problem.get_flattened_variables()}
        else:
            lower_bounds = options.lower_bounds
        if options.upper_bounds is None:
            upper_bounds = {var.symbol: var.upperbound for var in problem.get_flattened_variables()}
        else:
            upper_bounds = options.upper_bounds
        return repair(lower_bounds=lower_bounds, upper_bounds=upper_bounds)
    raise ValueError(f"Unknown repair operator: {options.name}")
