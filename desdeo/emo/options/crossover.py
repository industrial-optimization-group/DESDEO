"""JSON Schema for crossover operator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from desdeo.emo.operators.crossover import (
    BaseCrossover,
    BlendAlphaCrossover,
    BoundedExponentialCrossover,
    CompositeCrossover,
    DifferentialEvolutionCrossover,
    LocalCrossover,
    ParentCentricCrossover,
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
    pair_xover_probability: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Probability that a parent pair is recombined at all."
    )
    """Probability that a parent pair is recombined at all, drawn once per pair. On failure the pair is
    copied to the offspring unchanged, with all of its decision variables kept together. This is the
    `p_c` reported in the literature: 1.0 in the RVEA and NSGA-III papers, 0.9 in NSGA-II."""
    xover_probability: float = Field(
        default=0.5, ge=0.0, le=1.0, description="The per-variable SBX crossover probability."
    )
    """The per-variable SBX crossover probability, drawn once per decision variable. Defaults to 0.5,
    following Deb and Agrawal (1995): "we choose to perform SBX in each variable with probability 0.5".
    This is a separate level from `pair_xover_probability`; the literature's `p_c` refers to the pair,
    not to the variable, and belongs in `pair_xover_probability`."""
    xover_distribution: float = Field(default=30.0, gt=0.0, description="The SBX distribution index.")
    """The SBX distribution index."""
    truncated: bool = Field(
        default=True,
        description=(
            "Whether to truncate the probability distribution to keep the offspring within the variable bounds."
        ),
    )
    """Whether to truncate the probability distribution to keep the offspring within the variable bounds."""
    uniform_xover_probability: float = Field(
        default=0.5, ge=0.0, le=1.0, description="The uniform crossover probability."
    )
    """The uniform crossover probability. Only operates on variables that have already been selected for crossover
    by the xover_probability parameter."""
    swap_uncrossed_variables: bool = Field(
        default=False,
        description=(
            "Whether a decision variable not selected for SBX is exchanged between the two offspring "
            "instead of inherited unchanged. Set only to reproduce jMetal (Java)."
        ),
    )
    """Whether a decision variable not selected by `xover_probability` is exchanged between the two offspring
    instead of inherited unchanged. Defaults to False, which is what every implementation surveyed does except
    jMetal (Java), whose else-branch assigns `offspring1[i] = parent2[i]` and `offspring2[i] = parent1[i]`.
    That adds a genuine uniform-crossover component on top of SBX: at the standard per-variable rate of 0.5,
    half of the genome is swapped wholesale every time a pair recombines."""


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

    model_config = {"use_attribute_docstrings": True}

    name: Literal["BlendAlphaCrossover"] = Field(
        default="BlendAlphaCrossover",
        frozen=True,
    )
    """The name of the crossover operator."""
    alpha: float = Field(default=0.5, ge=0.0)
    """
    Non-negative blending factor 'alpha' that controls the extent to which offspring
    may be sampled outside the interval defined by each pair of parent genes.
    alpha = 0 restricts children strictly within the parents range, larger alpha allows outliers.
    """
    repeats: int = Field(default=2, ge=1)
    """Number of offspring to generate per parent pair."""
    sample_each_component: bool = Field(
        default=True,
    )
    """If True, a new random number is generated for each component of the offspring. If False, a single random number
    is generated for the entire offspring."""


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


class BoundedExponentialCrossoverOptions(BaseModel):
    """Options for Bounded Exponential Crossover."""

    name: Literal["BoundedExponentialCrossover"] = Field(
        default="BoundedExponentialCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    xover_probability: float = Field(default=1.0, ge=0.0, le=1.0, description="The crossover probability.")
    """The crossover probability."""
    lambda_: float = Field(default=0.1, gt=0.0, description="Positive scale λ for the exponential distribution.")
    """Positive scale λ for the exponential distribution."""
    uniform_xover_probability: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Per-variable probability that the two offspring exchange which parent they descend from. "
            "0.0 keeps the operator's original behaviour, where each offspring keeps its own parent's "
            "identity in every variable."
        ),
    )
    """Per-variable probability that the two offspring exchange which parent they descend from.

    Defaults to 0.0, the operator's original behaviour. The same parameter on
    `SimulatedBinaryCrossoverOptions` defaults to 0.5 and separates that operator's two arms by 10.9x
    in median regret, so this is worth varying; the default stays at 0.0 because BEX is parent centric
    by construction and the transfer has not been measured."""


class DifferentialEvolutionCrossoverOptions(BaseModel):
    """Options for Differential Evolution crossover (DE/rand/1/bin)."""

    name: Literal["DifferentialEvolutionCrossover"] = Field(
        default="DifferentialEvolutionCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    scaling_factor: float = Field(default=0.5, gt=0.0, description="The factor F applied to the difference vector.")
    """The factor `F` applied to the difference vector `x_r2 - x_r3`. Defaults to 0.5, the midpoint of
    the 0.4-1.0 range Storn and Price recommend."""
    xover_probability: float = Field(default=0.9, ge=0.0, le=1.0, description="The binomial crossover rate CR.")
    """The binomial crossover rate `CR`: the per-component probability that the offspring takes the
    mutant's value rather than the target's. One component is always taken from the mutant regardless,
    so no offspring is a copy of its target even at 0.0."""


class ParentCentricCrossoverOptions(BaseModel):
    """Options for Parent-Centric Crossover (PCX)."""

    name: Literal["ParentCentricCrossover"] = Field(
        default="ParentCentricCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    sigma_zeta: float = Field(
        default=0.1, gt=0.0, description="Standard deviation along the centroid-to-parent direction."
    )
    """Standard deviation of the displacement along the direction from the parental centroid to the
    index parent. Defaults to 0.1, the value used throughout Deb, Anand and Joshi (2002)."""
    sigma_eta: float = Field(default=0.1, gt=0.0, description="Standard deviation orthogonal to that direction.")
    """Standard deviation of the displacement orthogonal to the centroid-to-parent direction, in units
    of the mean perpendicular distance of the other parents. Defaults to 0.1."""


class CompositeCrossoverOptions(BaseModel):
    """Options for Composite Crossover."""

    name: Literal["CompositeCrossover"] = Field(
        default="CompositeCrossover", frozen=True, description="The name of the crossover operator."
    )
    """The name of the crossover operator."""
    crossovers: list[CrossoverOptions] = Field(
        default_factory=list,
        description="List of crossover options to be used in the composite crossover.",
    )
    """List of crossover options to be used in the composite crossover."""


CrossoverOptions = (
    SimulatedBinaryCrossoverOptions
    | SinglePointBinaryCrossoverOptions
    | UniformIntegerCrossoverOptions
    | UniformMixedIntegerCrossoverOptions
    | BlendAlphaCrossoverOptions
    | SingleArithmeticCrossoverOptions
    | LocalCrossoverOptions
    | BoundedExponentialCrossoverOptions
    | DifferentialEvolutionCrossoverOptions
    | ParentCentricCrossoverOptions
    | CompositeCrossoverOptions
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
        "DifferentialEvolutionCrossover": DifferentialEvolutionCrossover,
        "ParentCentricCrossover": ParentCentricCrossover,
        "CompositeCrossover": CompositeCrossover,
    }
    if options.name != "CompositeCrossover":
        options = options.model_dump()
        name = options.pop("name")
        return crossover_types[name](problem=problem, publisher=publisher, seed=seed, verbosity=verbosity, **options)

    sub_crossovers = [crossover_constructor(problem, publisher, seed, verbosity, c) for c in options.crossovers]
    return CompositeCrossover(
        problem=problem, publisher=publisher, verbosity=verbosity, operators=sub_crossovers, seed=seed
    )
