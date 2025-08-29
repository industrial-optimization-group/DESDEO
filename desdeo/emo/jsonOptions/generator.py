"""JSON Schema for generator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from desdeo.emo.operators.generator import (
    BaseGenerator,
    LHSGenerator,
    RandomBinaryGenerator,
    RandomGenerator,
    RandomIntegerGenerator,
    RandomMixedIntegerGenerator,
)

if TYPE_CHECKING:
    from desdeo.problem import Problem
    from desdeo.tools.patterns import Publisher


class BaseGeneratorOptions(BaseModel):
    """Options for all generators."""

    n_points: int = Field(gt=0, description="The number of points to generate for the initial population.")
    """The number of points to generate for the initial population."""


class LHSGeneratorOptions(BaseGeneratorOptions):
    """Options for Latin Hypercube Sampling (LHS) generator."""

    name: Literal["LHSGenerator"] = Field(default="LHSGenerator", frozen=True, description="The name of the generator.")
    """The name of the generator."""


class RandomBinaryGeneratorOptions(BaseGeneratorOptions):
    """Options for Random Binary generator."""

    name: Literal["RandomBinaryGenerator"] = Field(
        default="RandomBinaryGenerator", frozen=True, description="The name of the generator."
    )
    """The name of the generator."""


class RandomGeneratorOptions(BaseGeneratorOptions):
    """Options for Random generator."""

    name: Literal["RandomGenerator"] = Field(
        default="RandomGenerator", frozen=True, description="The name of the generator."
    )
    """The name of the generator."""


class RandomIntegerGeneratorOptions(BaseGeneratorOptions):
    """Options for Random Integer generator."""

    name: Literal["RandomIntegerGenerator"] = Field(
        default="RandomIntegerGenerator", frozen=True, description="The name of the generator."
    )
    """The name of the generator."""


class RandomMixedIntegerGeneratorOptions(BaseGeneratorOptions):
    """Options for Random Mixed Integer generator."""

    name: Literal["RandomMixedIntegerGenerator"] = Field(
        default="RandomMixedIntegerGenerator", frozen=True, description="The name of the generator."
    )
    """The name of the generator."""


GeneratorOptions = (
    LHSGeneratorOptions
    | RandomBinaryGeneratorOptions
    | RandomGeneratorOptions
    | RandomIntegerGeneratorOptions
    | RandomMixedIntegerGeneratorOptions
)


def generator_constructor(
    problem: Problem, options: GeneratorOptions, publisher: Publisher, verbosity: int, seed: int
) -> BaseGenerator:
    """Construct a generator based on the provided options.

    Args:
        problem (Problem): The optimization problem to solve.
        options (GeneratorOptions): The options for the generator.
        publisher (Publisher): The publisher for the generator.
        verbosity (int): The verbosity level for the generator.
        seed (int): The random seed for the generator.

    Returns:
        BaseGenerator: The constructed generator.
    """
    generator_types = {
        "LHSGenerator": LHSGenerator,
        "RandomBinaryGenerator": RandomBinaryGenerator,
        "RandomGenerator": RandomGenerator,
        "RandomIntegerGenerator": RandomIntegerGenerator,
        "RandomMixedIntegerGenerator": RandomMixedIntegerGenerator,
    }
    options = options.model_dump()
    name = options.pop("name")
    return generator_types[name](problem, **options, publisher=publisher, verbosity=verbosity, seed=seed)
