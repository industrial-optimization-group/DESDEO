"""Imports available from the desdeo emo."""

__all__ = [
    "algorithms",
    "crossover",
    "generator",
    "mutation",
    "other",
    "preference_handling",
    "repair",
    "scalar_selection",
    "selection",
    "templates",
    "termination",
]

from types import SimpleNamespace

from .options.algorithms import (
    emo_constructor,
    ibea_mixed_integer_options,
    ibea_options,
    nsga3_mixed_integer_options,
    nsga3_options,
    rvea_mixed_integer_options,
    rvea_options,
)
from .options.crossover import (
    BlendAlphaCrossoverOptions,
    BoundedExponentialCrossoverOptions,
    LocalCrossoverOptions,
    SimulatedBinaryCrossoverOptions,
    SingleArithmeticCrossoverOptions,
    SinglePointBinaryCrossoverOptions,
    UniformIntegerCrossoverOptions,
    UniformMixedIntegerCrossoverOptions,
)
from .options.generator import (
    LHSGeneratorOptions,
    RandomBinaryGeneratorOptions,
    RandomGeneratorOptions,
    RandomIntegerGeneratorOptions,
    RandomMixedIntegerGeneratorOptions,
)
from .options.mutation import (
    BinaryFlipMutationOptions,
    BoundedPolynomialMutationOptions,
    IntegerRandomMutationOptions,
    MixedIntegerRandomMutationOptions,
    MPTMutationOptions,
    NonUniformMutationOptions,
    PowerMutationOptions,
    SelfAdaptiveGaussianMutationOptions,
)
from .options.repair import ClipRepairOptions, NoRepairOptions
from .options.scalar_selection import RouletteWheelSelectionOptions, TournamentSelectionOptions
from .options.selection import IBEASelectorOptions, NSGA3SelectorOptions, ReferenceVectorOptions, RVEASelectorOptions
from .options.templates import (
    DesirableRangesOptions,
    NonPreferredSolutionsOptions,
    PreferredSolutionsOptions,
    ReferencePointOptions,
    Template1Options,
    Template2Options,
)
from .options.termination import (
    CompositeTerminatorOptions,
    ExternalCheckTerminatorOptions,
    MaxEvaluationsTerminatorOptions,
    MaxGenerationsTerminatorOptions,
    MaxTimeTerminatorOptions,
)

# Just didn't want to have a thousand imports in the main namespace
algorithms = SimpleNamespace(
    rvea_options=rvea_options,
    nsga3_options=nsga3_options,
    ibea_options=ibea_options,
    rvea_mixed_integer_options=rvea_mixed_integer_options,
    nsga3_mixed_integer_options=nsga3_mixed_integer_options,
    ibea_mixed_integer_options=ibea_mixed_integer_options,
    emo_constructor=emo_constructor,
)

termination = SimpleNamespace(
    MaxEvaluationsTerminatorOptions=MaxEvaluationsTerminatorOptions,
    MaxGenerationsTerminatorOptions=MaxGenerationsTerminatorOptions,
    MaxTimeTerminatorOptions=MaxTimeTerminatorOptions,
    CompositeTerminatorOptions=CompositeTerminatorOptions,
    ExternalCheckTerminatorOptions=ExternalCheckTerminatorOptions,
)

selection = SimpleNamespace(
    IBEASelectorOptions=IBEASelectorOptions,
    NSGA3SelectorOptions=NSGA3SelectorOptions,
    RVEASelectorOptions=RVEASelectorOptions,
)

other = SimpleNamespace(
    ReferenceVectorOptions=ReferenceVectorOptions,
)

scalar_selection = SimpleNamespace(
    TournamentSelectionOptions=TournamentSelectionOptions,
    RouletteWheelSelectionOptions=RouletteWheelSelectionOptions,
)

mutation = SimpleNamespace(
    BinaryFlipMutationOptions=BinaryFlipMutationOptions,
    BoundedPolynomialMutationOptions=BoundedPolynomialMutationOptions,
    IntegerRandomMutationOptions=IntegerRandomMutationOptions,
    MixedIntegerRandomMutationOptions=MixedIntegerRandomMutationOptions,
    MPTMutationOptions=MPTMutationOptions,
    NonUniformMutationOptions=NonUniformMutationOptions,
    PowerMutationOptions=PowerMutationOptions,
    SelfAdaptiveGaussianMutationOptions=SelfAdaptiveGaussianMutationOptions,
)

generator = SimpleNamespace(
    LHSGeneratorOptions=LHSGeneratorOptions,
    RandomBinaryGeneratorOptions=RandomBinaryGeneratorOptions,
    RandomGeneratorOptions=RandomGeneratorOptions,
    RandomIntegerGeneratorOptions=RandomIntegerGeneratorOptions,
    RandomMixedIntegerGeneratorOptions=RandomMixedIntegerGeneratorOptions,
)

templates = SimpleNamespace(
    Template1Options=Template1Options,
    Template2Options=Template2Options,
)

repair = SimpleNamespace(NoRepairOptions=NoRepairOptions, ClipRepairOptions=ClipRepairOptions)

preference_handling = SimpleNamespace(
    ReferencePointOptions=ReferencePointOptions,
    DesirableRangesOptions=DesirableRangesOptions,
    PreferredSolutionsOptions=PreferredSolutionsOptions,
    NonPreferredSolutionsOptions=NonPreferredSolutionsOptions,
)

crossover = SimpleNamespace(
    BlendAlphaCrossoverOptions=BlendAlphaCrossoverOptions,
    BoundedExponentialCrossoverOptions=BoundedExponentialCrossoverOptions,
    LocalCrossoverOptions=LocalCrossoverOptions,
    SimulatedBinaryCrossoverOptions=SimulatedBinaryCrossoverOptions,
    SingleArithmeticCrossoverOptions=SingleArithmeticCrossoverOptions,
    SinglePointBinaryCrossoverOptions=SinglePointBinaryCrossoverOptions,
    UniformIntegerCrossoverOptions=UniformIntegerCrossoverOptions,
    UniformMixedIntegerCrossoverOptions=UniformMixedIntegerCrossoverOptions,
)
