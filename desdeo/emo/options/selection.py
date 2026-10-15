"""JSON Schema for selection operator options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from desdeo.emo.operators.selection import (
    BaseSelector,
    IBEASelector,
    MOEADSelector,
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

    model_config = {"use_attribute_docstrings": True}

    name: Literal["SMSEMOASelector"] = Field(default="SMSEMOASelector", frozen=True)
    """The name of the selection operator."""
    normalised_reference_point_component: float = Field(default=2, gt=1.0)
    """The reference point component used for hypervolume calculation.
    The solutions are normalized to the range [0, 1] and the reference point is set to a vector of ones multiplied by
    this component."""


class MOEADSelectorOptions(BaseModel):
    """Options for the MOEA/D selector.

    Only `TemplateMOEADOptions` takes this selector, since its replacement works one offspring at a
    time inside the MOEA/D loop. It is therefore not a member of `SelectorOptions`.
    """

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: Literal["MOEADSelector"] = Field(
        default="MOEADSelector", frozen=True, description="The name of the selection operator."
    )
    """The name of the selection operator."""
    reference_vector_options: ReferenceVectorOptions = Field(
        default=ReferenceVectorOptions(vector_type="planar"), description="Options for the weight vectors."
    )
    """Options for the weight vectors. Their number is the population size. The vectors are always
    normalized to sum to one, whatever `vector_type` says."""
    neighbourhood_size: int = Field(default=20, ge=2, description="The neighbourhood size T.")
    """The neighbourhood size `T`: how many of the closest weight vectors, the subproblem's own
    included, form a subproblem's neighbourhood."""
    neighbourhood_probability: float = Field(
        default=1.0, ge=0.0, le=1.0, description="The probability delta of mating within the neighbourhood."
    )
    """The probability `delta` that the mating pool and the replacement range are the neighbourhood
    rather than the whole population. 1.0 in the original MOEA/D, 0.9 in MOEA/D-DE."""
    max_replacements: int | None = Field(
        default=None, ge=1, description="The maximum number n_r of solutions one offspring may replace."
    )
    """The maximum number `n_r` of solutions one offspring may replace. None places no cap, as in the
    original MOEA/D; MOEA/D-DE uses 2."""
    aggregation: Literal["tchebycheff", "pbi", "weighted_sum"] = Field(
        default="tchebycheff", description="The aggregation function of the subproblems."
    )
    """The aggregation function of the subproblems."""
    pbi_penalty: float = Field(default=5.0, gt=0.0, description="The penalty theta of the PBI function.")
    """The penalty `theta` of the PBI aggregation function. Only used with `aggregation="pbi"`."""


SelectorOptions = (
    RVEASelectorOptions | NSGA2SelectorOptions | NSGA3SelectorOptions | IBEASelectorOptions | SMSEMOASelectorOptions
)


def selection_constructor(
    problem: Problem, options: SelectorOptions | MOEADSelectorOptions, publisher: Publisher, verbosity: int, seed: int
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
        "MOEADSelector": MOEADSelector,
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
