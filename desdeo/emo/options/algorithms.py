"""Define popular MOEAs as Pydantic models."""

from collections.abc import Callable
from functools import partial

from desdeo.emo.options.crossover import SimulatedBinaryCrossoverOptions, UniformMixedIntegerCrossoverOptions
from desdeo.emo.options.generator import LHSGeneratorOptions, RandomMixedIntegerGeneratorOptions
from desdeo.emo.options.mutation import BoundedPolynomialMutationOptions, MixedIntegerRandomMutationOptions
from desdeo.emo.options.repair import NoRepairOptions
from desdeo.emo.options.scalar_selection import TournamentSelectionOptions
from desdeo.emo.options.selection import (
    IBEASelectorOptions,
    NSGA3SelectorOptions,
    ParameterAdaptationStrategy,
    ReferenceVectorOptions,
    RVEASelectorOptions,
)
from desdeo.emo.options.templates import (
    ConstructorExtras,
    EMOOptions,
    EMOResult,
    Template1Options,
    Template2Options,
    emo_constructor,
)
from desdeo.emo.options.termination import MaxGenerationsTerminatorOptions
from desdeo.problem import Problem

rvea_options = lambda: EMOOptions(  # noqa: E731
    preference=None,
    template=Template1Options(
        algorithm_name="RVEA",
        crossover=SimulatedBinaryCrossoverOptions(
            name="SimulatedBinaryCrossover",
            xover_distribution=30,
            xover_probability=0.5,
        ),
        mutation=BoundedPolynomialMutationOptions(
            name="BoundedPolynomialMutation",
            distribution_index=20,
            mutation_probability=None,
        ),
        selection=RVEASelectorOptions(
            name="RVEASelector",
            alpha=2,
            parameter_adaptation_strategy=ParameterAdaptationStrategy.GENERATION_BASED,
            reference_vector_options=ReferenceVectorOptions(
                adaptation_frequency=100,
                creation_type="simplex",
                vector_type="spherical",
                lattice_resolution=None,
                number_of_vectors=100,
                adaptation_distance=0.2,
                reference_point=None,
                preferred_solutions=None,
                non_preferred_solutions=None,
                preferred_ranges=None,
            ),
        ),
        generator=LHSGeneratorOptions(
            name="LHSGenerator",
            n_points=100,
        ),
        repair=NoRepairOptions(
            name="NoRepair",
        ),
        termination=MaxGenerationsTerminatorOptions(
            name="MaxGenerationsTerminator",
            max_generations=100,
        ),
        use_archive=True,
        verbosity=2,
        seed=42,
    ),
)

nsga3_options = lambda: EMOOptions(  # noqa: E731
    preference=None,
    template=Template1Options(
        algorithm_name="NSGA3",
        crossover=SimulatedBinaryCrossoverOptions(
            name="SimulatedBinaryCrossover",
            xover_distribution=30,
            xover_probability=0.5,
        ),
        mutation=BoundedPolynomialMutationOptions(
            name="BoundedPolynomialMutation",
            distribution_index=20,
            mutation_probability=None,
        ),
        selection=NSGA3SelectorOptions(
            name="NSGA3Selector",
            reference_vector_options=ReferenceVectorOptions(
                adaptation_frequency=0,
                creation_type="simplex",
                vector_type="planar",
                lattice_resolution=None,
                number_of_vectors=100,
                adaptation_distance=0.2,
                reference_point=None,
                preferred_solutions=None,
                non_preferred_solutions=None,
                preferred_ranges=None,
            ),
        ),
        generator=LHSGeneratorOptions(
            name="LHSGenerator",
            n_points=100,
        ),
        repair=NoRepairOptions(
            name="NoRepair",
        ),
        termination=MaxGenerationsTerminatorOptions(
            name="MaxGenerationsTerminator",
            max_generations=100,
        ),
        use_archive=True,
        verbosity=2,
        seed=42,
    ),
)

ibea_options = lambda: EMOOptions(  # noqa:E731
    preference=None,
    template=Template2Options(
        algorithm_name="IBEA",
        crossover=SimulatedBinaryCrossoverOptions(
            name="SimulatedBinaryCrossover",
            xover_distribution=20,  # Note that the operator defaults are different in Template2
            xover_probability=0.5,
        ),
        mutation=BoundedPolynomialMutationOptions(
            name="BoundedPolynomialMutation",
            distribution_index=20,
            mutation_probability=0.01,
        ),
        selection=IBEASelectorOptions(
            name="IBEASelector",
            binary_indicator="eps",
            kappa=0.05,
            population_size=100,
        ),
        mate_selection=TournamentSelectionOptions(
            name="TournamentSelection",
            tournament_size=2,
            winner_size=100,
        ),
        generator=LHSGeneratorOptions(
            name="LHSGenerator",
            n_points=100,
        ),
        repair=NoRepairOptions(
            name="NoRepair",
        ),
        termination=MaxGenerationsTerminatorOptions(
            name="MaxGenerationsTerminator",
            max_generations=100,
        ),
        use_archive=True,
        verbosity=2,
        seed=42,
    ),
)

