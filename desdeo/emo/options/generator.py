"""JSON Schema for generator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import polars as pl
from pydantic import BaseModel, Field

from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import (
    ArchiveGenerator,
    BaseGenerator,
    LHSGenerator,
    RandomBinaryGenerator,
    RandomGenerator,
    RandomIntegerGenerator,
    RandomMixedIntegerGenerator,
    SeededHybridGenerator,
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


class ArchiveGeneratorOptions(BaseModel):
    """Options for Archive generator."""

    model_config = {"arbitrary_types_allowed": True, "use_attribute_docstrings": True}

    name: Literal["ArchiveGenerator"] = "ArchiveGenerator"
    """The name of the generator."""
    solutions: pl.DataFrame
    """The initial solutions to populate the archive with."""
    outputs: pl.DataFrame
    """The corresponding outputs of the initial solutions."""


class SeededHybridGeneratorOptions(BaseGeneratorOptions):
    """Options for the seeded hybrid generator."""

    name: Literal["SeededHybridGenerator"] = Field(default="SeededHybridGenerator", frozen=True)
    model_config = {"arbitrary_types_allowed": True, "use_attribute_docstrings": True}

    seed_solution: pl.DataFrame
    """A dataframe with a single row representing the solution seed. The columns
    must math the symbols of the variables in the problem being solved.
    """
    perturb_fraction: float = Field(default=0.2, ge=0.0, le=1.0)
    """The desired fraction of perturbed vs random solutions in the generated population."""

    sigma: float = Field(default=0.02, ge=0.0)
    """The relative perturbation scale with respect to variable ranges."""

    flip_prob: float = Field(default=0.1, ge=0.0, le=1.0)
    """The flipping probability when perturbing binary variables."""


GeneratorOptions = (
    LHSGeneratorOptions
    | RandomBinaryGeneratorOptions
    | RandomGeneratorOptions
    | RandomIntegerGeneratorOptions
    | RandomMixedIntegerGeneratorOptions
    | ArchiveGeneratorOptions
    | SeededHybridGeneratorOptions
)


def generator_constructor(
    problem: Problem,
    options: GeneratorOptions,
    publisher: Publisher,
    verbosity: int,
    seed: int,
    evaluator: EMOEvaluator,
) -> BaseGenerator:
    """Construct a generator based on the provided options.

    Args:
        problem (Problem): The optimization problem to solve.
        options (GeneratorOptions): The options for the generator.
        publisher (Publisher): The publisher for the generator.
        verbosity (int): The verbosity level for the generator.
        seed (int): The random seed for the generator.
        evaluator (EMOEvaluator): The evaluator to use for evaluating solutions.

    Returns:
        BaseGenerator: The constructed generator.
    """
    generator_types = {
        "LHSGenerator": LHSGenerator,
        "RandomBinaryGenerator": RandomBinaryGenerator,
        "RandomGenerator": RandomGenerator,
        "RandomIntegerGenerator": RandomIntegerGenerator,
        "RandomMixedIntegerGenerator": RandomMixedIntegerGenerator,
        "ArchiveGenerator": ArchiveGenerator,
        "SeededHybridGenerator": SeededHybridGenerator,
    }
    options: dict = options.model_dump()
    name = options.pop("name")
    return generator_types[name](
        problem, **options, publisher=publisher, verbosity=verbosity, seed=seed, evaluator=evaluator
    )
