"""JSON Schema for template options."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Literal

from pydantic import BaseModel, Field

from desdeo.emo.hooks.archivers import NonDominatedArchive
from desdeo.emo.methods.templates import EMOResult, template1, template2
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.options.crossover import (
    CrossoverOptions,
    crossover_constructor,
)
from desdeo.emo.options.generator import (
    GeneratorOptions,
    generator_constructor,
)
from desdeo.problem import Problem
from desdeo.tools.patterns import Publisher
from desdeo.tools.scalarization import add_desirability_funcs, add_iopis_funcs

from .mutation import (
    MutationOptions,
    mutation_constructor,
)
from .repair import NoRepairOptions, RepairOptions, repair_constructor
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
    repair: RepairOptions = Field(NoRepairOptions(), description="The repair operator options.")
    """The repair operator options."""
    use_archive: bool = Field(default=True, description="Whether to use an archive.")
    """Whether to use an archive."""
    seed: int = Field(default=0, description="The seed for random number generation.")
    """The seed for random number generation."""
    verbosity: int = Field(default=2, description="The verbosity level of the operators.")
    """The verbosity level of the operators."""
    algorithm_name: str
    """The unique name of the algorithm."""


class Template1Options(BaseTemplateOptions):
    """Options for template 1.

    Template 1 is used by methods such as NSGA-III and RVEA. See
    [template1][desdeo.emo.methods.templates.template1] for
    more details.
    """

    name: Literal["Template1"] = Field(default="Template1", frozen=True, description="The name of the template.")
    """The name of the template."""


class Template2Options(BaseTemplateOptions):
    """Options for template 2.

    Template 2 is used by methods such as IBEA. See
    [template2][desdeo.emo.methods.templates.template2] for
    more details.
    """

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
    aspiration_levels: dict[str, float] = Field(
        description="The aspiration levels as a dictionary with objective function symbols as the keys."
    )
    """The aspiration levels as a dictionary with objective function symbols as the keys."""
    reservation_levels: dict[str, float] = Field(
        description="The reservation levels as a dictionary with objective function symbols as the keys."
    )
    """The reservation levels as a dictionary with objective function symbols as the keys."""
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
    """The template options for the EMO algorithm."""


def preference_handler(
    preference: PreferenceOptions | None, problem: Problem, selection: SelectorOptions
) -> tuple[Problem, SelectorOptions]:
    """Handle the preference options for the EMO algorithm.

    This function modifies the problem and selection operator based on the provided preference options. E.g., if
    the preference method is "Hakanen", the reference vector options of the selection operator are modified to
    include the preference information. If the preference method is "IOPIS" or "DF transformation", the problem is
    modified to include desirability functions or IOPIS functions.

    Args:
        preference (PreferenceOptions | None): The preference options.
        problem (Problem): The optimization problem.
        selection (SelectorOptions): The selection operator options.

    Returns:
        tuple[Problem, SelectorOptions]: The (modified, if necessary) problem and selection operator options.

    Raises:
        InvalidTemplateError: If the preference handling method is incompatible with the selection operator.
    """
    if preference is None:
        return problem, selection

    if preference.method == "Hakanen":
        if "reference_vector_options" not in type(selection).model_fields:
            raise InvalidTemplateError(
                "Preference handling with Hakanen method requires a selection operator with reference vectors."
            )
        if selection.name == "IBEASelector":  # Technically not needed due to check above, but for shutting up linters
            raise InvalidTemplateError("Preference handling with Hakanen method is not supported for IBEASelector.")
        if selection.reference_vector_options is None:
            reference_vector_options = ReferenceVectorOptions()  # Use default reference vector options
        else:
            reference_vector_options = selection.reference_vector_options
        if isinstance(preference, DesirableRangesOptions):
            preference_value = {
                obj.symbol: [preference.aspiration_levels[obj.symbol], preference.reservation_levels[obj.symbol]]
                for obj in problem.objectives
            }
        else:
            preference_value = preference.preference
        setattr(reference_vector_options, preference.name, preference_value)
        selection.reference_vector_options = reference_vector_options
        return problem, selection
    if preference.method == "IOPIS":
        iopis_problem, _ = add_iopis_funcs(
            problem=problem,
            reference_point=preference.preference,
        )
        return iopis_problem, selection
    if preference.method == "DF transformation":
        df_problem, _ = add_desirability_funcs(
            problem=problem,
            aspiration_levels=preference.aspiration_levels,
            reservation_levels=preference.reservation_levels,
        )
        return df_problem, selection
    raise InvalidTemplateError(f"Unknown preference handling method: {preference.method}")


@dataclass
class ConstructorExtras:
    """Extra information returned by the emo_constructor."""

    problem: Problem
    """New problem generated by the constructor (e.g. to handle preferences via IOPIS). If no new problem is generated,
    the original problem is returned."""
    publisher: Publisher
    """The publisher associated with the current solver."""
    archive: NonDominatedArchive | None
    """The archive associated with the current solver, if any."""


def emo_constructor(
    emo_options: EMOOptions, problem: Problem, external_check: Callable[[], bool] | None = None
) -> tuple[Callable[[], EMOResult], ConstructorExtras]:
    """Construct an evolutionary algorithm from the given options.

    Args:
        emo_options (EMOOptions): The options for the EMO algorithm.
        problem (Problem): The optimization problem to solve.
        external_check (Callable[[], bool] | None): A callable that returns True if the algorithm should stop,
            False otherwise. By default, None.

    Returns:
        tuple[Callable[[], EMOResult], ConstructorExtras]: A tuple containing the template function
        and extra information such as the (possibly modified) problem, publisher, and archive. Run the template
        function to execute the algorithm.

    Raises:
        InvalidTemplateError: If the template configuration is invalid.
    """
    publisher = Publisher()

    template = emo_options.template

    problem_, selector_options = preference_handler(
        preference=emo_options.preference, problem=problem, selection=template.selection
    )

    evaluator = EMOEvaluator(problem=problem_, publisher=publisher, verbosity=template.verbosity)

    selector = selection_constructor(
        problem=problem_,
        options=selector_options,
        publisher=publisher,
        verbosity=template.verbosity,
        seed=template.seed,
    )

    generator = generator_constructor(
        problem=problem_,
        options=template.generator,
        evaluator=evaluator,
        publisher=publisher,
        verbosity=template.verbosity,
        seed=template.seed,
    )

    crossover = crossover_constructor(
        problem=problem_,
        options=template.crossover,
        publisher=publisher,
        verbosity=template.verbosity,
        seed=template.seed,
    )

    mutation = mutation_constructor(
        problem=problem_,
        options=template.mutation,
        publisher=publisher,
        verbosity=template.verbosity,
        seed=template.seed,
    )

    terminator = terminator_constructor(
        options=template.termination,
        publisher=publisher,
        external_check=external_check,
    )

    repair = repair_constructor(options=template.repair, problem=problem_)

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
            problem=problem_,
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
        raise InvalidTemplateError(f"Inconsistent template configuration. See details:\n {consistency[1]}")
    archive = components.pop("archive", None)
    template_funcs = {
        "Template1": template1,
        "Template2": template2,
    }

    constructor_extras = ConstructorExtras(problem=problem_, publisher=publisher, archive=archive)

    return (partial(template_funcs[template.name], **components, repair=repair), constructor_extras)
