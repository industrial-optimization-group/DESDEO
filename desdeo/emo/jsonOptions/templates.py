"""JSON Schema for template options."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Literal

from pydantic import BaseModel, Field

from desdeo.emo.hooks.archivers import NonDominatedArchive
from desdeo.emo.jsonOptions.crossover import (
    CrossoverOptions,
    crossover_constructor,
)
from desdeo.emo.jsonOptions.generator import (
    GeneratorOptions,
    generator_constructor,
)
from desdeo.emo.methods.templates import EMOResult, template1, template2
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.problem import Problem
from desdeo.tools.patterns import Publisher

from .mutation import (
    MutationOptions,
    mutation_constructor,
)
from .scalar_selection import (
    ScalarSelectionOptions,
    scalar_selector_constructor,
)
from .selection import ReferenceVectorOptions, SelectorOptions, selection_constructor
from .termination import (
    TerminatorOptions,
    terminator_constructor,
)


class InvalidTemplateError(Exception):
    """Exception raised for invalid template configurations."""


class BaseTemplateOptions(BaseModel):
    """Base class for template options."""

    crossover: CrossoverOptions = Field(description="The crossover operator options.")
    """The crossover operator options."""
    mutation: MutationOptions = Field(description="The mutation operator options.")
    """The mutation operator options."""
    selection: SelectorOptions = Field(description="The selection operator options.")
    """The selection operator options."""
    termination: TerminatorOptions = Field(description="The termination operator options.")
    """The termination operator options."""
    generator: GeneratorOptions = Field(description="The population generator options.")
    """The population generator options."""
    use_archive: bool = Field(default=True, description="Whether to use an archive.")
    """Whether to use an archive."""
    seed: int = Field(default=0, description="The seed for random number generation.")
    """The seed for random number generation."""
    verbosity: int = Field(default=2, description="The verbosity level of the operators.")
    """The verbosity level of the operators."""


class Template1Options(BaseTemplateOptions):
    """Options for template 1."""

    name: Literal["Template1"] = Field(default="Template1", frozen=True, description="The name of the template.")
    """The name of the template."""


class Template2Options(BaseTemplateOptions):
    """Options for template 2."""

    name: Literal["Template2"] = Field(default="Template2", frozen=True, description="The name of the template.")
    """The name of the template."""
    mate_selection: ScalarSelectionOptions = Field(description="The mate selection operator options.")


TemplateOptions = Template1Options | Template2Options


class ReferencePointOptions(BaseModel):
    """Options for providing a reference point for an EA."""

    name: Literal["reference_point"] = Field(
        default="reference_point", frozen=True, description="The name of the reference point option."
    )
    """The name of the reference point option."""
    preference: dict[str, float] = Field(
        description="The reference point as a dictionary with objective function symbols as the keys."
    )
    """The reference point as a dictionary with objective function symbols as the keys."""
    method: Literal["Hakanen", "IOPIS"] = Field(
        default="Hakanen", description="The method for handling the reference point."
    )
    """The method for handling the reference point."""


class DesirableRangesOptions(BaseModel):
    """Options for providing desirable ranges for an EA."""

    name: Literal["preferred_ranges"] = Field(
        default="preferred_ranges", frozen=True, description="The name of the preferred ranges option."
    )
    """The name of the preferred ranges option."""
    preference: dict[str, tuple[float, float]] = Field(
        description="The desirable ranges as a dictionary with objective function symbols as the keys."
    )
    """The desirable ranges as a dictionary with objective function symbols as the keys."""
    method: Literal["Hakanen", "DF transformation"] = Field(
        default="Hakanen", description="The method for handling the desirable ranges."
    )
    """The method for handling the desirable ranges."""


class PreferredSolutionsOptions(BaseModel):
    """Options for providing preferred solutions for an EA."""

    name: Literal["preferred_solutions"] = Field(
        default="preferred_solutions", frozen=True, description="The name of the preferred solutions option."
    )
    """The name of the preferred solutions option."""
    preference: dict[str, list[float]] = Field(
        description="The preferred solutions as a dictionary with objective function symbols as the keys."
    )
    """The preferred solutions as a dictionary with objective function symbols as the keys."""
    method: Literal["Hakanen"] = Field(
        default="Hakanen", description="The method for handling the preferred solutions."
    )
    """The method for handling the preferred solutions."""


class NonPreferredSolutionsOptions(BaseModel):
    """Options for providing non-preferred solutions for an EA."""

    name: Literal["non_preferred_solutions"] = Field(
        default="non_preferred_solutions", frozen=True, description="The name of the non-preferred solutions option."
    )
    """The name of the non-preferred solutions option."""
    preference: dict[str, list[float]] = Field(
        description="The non-preferred solutions as a dictionary with objective function symbols as the keys."
    )
    """The non-preferred solutions as a dictionary with objective function symbols as the keys."""
    method: Literal["Hakanen"] = Field(
        default="Hakanen", description="The method for handling the non-preferred solutions."
    )
    """The method for handling the non-preferred solutions."""


PreferenceOptions = (
    ReferencePointOptions | DesirableRangesOptions | PreferredSolutionsOptions | NonPreferredSolutionsOptions
)


class EMOOptions(BaseModel):
    """Options for configuring the EMO algorithm."""

    preference: PreferenceOptions | None = Field(description="The preference information for the EMO algorithm.")
    """The preference information for the EMO algorithm."""
    template: TemplateOptions = Field(description="The template options for the EMO algorithm.")


def preference_handler(preference: PreferenceOptions | None, problem: Problem, selection: SelectorOptions) -> None:
    """Handle the preference options for the EMO algorithm."""
    if preference is None:
        return

    if preference.method == "Hakanen":
        if "reference_vector_options" not in type(selection).model_fields:
            raise InvalidTemplateError(
                "Preference handling with Hakanen method requires a selection operator with reference vectors."
            )
        if selection.reference_vector_options is None:
            reference_vector_options = ReferenceVectorOptions()  # Use default reference vector options
        setattr(reference_vector_options, preference.name, preference.preference)
        selection.reference_vector_options = reference_vector_options
    elif preference.method == "IOPIS":
        raise NotImplementedError("IOPIS method is not implemented here yet.")
    elif preference.method == "DF transformation":
        raise NotImplementedError("DF transformation method is not implemented here yet.")
    else:
        raise InvalidTemplateError(f"Unknown preference handling method: {preference.method}")


def template_constructor(emo_options: EMOOptions, problem: Problem) -> tuple[Callable[[], EMOResult], Publisher]:
    """Construct a template from the given options."""
    publisher = Publisher()

    template = emo_options.template

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=template.verbosity)

    selector = selection_constructor(
        problem=problem,
        options=template.selection,
        publisher=publisher,
        verbosity=template.verbosity,
        seed=template.seed,
    )

    generator = generator_constructor(
        problem=problem,
        options=template.generator,
        evaluator=evaluator,
        publisher=publisher,
        verbosity=template.verbosity,
        seed=template.seed,
    )

    crossover = crossover_constructor(
        problem=problem,
        options=template.crossover,
        publisher=publisher,
        verbosity=template.verbosity,
        seed=template.seed,
    )

    mutation = mutation_constructor(
        problem=problem,
        options=template.mutation,
        publisher=publisher,
        verbosity=template.verbosity,
        seed=template.seed,
    )

    terminator = terminator_constructor(
        options=template.termination,
        publisher=publisher,
    )

    components = {
        "evaluator": evaluator,
        "generator": generator,
        "crossover": crossover,
        "mutation": mutation,
        "selection": selector,
        "terminator": terminator,
    }

    if template.use_archive:
        archive = NonDominatedArchive(
            problem=problem,
            publisher=publisher,
        )
        components["archive"] = archive

    if template.name == "Template2":
        scalar_selector = scalar_selector_constructor(
            options=template.mate_selection,
            publisher=publisher,
            verbosity=template.verbosity,
            seed=template.seed,
        )
        components["mate_selection"] = scalar_selector

    [publisher.auto_subscribe(x) for x in components.values()]
    [publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components.values()]

    consistency = publisher.check_consistency()

    if not consistency[0]:
        raise ValueError(f"Inconsistent template configuration. See details:\n {consistency[1]}")
    components.pop("archive", None)
    template_funcs = {
        "Template1": template1,
        "Template2": template2,
    }
    return (partial(template_funcs[template.name], **components), publisher)
