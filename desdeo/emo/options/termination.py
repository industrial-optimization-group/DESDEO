"""JSON Schema for termination operator options."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, model_validator

from desdeo.emo.operators.termination import (
    BaseTerminator,
    CompositeTerminator,
    ExternalCheckTerminator,
    MaxEvaluationsTerminator,
    MaxGenerationsTerminator,
    MaxTimeTerminator,
)

if TYPE_CHECKING:
    from desdeo.tools.patterns import Publisher


class MaxGenerationsTerminatorOptions(BaseModel):
    """Options for max generations terminator operator."""

    name: Literal["MaxGenerationsTerminator"] = Field(
        default="MaxGenerationsTerminator", frozen=True, description="The name of the termination operator."
    )
    """The name of the termination operator."""
    max_generations: int = Field(default=100, gt=0, description="The maximum number of generations allowed.")
    """The maximum number of generations allowed."""


class MaxEvaluationsTerminatorOptions(BaseModel):
    """Options for max evaluations terminator operator."""

    name: Literal["MaxEvaluationsTerminator"] = Field(
        default="MaxEvaluationsTerminator", frozen=True, description="The name of the termination operator."
    )
    """The name of the termination operator."""
    max_evaluations: int = Field(default=10000, gt=0, description="The maximum number of evaluations allowed.")
    """The maximum number of evaluations allowed."""


class MaxTimeTerminatorOptions(BaseModel):
    """Options for max time terminator operator."""

    name: Literal["MaxTimeTerminator"] = Field(
        default="MaxTimeTerminator", frozen=True, description="The name of the termination operator."
    )
    """The name of the termination operator."""
    max_time_in_seconds: float = Field(default=30.0, gt=0, description="The maximum time allowed (in seconds).")
    """The maximum time allowed (in seconds).

    Named to match `MaxTimeTerminator.__init__`, because `terminator_constructor` splats
    `model_dump()` as keyword arguments. It was `max_time` until that mismatch was found, which made
    every construction through this options model raise `TypeError`."""


class ExternalCheckTerminatorOptions(BaseModel):
    """Options for external check terminator operator. Note that the check function must be provided separately."""

    name: Literal["ExternalCheckTerminator"] = Field(
        default="ExternalCheckTerminator", frozen=True, description="The name of the termination operator."
    )
    """The name of the termination operator."""


class CompositeTerminatorOptions(BaseModel):
    """Options for composite terminator operator."""

    name: Literal["CompositeTerminator"] = Field(
        default="CompositeTerminator", frozen=True, description="The name of the termination operator."
    )
    """The name of the termination operator."""
    terminators: list[
        MaxEvaluationsTerminatorOptions
        | MaxGenerationsTerminatorOptions
        | MaxTimeTerminatorOptions
        | ExternalCheckTerminatorOptions
    ] = Field(default_factory=lambda: [MaxGenerationsTerminatorOptions()], description="List of terminators.")
    """List of terminators."""
    mode: Literal["all", "any"] = Field(default="any", description="Whether to use logical AND or OR.")
    """Whether to use logical AND or OR."""

    @model_validator(mode="after")
    def check_unique_terminator_types(self):
        """Ensure that all terminator types in the composite are unique."""
        types_seen = set()
        for term in self.terminators:
            t = type(term)
            if t in types_seen:
                raise ValueError(f"Duplicate terminator type: {t.__name__}")
            types_seen.add(t)
        return self


TerminatorOptions = (
    MaxGenerationsTerminatorOptions
    | MaxEvaluationsTerminatorOptions
    | MaxTimeTerminatorOptions
    | ExternalCheckTerminatorOptions
    | CompositeTerminatorOptions
)


def terminator_constructor(
    options: TerminatorOptions, publisher: Publisher, external_check: Callable | None = None
) -> BaseTerminator:
    """Construct a termination operator.

    Args:
        options (TerminatorOptions): Options for the termination operator.
        publisher (Publisher): Publisher instance for the termination operator.
        external_check (Callable | None, optional): External check function for the termination operator.
            Defaults to None. Only required if using ExternalCheckTerminator.

    Raises:
        ValueError: If the options are invalid.
        ValueError: If the external check function is required but not provided.

    Returns:
        BaseTerminator: Instance of the termination operator.
    """
    terminators = {
        "MaxGenerationsTerminator": MaxGenerationsTerminator,
        "MaxEvaluationsTerminator": MaxEvaluationsTerminator,
        "MaxTimeTerminator": MaxTimeTerminator,
        "ExternalCheckTerminator": ExternalCheckTerminator,
        "CompositeTerminator": CompositeTerminator,
    }
    # The composite recurses on its children, so it has to branch *before* `model_dump()`: dumping is
    # recursive, and a child turned into a plain dict has no `.model_dump()` for the recursive call
    # to reach.
    if options.name == "CompositeTerminator":
        sub_terminators = [terminator_constructor(child, publisher, external_check) for child in options.terminators]
        return CompositeTerminator(terminators=sub_terminators, publisher=publisher, mode=options.mode)

    fields: dict = options.model_dump()
    name = fields.pop("name")
    if name == "ExternalCheckTerminator":
        if external_check is None:
            raise ValueError("External check function must be provided for ExternalCheckTerminator.")
        return ExternalCheckTerminator(check_function=external_check, publisher=publisher, **fields)
    if name not in terminators:
        raise ValueError(f"Unknown terminator name: {name}")
    return terminators[name](publisher=publisher, **fields)
