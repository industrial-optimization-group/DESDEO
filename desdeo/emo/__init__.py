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
    agemoea2_mixed_integer_options,
    agemoea2_options,
    emo_constructor,
    hype_mixed_integer_options,
    hype_options,
    ibea_mixed_integer_options,
    ibea_options,
    modified_wasfga_mixed_integer_options,
    modified_wasfga_options,
    moead_de_options,
    moead_mixed_integer_options,
    moead_options,
    nsga2_options,
    nsga3_mixed_integer_options,
    nsga3_options,
    rvea_mixed_integer_options,
    rvea_options,
    sms_emoa_mixed_integer_options,
    sms_emoa_options,
    spea2_mixed_integer_options,
    spea2_options,
    xlemoo_options,
)
from .options.crossover import (
    BlendAlphaCrossoverOptions,
    BoundedExponentialCrossoverOptions,
    DifferentialEvolutionCrossoverOptions,
    LocalCrossoverOptions,
    ParentCentricCrossoverOptions,
    SimulatedBinaryCrossoverOptions,
    SingleArithmeticCrossoverOptions,
    SinglePointBinaryCrossoverOptions,
    UniformCrossoverOptions,
    UniformIntegerCrossoverOptions,
    UniformMixedIntegerCrossoverOptions,
)
from .options.generator import (
    LHSGeneratorOptions,
    RandomBinaryGeneratorOptions,
    RandomGeneratorOptions,
    RandomIntegerGeneratorOptions,
    RandomMixedIntegerGeneratorOptions,
    SeededHybridGeneratorOptions,
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
from .options.scalar_selection import (
    ElitistSelectionOptions,
    RouletteWheelSelectionOptions,
    TournamentSelectionOptions,
)
from .options.selection import (
    AGEMOEA2SelectorOptions,
    HypESelectorOptions,
    IBEASelectorOptions,
    ModifiedWASFGASelectorOptions,
    MOEADSelectorOptions,
    NSGA2SelectorOptions,
    NSGA3SelectorOptions,
    ReferenceVectorOptions,
    RVEASelectorOptions,
    SMSEMOASelectorOptions,
    SPEA2SelectorOptions,
)
from .options.templates import (
    DesirableRangesOptions,
    NonPreferredSolutionsOptions,
    PreferredSolutionsOptions,
    ReferencePointOptions,
    Template1Options,
    Template2Options,
    Template3Options,
    TemplateMOEADOptions,
    TemplateXLEMOOOptions,
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
    nsga2_options=nsga2_options,
    nsga3_options=nsga3_options,
    ibea_options=ibea_options,
    sms_emoa_options=sms_emoa_options,
    moead_options=moead_options,
    moead_de_options=moead_de_options,
    spea2_options=spea2_options,
    agemoea2_options=agemoea2_options,
    hype_options=hype_options,
    modified_wasfga_options=modified_wasfga_options,
    rvea_mixed_integer_options=rvea_mixed_integer_options,
    nsga3_mixed_integer_options=nsga3_mixed_integer_options,
    ibea_mixed_integer_options=ibea_mixed_integer_options,
    sms_emoa_mixed_integer_options=sms_emoa_mixed_integer_options,
    moead_mixed_integer_options=moead_mixed_integer_options,
    spea2_mixed_integer_options=spea2_mixed_integer_options,
    agemoea2_mixed_integer_options=agemoea2_mixed_integer_options,
    hype_mixed_integer_options=hype_mixed_integer_options,
    modified_wasfga_mixed_integer_options=modified_wasfga_mixed_integer_options,
    xlemoo_options=xlemoo_options,
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
    NSGA2SelectorOptions=NSGA2SelectorOptions,
    RVEASelectorOptions=RVEASelectorOptions,
    MOEADSelectorOptions=MOEADSelectorOptions,
    SMSEMOASelectorOptions=SMSEMOASelectorOptions,
    SPEA2SelectorOptions=SPEA2SelectorOptions,
    AGEMOEA2SelectorOptions=AGEMOEA2SelectorOptions,
    HypESelectorOptions=HypESelectorOptions,
    ModifiedWASFGASelectorOptions=ModifiedWASFGASelectorOptions,
)

other = SimpleNamespace(
    ReferenceVectorOptions=ReferenceVectorOptions,
)

scalar_selection = SimpleNamespace(
    TournamentSelectionOptions=TournamentSelectionOptions,
    RouletteWheelSelectionOptions=RouletteWheelSelectionOptions,
    ElitistSelectionOptions=ElitistSelectionOptions,
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
    SeededHybridGeneratorOptions=SeededHybridGeneratorOptions,
)

templates = SimpleNamespace(
    Template1Options=Template1Options,
    Template2Options=Template2Options,
    Template3Options=Template3Options,
    TemplateXLEMOOOptions=TemplateXLEMOOOptions,
    TemplateMOEADOptions=TemplateMOEADOptions,
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
    DifferentialEvolutionCrossoverOptions=DifferentialEvolutionCrossoverOptions,
    LocalCrossoverOptions=LocalCrossoverOptions,
    ParentCentricCrossoverOptions=ParentCentricCrossoverOptions,
    SimulatedBinaryCrossoverOptions=SimulatedBinaryCrossoverOptions,
    SingleArithmeticCrossoverOptions=SingleArithmeticCrossoverOptions,
    SinglePointBinaryCrossoverOptions=SinglePointBinaryCrossoverOptions,
    UniformCrossoverOptions=UniformCrossoverOptions,
    UniformIntegerCrossoverOptions=UniformIntegerCrossoverOptions,
    UniformMixedIntegerCrossoverOptions=UniformMixedIntegerCrossoverOptions,
)
