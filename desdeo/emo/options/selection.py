"""JSON Schema for selection operator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from desdeo.emo.operators.selection import (
    BaseSelector,
    IBEASelector,
    NSGA2Selector,
    NSGA3Selector,
    ParameterAdaptationStrategy,
    ReferenceVectorOptions,
    RVEASelector,
    SMSEMOASelector,
)
from desdeo.tools.indicators_binary import self_epsilon, self_hv

if TYPE_CHECKING:
    from desdeo.problem import Problem
    from desdeo.tools.patterns import Publisher


class RVEASelectorOptions(BaseModel):
    """Options for RVEA Selection."""

    model_config = ConfigDict(use_enum_values=True)

    name: Literal["RVEASelector"] = Field(
        default="RVEASelector", frozen=True, description="The name of the selection operator."
    )
    """The name of the selection operator."""
    reference_vector_options: ReferenceVectorOptions = Field(
        default=ReferenceVectorOptions(), description="Options for the reference vectors."
    )
    """Options for the reference vectors."""
    parameter_adaptation_strategy: ParameterAdaptationStrategy = Field(
        default=ParameterAdaptationStrategy.GENERATION_BASED, description="The parameter adaptation strategy to use."
    )
    """Whether the angle penalized distance is adapted per generation or per function evaluation."""
    alpha: float = Field(default=2.0, gt=0.0, description="The alpha parameter in the angle penalized distance.")
    """The alpha parameter in the angle penalized distance."""


class NSGA3SelectorOptions(BaseModel):
    """Options for NSGA-III Selection."""

    name: Literal["NSGA3Selector"] = Field(
        default="NSGA3Selector", frozen=True, description="The name of the selection operator."
    )
    """The name of the selection operator."""
    reference_vector_options: ReferenceVectorOptions = Field(
        default=ReferenceVectorOptions(), description="Options for the reference vectors."
    )
    """Options for the reference vectors."""
    invert_reference_vectors: bool = Field(
        default=False, description="Whether to invert the reference vectors (inverted triangle)."
    )
    """Whether to invert the reference vectors (inverted triangle)."""


class NSGA2SelectorOptions(BaseModel):
    """Options for NSGA-II Selection."""

    name: Literal["NSGA2Selector"] = Field(
        default="NSGA2Selector", frozen=True, description="The name of the selection operator."
    )
    """The name of the selection operator."""
    population_size: int = Field(gt=0, description="The population size.")
    """The population size."""


class IBEASelectorOptions(BaseModel):
    """Options for IBEA Selection."""

    name: Literal["IBEASelector"] = Field(
        default="IBEASelector", frozen=True, description="The name of the selection operator."
    )
    """The name of the selection operator."""
    population_size: int = Field(gt=0, description="The population size.")
    """The population size."""
    kappa: float = Field(default=0.05, description="The kappa parameter for IBEA.")
    """The kappa parameter for IBEA."""
    binary_indicator: Literal["eps", "hv"] = Field(default="eps", description="The binary indicator for IBEA.")
    """The binary indicator for IBEA."""


class SMSEMOASelectorOptions(BaseModel):
    """Options for SMS-EMOA Selection."""

    name: Literal["SMSEMOASelector"] = Field(
        default="SMSEMOASelector", frozen=True, description="The name of the selection operator."
    )
    """The name of the selection operator."""
    population_size: int = Field(gt=0, description="The population size.")
    """The population size."""
    reference_point_offset: float = Field(
        default=1.0,
        gt=0.0,
        description=(
            "The offset added to the worst objective values of the worst-ranked front to build the dynamic "
            "reference point used in the hypervolume computation (for three or more objectives)."
        ),
    )
    """The offset for the dynamic reference point used in the hypervolume computation."""
    use_dominating_points: bool = Field(
        default=True,
        description=(
            "Whether to use the cheaper 'dominating points' variant when the population is not yet fully "
            "non-dominated (Algorithm 3 in the SMS-EMOA reference)."
        ),
    )
    """Whether to use the 'dominating points' variant for dominated solutions."""
    greedy_reduction: bool = Field(
        default=True,
        description=(
            "If True, discard individuals one at a time, recomputing hypervolume contributions after each removal "
            "(faithful, best quality). If False, remove the required number of least-contributing individuals in a "
            "single batch per front, which is much faster for four or more objectives at a small quality cost."
        ),
    )
    """Whether to remove individuals one at a time (greedy) or in a single batch per front."""


SelectorOptions = (
    RVEASelectorOptions | NSGA2SelectorOptions | NSGA3SelectorOptions | IBEASelectorOptions | SMSEMOASelectorOptions
)


def selection_constructor(
    problem: Problem, options: SelectorOptions, publisher: Publisher, verbosity: int, seed: int
) -> BaseSelector:
    """Construct a selection operator from given options.

    Args:
        problem (Problem): The optimization problem.
        options (SelectorOptions): The options for the selection operator.
        publisher (Publisher): The publisher to use for the operator.
        verbosity (int): The verbosity level.
        seed (int): The random seed.

    Returns:
        BaseSelector: The constructed selection operator.

    Raises:
        ValueError: If an unknown selection operator name is provided.
    """
    selection_types = {
        "RVEASelector": RVEASelector,
        "NSGA2Selector": NSGA2Selector,
        "NSGA3Selector": NSGA3Selector,
        "IBEASelector": IBEASelector,
        "SMSEMOASelector": SMSEMOASelector,
    }
    options: dict = options.model_dump()
    name = options.pop("name")
    if name == "IBEASelector":
        indi = options.pop("binary_indicator")
        match indi:
            case "eps":
                options["binary_indicator"] = self_epsilon
            case "hv":
                options["binary_indicator"] = self_hv
            case _:
                raise ValueError(f"Unknown binary indicator: {indi}")
    return selection_types[name](problem=problem, publisher=publisher, seed=seed, verbosity=verbosity, **options)
