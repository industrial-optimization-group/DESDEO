"""Define popular MOEAs as Pydantic models."""

from desdeo.emo.options.crossover import SimulatedBinaryCrossoverOptions, UniformMixedIntegerCrossoverOptions
from desdeo.emo.options.generator import LHSGeneratorOptions, RandomMixedIntegerGeneratorOptions
from desdeo.emo.options.mutation import BoundedPolynomialMutationOptions, MixedIntegerRandomMutationOptions
from desdeo.emo.options.repair import NoRepairOptions
from desdeo.emo.options.scalar_selection import TournamentSelectionOptions
from desdeo.emo.options.selection import (
    IBEASelectorOptions,
    NSGA2SelectorOptions,
    NSGA3SelectorOptions,
    ParameterAdaptationStrategy,
    ReferenceVectorOptions,
    RVEASelectorOptions,
    SMSEMOASelectorOptions,
)
from desdeo.emo.options.templates import (
    EMOOptions,
    Template1Options,
    Template2Options,
)
from desdeo.emo.options.termination import MaxEvaluationsTerminatorOptions, MaxGenerationsTerminatorOptions


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


def nsga2_options() -> EMOOptions:
    """Get default NSGA-II options as a Pydantic model.

    Reference: Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. A. M. T.
        (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE
        transactions on evolutionary computation, 6(2), 182-197.

    Returns:
        EMOOptions: The default NSGA-II options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=Template2Options(
            algorithm_name="NSGA-II",
            crossover=SimulatedBinaryCrossoverOptions(
                name="SimulatedBinaryCrossover",
                xover_distribution=20,  # Note that the operator defaults are different in Template2
                xover_probability=0.9,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=0.01,
            ),
            selection=NSGA2SelectorOptions(
                name="NSGA2Selector",
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


def smsemoa_options(
    population_size: int = 100,
    n_offspring: int = 100,
    max_evaluations: int = 20000,
    use_dominating_points: bool = True,
    greedy_reduction: bool = True,
    seed: int = 42,
) -> EMOOptions:
    """Get default S-Metric Selection EMOA (SMS-EMOA) options as a Pydantic model.

    SMS-EMOA is a steady-state evolutionary multiobjective algorithm whose selection (Reduce) operator combines
    non-dominated sorting with the contributing hypervolume, thereby steering the population towards a
    well-distributed approximation of the Pareto front that maximizes the dominated hypervolume. This
    implementation creates ``n_offspring`` offspring per generation (a (mu + n_offspring) scheme) and reduces the
    population back to ``population_size`` by repeatedly discarding the worst individual of the worst-ranked
    front. Termination is based on the number of function evaluations.

    Reference:
        Beume, N., Naujoks, B., & Emmerich, M. (2007). SMS-EMOA: Multiobjective selection based on dominated
        hypervolume. European Journal of Operational Research, 181(3), 1653-1669.
        https://doi.org/10.1016/j.ejor.2006.08.008

    Args:
        population_size (int, optional): The (constant) size of the population. Defaults to 100.
        n_offspring (int, optional): The number of offspring generated each generation. Must be greater than 1.
            Smaller values are closer to the original steady-state SMS-EMOA (one offspring per generation) and give
            marginally higher quality, while larger values amortize per-iteration overhead and run faster. The
            default of 100 (a (mu + mu) scheme) is a good balance. Defaults to 100.
        max_evaluations (int, optional): The function evaluation budget. Defaults to 20000.
        use_dominating_points (bool, optional): Whether to use the cheaper "dominating points" variant when the
            population is not yet fully non-dominated. Defaults to True.
        greedy_reduction (bool, optional): If True, remove individuals one at a time, recomputing hypervolume
            contributions after each removal (faithful, best quality). If False, remove the least contributors in a
            single batch per generation, which is dramatically faster for four or more objectives at a small
            quality cost. Defaults to True.
        seed (int, optional): The random seed. Defaults to 42.

    Returns:
        EMOOptions: The default SMS-EMOA options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=Template2Options(
            algorithm_name="SMS-EMOA",
            crossover=SimulatedBinaryCrossoverOptions(
                name="SimulatedBinaryCrossover",
                xover_distribution=15,
                xover_probability=0.9,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,
            ),
            selection=SMSEMOASelectorOptions(
                name="SMSEMOASelector",
                population_size=population_size,
                reference_point_offset=1.0,
                use_dominating_points=use_dominating_points,
                greedy_reduction=greedy_reduction,
            ),
            mate_selection=TournamentSelectionOptions(
                name="TournamentSelection",
                tournament_size=2,
                winner_size=n_offspring,
            ),
            generator=LHSGeneratorOptions(
                name="LHSGenerator",
                n_points=population_size,
            ),
            repair=NoRepairOptions(
                name="NoRepair",
            ),
            termination=MaxEvaluationsTerminatorOptions(
                name="MaxEvaluationsTerminator",
                max_evaluations=max_evaluations,
            ),
            use_archive=True,
            verbosity=2,
            seed=seed,
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
        ["rvea", "nsga3", "ibea", "smsemoa", "rvea_mixed_integer", "nsga3_mixed_integer", "ibea_mixed_integer"],
        [
            rvea_options,
            nsga3_options,
            ibea_options,
            smsemoa_options,
            rvea_mixed_integer_options,
            nsga3_mixed_integer_options,
            ibea_mixed_integer_options,
        ],
        strict=True,
    ):
        if not json_dump_path.exists():
            json_dump_path.mkdir(parents=True, exist_ok=True)
        with Path.open(json_dump_path / f"{algo_name}.json", "w") as f:
            json.dump(algo().model_dump(), f, indent=4)

    # Also dump the schema
    with Path.open(json_dump_path / f"emoOptionsSchema.json", "w") as f:
        json.dump(EMOOptions.model_json_schema(), f, indent=4)
