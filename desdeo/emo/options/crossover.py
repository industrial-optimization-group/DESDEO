"""JSON Schema for crossover operator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from desdeo.emo.operators.crossover import (
    BaseCrossover,
    BlendAlphaCrossover,
    BoundedExponentialCrossover,
    LocalCrossover,
    SimulatedBinaryCrossover,
    SingleArithmeticCrossover,
    SinglePointBinaryCrossover,
    UniformIntegerCrossover,
    UniformMixedIntegerCrossover,
)

if TYPE_CHECKING:
    from desdeo.problem import Problem
    from desdeo.tools.patterns import Publisher


class SimulatedBinaryCrossoverOptions(BaseModel):
    """Options for Simulated Binary Crossover (SBX)."""

    name: Literal["SimulatedBinaryCrossover"] = Field(
        default="SimulatedBinaryCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    xover_probability: float = Field(default=0.5, ge=0.0, le=1.0, description="The SBX crossover probability.")
    """The SBX crossover probability."""
    xover_distribution: float = Field(default=30.0, gt=0.0, description="The SBX distribution index.")
    """The SBX distribution index."""


class SinglePointBinaryCrossoverOptions(BaseModel):
    """Options for Single Point Binary Crossover."""

    name: Literal["SinglePointBinaryCrossover"] = Field(
        default="SinglePointBinaryCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""


class UniformIntegerCrossoverOptions(BaseModel):
    """Options for Uniform Integer Crossover."""

    name: Literal["UniformIntegerCrossover"] = Field(
        default="UniformIntegerCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""


class UniformMixedIntegerCrossoverOptions(BaseModel):
    """Options for Uniform Mixed Integer Crossover."""

    name: Literal["UniformMixedIntegerCrossover"] = Field(
        default="UniformMixedIntegerCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""


class BlendAlphaCrossoverOptions(BaseModel):
    """Options for Blend Alpha Crossover."""

    name: Literal["BlendAlphaCrossover"] = Field(
        default="BlendAlphaCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    alpha: float = Field(
        default=0.5,
        ge=0.0,
        description=(
            "Non-negative blending factor 'alpha' that controls the extent to which offspring"
            " may be sampled outside the interval defined by each pair of parent genes. "
            "alpha = 0 restricts children strictly within the parents range, larger alpha allows some outliers."
        ),
    )
    """
    Non-negative blending factor 'alpha' that controls the extent to which offspring
    may be sampled outside the interval defined by each pair of parent genes.
    alpha = 0 restricts children strictly within the parents range, larger alpha allows some outliers.
    """
    xover_probability: float = Field(default=1.0, ge=0.0, le=1.0)


class SingleArithmeticCrossoverOptions(BaseModel):
    """Options for Single Arithmetic Crossover."""

    name: Literal["SingleArithmeticCrossover"] = Field(
        default="SingleArithmeticCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    xover_probability: float = Field(default=1.0, ge=0.0, le=1.0, description="The crossover probability.")
    """The crossover probability."""


class LocalCrossoverOptions(BaseModel):
    """Options for Local Crossover."""

    name: Literal["LocalCrossover"] = Field(
        default="LocalCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    xover_probability: float = Field(default=1.0, ge=0.0, le=1.0, description="The crossover probability.")
    """The crossover probability."""


class BoundedExponentialCrossoverOptions(BaseModel):
    """Options for Bounded Exponential Crossover."""

    name: Literal["BoundedExponentialCrossover"] = Field(
        default="BoundedExponentialCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    xover_probability: float = Field(default=1.0, ge=0.0, le=1.0, description="The crossover probability.")
    """The crossover probability."""
    lambda_: float = Field(default=1.0, gt=0.0, description="Positive scale λ for the exponential distribution.")
    """Positive scale λ for the exponential distribution."""


CrossoverOptions = (
    SimulatedBinaryCrossoverOptions
    | SinglePointBinaryCrossoverOptions
    | UniformIntegerCrossoverOptions
    | UniformMixedIntegerCrossoverOptions
    | BlendAlphaCrossoverOptions
    | SingleArithmeticCrossoverOptions
    | LocalCrossoverOptions
    | BoundedExponentialCrossoverOptions
)


def crossover_constructor(
    problem: Problem, publisher: Publisher, seed: int, verbosity: int, options: CrossoverOptions
) -> BaseCrossover:
    """Construct a crossover operator.

    Args:
        problem (Problem): The optimization problem to solve.
        publisher (Publisher): The publisher for communication.
        seed (int): The random seed for reproducibility.
        verbosity (int): The verbosity level of the output.
        options (CrossoverOptions): The options for the crossover operator.

    Returns:
        BaseCrossover: The constructed crossover operator.
    """
    crossover_types = {
        "SimulatedBinaryCrossover": SimulatedBinaryCrossover,
        "SinglePointBinaryCrossover": SinglePointBinaryCrossover,
        "UniformIntegerCrossover": UniformIntegerCrossover,
        "UniformMixedIntegerCrossover": UniformMixedIntegerCrossover,
        "BlendAlphaCrossover": BlendAlphaCrossover,
        "SingleArithmeticCrossover": SingleArithmeticCrossover,
        "LocalCrossover": LocalCrossover,
        "BoundedExponentialCrossover": BoundedExponentialCrossover,
    }
    options = options.model_dump()
    name = options.pop("name")
    return crossover_types[name](problem=problem, publisher=publisher, seed=seed, verbosity=verbosity, **dict(options))
