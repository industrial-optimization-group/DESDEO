"""JSON Schema for termination operator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from desdeo.emo.operators.termination import (
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
    max_time: float = Field(default=30.0, gt=0, description="The maximum time allowed (in seconds).")
    """The maximum time allowed (in seconds)."""


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
        MaxEvaluationsTerminatorOptions,
        MaxGenerationsTerminatorOptions,
        MaxTimeTerminatorOptions,
        ExternalCheckTerminatorOptions,
    ] = Field(default_factory=lambda: [MaxGenerationsTerminatorOptions()], description="List of terminators.")
    """List of terminators."""
    mode: Literal["all", "any"] = Field(default="any", description="Whether to use logical AND or OR.")
    """Whether to use logical AND or OR."""


TerminatorOptions = (
    MaxGenerationsTerminatorOptions
    | MaxEvaluationsTerminatorOptions
    | MaxTimeTerminatorOptions
    | ExternalCheckTerminatorOptions
    | CompositeTerminatorOptions
)


def terminator_constructor(options: TerminatorOptions, publisher: Publisher, external_check: callable = None):
    terminators = {
        "MaxGenerationsTerminator": MaxGenerationsTerminator,
        "MaxEvaluationsTerminator": MaxEvaluationsTerminator,
        "MaxTimeTerminator": MaxTimeTerminator,
        "ExternalCheckTerminator": ExternalCheckTerminator,
        "CompositeTerminator": CompositeTerminator,
    }
    options = options.model_dump()
    name = options.pop("name")
    if name not in ("ExternalCheckTerminator", "CompositeTerminator"):
        return terminators[name](publisher=publisher, **options)
    if name == "ExternalCheckTerminator":
        if external_check is None:
            raise ValueError("External check function must be provided for ExternalCheckTerminator.")
        return terminators[name](external_check=external_check, **options)
    if name == "CompositeTerminator":
        sub_terminators = []
        for term_options in options.pop("terminators"):
            sub_name = term_options.pop("name")
            sub_terminators.append(terminators[sub_name](publisher=publisher, **term_options))
        return CompositeTerminator(terminators=sub_terminators, publisher=publisher, mode=options.mode)
    raise ValueError(f"Unknown terminator name: {name}")
