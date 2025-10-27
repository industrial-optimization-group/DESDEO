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


def rvea_options() -> EMOOptions:
    """Get default Reference Vector Guided Evolutionary Algorithm (RVEA) options as a Pydantic model.

    References:
        R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, "A Reference Vector Guided Evolutionary Algorithm for Many-
        Objective Optimization," in IEEE Transactions on Evolutionary Computation, vol. 20, no. 5, pp. 773-791,
        Oct. 2016, doi: 10.1109/TEVC.2016.2519378.

        J. Hakanen, T. Chugh, K. Sindhya, Y. Jin, and K. Miettinen, “Connections of reference vectors and different
        types of preference information in interactive multiobjective evolutionary algorithms,” in 2016 IEEE Symposium
        Series on Computational Intelligence (SSCI), Athens, Greece: IEEE, Dec. 2016, pp. 1-8.

    Returns:
        EMOOptions: The default RVEA options as a Pydantic model.
    """
    return EMOOptions(
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


def nsga3_options() -> EMOOptions:
    """Get default NSGA-III options as a Pydantic model.

    References:
        K. Deb and H. Jain, “An Evolutionary Many-Objective Optimization Algorithm Using Reference-Point-Based
        Nondominated Sorting Approach, Part I: Solving Problems With Box Constraints,” IEEE Transactions on Evolutionary
        Computation, vol. 18, no. 4, pp. 577-601, Aug. 2014.

        J. Hakanen, T. Chugh, K. Sindhya, Y. Jin, and K. Miettinen, “Connections of reference vectors and different
        types of preference information in interactive multiobjective evolutionary algorithms,” in 2016 IEEE Symposium
        Series on Computational Intelligence (SSCI), Athens, Greece: IEEE, Dec. 2016, pp. 1-8.

    Returns:
        EMOOptions: The default NSGA-III options as a Pydantic model.
    """
    return EMOOptions(
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


def ibea_options() -> EMOOptions:
    """Get default IBEA options as a Pydantic model.

    References:
        Zitzler, E., Künzli, S. (2004). Indicator-Based Selection in Multiobjective Search. In: Yao, X., et al.
        Parallel Problem Solving from Nature - PPSN VIII. PPSN 2004. Lecture Notes in Computer Science, vol 3242.
        Springer, Berlin, Heidelberg. https://doi.org/10.1007/978-3-540-30217-9_84

    Returns:
        EMOOptions: The default IBEA options as a Pydantic model.
    """
    return EMOOptions(
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


def rvea_mixed_integer_options() -> EMOOptions:
    """Get default RVEA options for mixed integer problems as a Pydantic model.

    References:
        R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, "A Reference Vector Guided Evolutionary Algorithm for Many-
        Objective Optimization," in IEEE Transactions on Evolutionary Computation, vol. 20, no. 5, pp. 773-791,
        Oct. 2016, doi: 10.1109/TEVC.2016.2519378.

        J. Hakanen, T. Chugh, K. Sindhya, Y. Jin, and K. Miettinen, “Connections of reference vectors and different
        types of preference information in interactive multiobjective evolutionary algorithms,” in 2016 IEEE Symposium
        Series on Computational Intelligence (SSCI), Athens, Greece: IEEE, Dec. 2016, pp. 1-8.

    Returns:
        EMOOptions: The default RVEA mixed integer options as a Pydantic model
    """
    return EMOOptions(
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


def nsga3_mixed_integer_options() -> EMOOptions:
    """Get default NSGA3 options for mixed integer problems as a Pydantic model.

    References:
        K. Deb and H. Jain, “An Evolutionary Many-Objective Optimization Algorithm Using Reference-Point-Based
        Nondominated Sorting Approach, Part I: Solving Problems With Box Constraints,” IEEE Transactions on Evolutionary
        Computation, vol. 18, no. 4, pp. 577-601, Aug. 2014.

        J. Hakanen, T. Chugh, K. Sindhya, Y. Jin, and K. Miettinen, “Connections of reference vectors and different
        types of preference information in interactive multiobjective evolutionary algorithms,” in 2016 IEEE Symposium
        Series on Computational Intelligence (SSCI), Athens, Greece: IEEE, Dec. 2016, pp. 1-8.

    Returns:
        EMOOptions: The default NSGA3 mixed integer options as a Pydantic model
    """
    return EMOOptions(
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


def ibea_mixed_integer_options() -> EMOOptions:
    """Get default IBEA options for mixed integer problems as a Pydantic model.

    References:
        Zitzler, E., Künzli, S. (2004). Indicator-Based Selection in Multiobjective Search. In: Yao, X., et al.
        Parallel Problem Solving from Nature - PPSN VIII. PPSN 2004. Lecture Notes in Computer Science, vol 3242.
        Springer, Berlin, Heidelberg. https://doi.org/10.1007/978-3-540-30217-9_84

    Returns:
        EMOOptions: The default IBEA mixed integer options as a Pydantic model
    """
    return EMOOptions(
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
            json.dump(algo().model_dump(), f, indent=4)