rvea_mixed_integer_options = lambda: EMOOptions(  # noqa:E731
    preference=None,
    template=Template1Options(
        algorithm_name="RVEA_Mixed_Integer",
        crossover=UniformMixedIntegerCrossoverOptions(),
        mutation=MixedIntegerRandomMutationOptions(),
        selection=RVEASelectorOptions(
            name="RVEASelector",
            alpha=2,
            parameter_adaptation_strategy=ParameterAdaptationStrategy.GENERATION_BASED,
            reference_vector_options=ReferenceVectorOptions(
                adaptation_frequency=100,
                creation_type="simplex",
                vector_type="spherical",
                lattice_resolution=None,
                number_of_vectors=100,
                adaptation_distance=0.2,
                reference_point=None,
                preferred_solutions=None,
                non_preferred_solutions=None,
                preferred_ranges=None,
            ),
        ),
        generator=RandomMixedIntegerGeneratorOptions(n_points=100),
        repair=NoRepairOptions(
            name="NoRepair",
        ),
        termination=MaxGenerationsTerminatorOptions(
            name="MaxGenerationsTerminator",
            max_generations=100,
        ),
        use_archive=True,
        verbosity=2,
        seed=42,
    ),
)

nsga3_mixed_integer_options = lambda: EMOOptions(  # noqa:E731
    preference=None,
    template=Template1Options(
        algorithm_name="NSGA3_Mixed_Integer",
        crossover=UniformMixedIntegerCrossoverOptions(),
        mutation=MixedIntegerRandomMutationOptions(),
        selection=NSGA3SelectorOptions(
            name="NSGA3Selector",
            reference_vector_options=ReferenceVectorOptions(
                adaptation_frequency=0,
                creation_type="simplex",
                vector_type="planar",
                lattice_resolution=None,
                number_of_vectors=100,
                adaptation_distance=0.2,
                reference_point=None,
                preferred_solutions=None,
                non_preferred_solutions=None,
                preferred_ranges=None,
            ),
        ),
        generator=RandomMixedIntegerGeneratorOptions(n_points=100),
        repair=NoRepairOptions(
            name="NoRepair",
        ),
        termination=MaxGenerationsTerminatorOptions(
            name="MaxGenerationsTerminator",
            max_generations=100,
        ),
        use_archive=True,
        verbosity=2,
        seed=42,
    ),
)

ibea_mixed_integer_options = lambda: EMOOptions(   # noqa:E731
    preference=None,
    template=Template2Options(
        algorithm_name="IBEA_Mixed_Integer",
        crossover=UniformMixedIntegerCrossoverOptions(),
        mutation=MixedIntegerRandomMutationOptions(),
        selection=IBEASelectorOptions(
            name="IBEASelector",
            binary_indicator="eps",
            kappa=0.05,
            population_size=100,
        ),
        mate_selection=TournamentSelectionOptions(
            name="TournamentSelection",
            tournament_size=2,
            winner_size=100,
        ),
        generator=RandomMixedIntegerGeneratorOptions(n_points=100),
        repair=NoRepairOptions(
            name="NoRepair",
        ),
        termination=MaxGenerationsTerminatorOptions(
            name="MaxGenerationsTerminator",
            max_generations=100,
        ),
        use_archive=True,
        verbosity=2,
        seed=42,
    ),
)

if __name__ == "__main__":
    import json
    from pathlib import Path

    current_dir = Path(__file__)
    json_dump_path = current_dir.parent.parent.parent.parent / "datasets" / "emoTemplates"

    for algo_name, algo in zip(
        ["rvea", "nsga3", "ibea", "rvea_mixed_integer", "nsga3_mixed_integer", "ibea_mixed_integer"],
        [
            rvea_options,
            nsga3_options,
            ibea_options,
            rvea_mixed_integer_options,
            nsga3_mixed_integer_options,
            ibea_mixed_integer_options,
        ],
        strict=True,
    ):
        if not json_dump_path.exists():
            json_dump_path.mkdir(parents=True, exist_ok=True)
        with Path.open(json_dump_path / f"{algo_name}.json", "a") as f:
            json.dump(algo.model_dump(), f, indent=4)
