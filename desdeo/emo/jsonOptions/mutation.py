"""JSON Schema for mutation operator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from desdeo.emo.operators.crossover import SimulatedBinaryCrossover
from desdeo.emo.operators.mutation import (
    BaseMutation,
    BoundedPolynomialMutation,
    BinaryFlipMutation,
    IntegerRandomMutation,
    MixedIntegerRandomMutation,
    MPTMutation,
    NonUniformMutation,
    SelfAdaptiveGaussianMutation,
    PowerMutation,
)

if TYPE_CHECKING:
    from desdeo.problem import Problem
    from desdeo.tools.patterns import Publisher


class BoundedPolynomialMutationOptions(BaseModel):
    """Options for Bounded Polynomial Mutation."""

    name: Literal["BoundedPolynomialMutation"] = Field(
        default="BoundedPolynomialMutation", frozen=True, description="The name of the mutation operator."
    )
    """The name of the mutation operator."""
    mutation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The probability of mutation. Defaults to None, which sets the "
            "mutation probability to 1/<number of decision variables>."
        ),
    )
    """
    The probability of mutation. Defaults to None, which sets the mutation probability to
    1/<number of decision variables>.
    """
    distribution_index: float = Field(default=20.0, gt=0.0, description="The distribution index.")
    """The distribution index."""


class BinaryFlipMutationOptions(BaseModel):
    """Options for Binary Flip Mutation."""

    name: Literal["BinaryFlipMutation"] = Field(
        default="BinaryFlipMutation", frozen=True, description="The name of the mutation operator."
    )
    """The name of the mutation operator."""
    mutation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The probability of mutation. Defaults to None, which sets the "
            "mutation probability to 1/<number of decision variables>."
        ),
    )
    """
    The probability of mutation. Defaults to None, which sets the mutation probability to
    1/<number of decision variables>.
    """


class IntegerRandomMutationOptions(BaseModel):
    """Options for Integer Random Mutation."""

    name: Literal["IntegerRandomMutation"] = Field(
        default="IntegerRandomMutation", frozen=True, description="The name of the mutation operator."
    )
    """The name of the mutation operator."""
    mutation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The probability of mutation. Defaults to None, which sets the "
            "mutation probability to 1/<number of decision variables>."
        ),
    )
    """
    The probability of mutation. Defaults to None, which sets the mutation probability to
    1/<number of decision variables>.
    """


class MixedIntegerRandomMutationOptions(BaseModel):
    """Options for Mixed Integer Random Mutation."""

    name: Literal["MixedIntegerRandomMutation"] = Field(
        default="MixedIntegerRandomMutation", frozen=True, description="The name of the mutation operator."
    )
    """The name of the mutation operator."""
    mutation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The probability of mutation. Defaults to None, which sets the "
            "mutation probability to 1/<number of decision variables>."
        ),
    )
    """
    The probability of mutation. Defaults to None, which sets the mutation probability to
    1/<number of decision variables>.
    """


class MPTMutationOptions(BaseModel):
    """Options for MPT Mutation."""

    name: Literal["MPTMutation"] = Field(
        default="MPTMutation", frozen=True, description="The name of the mutation operator."
    )
    """The name of the mutation operator."""
    mutation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The probability of mutation. Defaults to None, which sets the "
            "mutation probability to 1/<number of decision variables>."
        ),
    )
    """
    The probability of mutation. Defaults to None, which sets the mutation probability to
    1/<number of decision variables>.
    """
    mutation_exponent: float = Field(
        default=2.0, ge=0.0, description="Controls strength of small mutation (larger means smaller mutations)."
    )
    """Controls strength of small mutation (larger means smaller mutations)."""


class NonUniformMutationOptions(BaseModel):
    """Options for Non-Uniform Mutation."""

    name: Literal["NonUniformMutation"] = Field(
        default="NonUniformMutation", frozen=True, description="The name of the mutation operator."
    )
    """The name of the mutation operator."""
    mutation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The probability of mutation. Defaults to None, which sets the "
            "mutation probability to 1/<number of decision variables>."
        ),
    )
    """
    The probability of mutation. Defaults to None, which sets the mutation probability to
    1/<number of decision variables>.
    """
    max_generations: int = Field(
        gt=0, description="Maximum number of generations in the evolutionary run. Used to scale mutation decay."
    )
    b: float = Field(
        default=5.0,
        ge=0.0,
        description=(
            "Non-uniform mutation decay parameter. Higher values cause"
            "faster reduction in mutation strength over generations."
        ),
    )
    """Non-uniform mutation decay parameter. Higher values cause
    faster reduction in mutation strength over generations."""


class SelfAdaptiveGaussianMutationOptions(BaseModel):
    """Options for Self-Adaptive Gaussian Mutation."""

    name: Literal["SelfAdaptiveGaussianMutation"] = Field(
        default="SelfAdaptiveGaussianMutation", frozen=True, description="The name of the mutation operator."
    )
    """The name of the mutation operator."""
    mutation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The probability of mutation. Defaults to None, which sets the "
            "mutation probability to 1/<number of decision variables>."
        ),
    )
    """
    The probability of mutation. Defaults to None, which sets the mutation probability to
    1/<number of decision variables>.
    """


class PowerMutationOptions(BaseModel):
    """Options for Power Mutation."""

    name: Literal["PowerMutation"] = Field(
        default="PowerMutation", frozen=True, description="The name of the mutation operator."
    )
    """The name of the mutation operator."""
    mutation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The probability of mutation. Defaults to None, which sets the "
            "mutation probability to 1/<number of decision variables>."
        ),
    )
    """
    The probability of mutation. Defaults to None, which sets the mutation probability to
    1/<number of decision variables>.
    """
    p: float = Field(
        default=1.5, ge=0.0, description="Power distribution parameter. Controls the perturbation magnitude."
    )
    """Power distribution parameter. Controls the perturbation magnitude."""


MutationOptions = (
    BoundedPolynomialMutationOptions
    | BinaryFlipMutationOptions
    | IntegerRandomMutationOptions
    | MixedIntegerRandomMutationOptions
    | MPTMutationOptions
    | NonUniformMutationOptions
    | SelfAdaptiveGaussianMutationOptions
    | PowerMutationOptions
)


def mutation_constructor(
    problem: Problem, publisher: Publisher, seed: int, verbosity: int, options: MutationOptions
) -> BaseMutation:
    """Construct a mutation operator.

    Args:
        problem (Problem): The optimization problem to solve.
        publisher (Publisher): The publisher for communication.
        seed (int): The random seed for reproducibility.
        verbosity (int): The verbosity level of the output.
        options (MutationOptions): The options for the mutation operator.

    Returns:
        BaseCrossover: The constructed crossover operator.
    """
    mutation_types = {
        "BoundedPolynomialMutation": BoundedPolynomialMutation,
        "BinaryFlipMutation": BinaryFlipMutation,
        "IntegerRandomMutation": IntegerRandomMutation,
        "MixedIntegerRandomMutation": MixedIntegerRandomMutation,
        "MPTMutation": MPTMutation,
        "NonUniformMutation": NonUniformMutation,
        "SelfAdaptiveGaussianMutation": SelfAdaptiveGaussianMutation,
        "PowerMutation": PowerMutation,
    }
    options = options.model_dump()
    name = options.pop("name")
    return mutation_types[name](problem=problem, publisher=publisher, seed=seed, verbosity=verbosity, **dict(options))
