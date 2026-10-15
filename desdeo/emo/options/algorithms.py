"""Define popular MOEAs as Pydantic models."""

from desdeo.emo.options.crossover import (
    DifferentialEvolutionCrossoverOptions,
    SimulatedBinaryCrossoverOptions,
    UniformMixedIntegerCrossoverOptions,
)
from desdeo.emo.options.generator import LHSGeneratorOptions, RandomGeneratorOptions, RandomMixedIntegerGeneratorOptions
from desdeo.emo.options.mutation import BoundedPolynomialMutationOptions, MixedIntegerRandomMutationOptions
from desdeo.emo.options.repair import ClipRepairOptions, NoRepairOptions
from desdeo.emo.options.scalar_selection import ElitistSelectionOptions, TournamentSelectionOptions
from desdeo.emo.options.selection import (
    AGEMOEA2SelectorOptions,
    HypESelectorOptions,
    IBEASelectorOptions,
    MOEADSelectorOptions,
    NSGA2SelectorOptions,
    NSGA3SelectorOptions,
    ParameterAdaptationStrategy,
    ReferenceVectorOptions,
    RVEASelectorOptions,
    SMSEMOASelectorOptions,
    SPEA2SelectorOptions,
)
from desdeo.emo.options.templates import (
    EMOOptions,
    Template1Options,
    Template2Options,
    Template3Options,
    TemplateMOEADOptions,
    TemplateXLEMOOOptions,
    emo_constructor,
)
from desdeo.emo.options.termination import MaxEvaluationsTerminatorOptions, MaxGenerationsTerminatorOptions

__all__ = [
    "agemoea2_mixed_integer_options",
    "agemoea2_options",
    "emo_constructor",
    "hype_mixed_integer_options",
    "hype_options",
    "ibea_mixed_integer_options",
    "ibea_options",
    "moead_de_options",
    "moead_mixed_integer_options",
    "moead_options",
    "nsga2_options",
    "nsga3_mixed_integer_options",
    "nsga3_options",
    "rvea_mixed_integer_options",
    "rvea_options",
    "sms_emoa_options",
    "spea2_mixed_integer_options",
    "spea2_options",
    "xlemoo_options",
]


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
                # The paper's p_c = 1 is a per-pair probability; the per-variable rate is Deb and
                # Agrawal's 0.5. Collapsing the two would cross every variable instead of half.
                pair_xover_probability=1.0,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
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
            repair=ClipRepairOptions(),
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
                # The paper's p_c = 1 is a per-pair probability; the per-variable rate is Deb
                # and Agrawal's 0.5. Collapsing the two would cross every variable, not half.
                pair_xover_probability=1.0,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
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
            repair=ClipRepairOptions(),
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
                pair_xover_probability=1.0,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,
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
            repair=ClipRepairOptions(),
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
                # NSGA-II reports p_c = 0.9, which is per pair, not per variable.
                pair_xover_probability=0.9,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,
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
            # Deb's NSGA-II reference code clamps offspring onto the variable bounds. Leaving this as
            # NoRepair lets an operator that can leave the box (or emit NaN) feed straight into the
            # evaluator, which the other real-coded templates here already guard against.
            repair=ClipRepairOptions(),
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


def xlemoo_options() -> EMOOptions:
    """Get default XLEMOO options as a Pydantic model.

    XLEMOO alternates between Darwinian and Learning modes. Default cycle is 20 Darwinian
    iterations followed by 1 Learning iteration. The learning mode trains a SkopeRules
    classifier on the H/L split of past solutions and instantiates new candidates from
    the extracted rules.

    References:
        Misitano, G. (2024). Exploring the explainable aspects and performance
            of a learnable evolutionary multiobjective optimization method. ACM
            Transactions on Evolutionary Learning and Optimization, 4(1), 1-39.

    Returns:
        EMOOptions: The default XLEMOO options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=TemplateXLEMOOOptions(
            algorithm_name="XLEMOO",
            crossover=SimulatedBinaryCrossoverOptions(
                name="SimulatedBinaryCrossover",
                xover_distribution=30,
                pair_xover_probability=1.0,
                xover_probability=0.5,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,
            ),
            selection=ElitistSelectionOptions(
                name="ElitistSelection",
                winner_size=50,
                target_column="asf",
            ),
            generator=LHSGeneratorOptions(
                name="LHSGenerator",
                n_points=50,
            ),
            repair=NoRepairOptions(
                name="NoRepair",
            ),
            termination=MaxGenerationsTerminatorOptions(
                name="MaxGenerationsTerminator",
                max_generations=200,
            ),
            n_darwin_per_cycle=20,
            n_learning_per_cycle=1,
            h_split=0.2,
            l_split=0.2,
            instantiation_factor=10.0,
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


def sms_emoa_options() -> EMOOptions:
    """Get default SMS-EMOA options as a Pydantic model.

    References:
        Beume, N., Naujoks, B., & Emmerich, M. (2007). SMS-EMOA: Multiobjective selection based on
        dominated hypervolume. European Journal of Operational Research, 181(3), 1653-1669.

    Returns:
        EMOOptions: The default SMS-EMOA options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=Template3Options(
            algorithm_name="SMS-EMOA",
            crossover=SimulatedBinaryCrossoverOptions(
                name="SimulatedBinaryCrossover",
                xover_distribution=30,
                pair_xover_probability=1.0,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,
            ),
            selection=SMSEMOASelectorOptions(),
            generator=LHSGeneratorOptions(
                name="LHSGenerator",
                n_points=100,
            ),
            repair=ClipRepairOptions(),
            termination=MaxEvaluationsTerminatorOptions(
                name="MaxEvaluationsTerminator",
                max_evaluations=1000,
            ),
            use_archive=True,
            verbosity=2,
            seed=42,
        ),
    )


def sms_emoa_mixed_integer_options() -> EMOOptions:
    """Get default SMS-EMOA options for mixed integer problems as a Pydantic model.

    References:
        Beume, N., Naujoks, B., & Emmerich, M. (2007). SMS-EMOA: Multiobjective selection based on
        dominated hypervolume. European Journal of Operational Research, 181(3), 1653-1669.

    Returns:
        EMOOptions: The default SMS-EMOA mixed integer options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=Template3Options(
            algorithm_name="SMS-EMOA_Mixed_Integer",
            crossover=UniformMixedIntegerCrossoverOptions(),
            mutation=MixedIntegerRandomMutationOptions(),
            selection=SMSEMOASelectorOptions(),
            generator=RandomMixedIntegerGeneratorOptions(n_points=100),
            repair=NoRepairOptions(
                name="NoRepair",
            ),
            termination=MaxEvaluationsTerminatorOptions(
                name="MaxEvaluationsTerminator",
                max_evaluations=1000,
            ),
            use_archive=True,
            verbosity=2,
            seed=42,
        ),
    )


def moead_options() -> EMOOptions:
    """Get default MOEA/D options as a Pydantic model.

    The variant of Section V of the paper: Tchebycheff aggregation, no external population, simulated
    binary crossover and polynomial mutation, and neighbourhood mating with every improved neighbour
    replaced.

    References:
        Q. Zhang and H. Li, "MOEA/D: A Multiobjective Evolutionary Algorithm Based on Decomposition," IEEE
        Transactions on Evolutionary Computation, vol. 11, no. 6, pp. 712-731, Dec. 2007,
        doi: 10.1109/TEVC.2007.892759.

    Returns:
        EMOOptions: The default MOEA/D options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=TemplateMOEADOptions(
            algorithm_name="MOEA/D",
            crossover=SimulatedBinaryCrossoverOptions(
                name="SimulatedBinaryCrossover",
                xover_distribution=20,
                # The paper's "crossover rate is 1.00" is per pair, following Deb's NSGA-II code,
                # whose per-variable rate is 0.5. The template keeps one of the two children.
                pair_xover_probability=1.0,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,  # 1/n
            ),
            selection=MOEADSelectorOptions(
                name="MOEADSelector",
                # The paper uses N = 100 weight vectors at two objectives and 300 at three (H = 23).
                # At three objectives the simplex lattice gives 91 vectors for 100 requested.
                reference_vector_options=ReferenceVectorOptions(
                    adaptation_frequency=0,
                    creation_type="simplex",
                    vector_type="planar",
                    lattice_resolution=None,
                    number_of_vectors=100,
                ),
                neighbourhood_size=20,
                neighbourhood_probability=1.0,
                max_replacements=None,
                aggregation="tchebycheff",
            ),
            # The population is drawn uniformly at random; the template sets its size to the number
            # of weight vectors.
            generator=RandomGeneratorOptions(
                name="RandomGenerator",
                n_points=100,
            ),
            repair=ClipRepairOptions(),
            # The paper runs 250 generations. Each generation spends one evaluation per weight vector.
            termination=MaxGenerationsTerminatorOptions(
                name="MaxGenerationsTerminator",
                max_generations=100,
            ),
            use_archive=True,
            verbosity=2,
            seed=42,
        ),
    )


def moead_de_options() -> EMOOptions:
    """Get default MOEA/D-DE options as a Pydantic model.

    MOEA/D with a differential evolution operator whose base vector is the subproblem's own solution,
    mating with the whole population with probability 1 - delta, and at most n_r replacements per
    offspring.

    The paper resets a variable that leaves its bounds to a random value inside them (Step 2.3). This
    configuration clips it instead, as DESDEO's differential evolution operator, PlatEMO and jMetal
    all do.

    References:
        H. Li and Q. Zhang, "Multiobjective Optimization Problems With Complicated Pareto Sets, MOEA/D and
        NSGA-II," IEEE Transactions on Evolutionary Computation, vol. 13, no. 2, pp. 284-302, Apr. 2009,
        doi: 10.1109/TEVC.2008.925798.

    Returns:
        EMOOptions: The default MOEA/D-DE options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=TemplateMOEADOptions(
            algorithm_name="MOEA/D-DE",
            crossover=DifferentialEvolutionCrossoverOptions(
                name="DifferentialEvolutionCrossover",
                scaling_factor=0.5,
                xover_probability=1.0,
                base_vector="target",  # Step 2.2 sets r1 = i
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,  # p_m = 1/n
            ),
            selection=MOEADSelectorOptions(
                name="MOEADSelector",
                # The paper uses N = 300 weight vectors at two objectives (H = 299) and 595 at three
                # (H = 33), on problems built to be hard to converge on.
                reference_vector_options=ReferenceVectorOptions(
                    adaptation_frequency=0,
                    creation_type="simplex",
                    vector_type="planar",
                    lattice_resolution=None,
                    number_of_vectors=100,
                ),
                neighbourhood_size=20,
                neighbourhood_probability=0.9,
                max_replacements=2,
                aggregation="tchebycheff",
            ),
            generator=RandomGeneratorOptions(
                name="RandomGenerator",
                n_points=100,
            ),
            repair=ClipRepairOptions(),
            # The paper runs 500 generations.
            termination=MaxGenerationsTerminatorOptions(
                name="MaxGenerationsTerminator",
                max_generations=100,
            ),
            use_archive=True,
            verbosity=2,
            seed=42,
        ),
    )


def spea2_options() -> EMOOptions:
    """Get default SPEA2 options as a Pydantic model.

    The archive is the selected population, of size `population_size`, and the mating tournament
    fills a population of `winner_size` from it. The paper's continuous experiments set both to 100
    and use SBX with eta = 20 and polynomial mutation; it does not state their rates, so the values
    here are the ones DESDEO uses for NSGA-II and IBEA.

    References:
        E. Zitzler, M. Laumanns and L. Thiele, "SPEA2: Improving the Strength Pareto Evolutionary Algorithm," TIK-Report
        103, Computer Engineering and Networks Laboratory (TIK), ETH Zurich, May 2001, doi: 10.3929/ethz-a-004284029.

    Returns:
        EMOOptions: The default SPEA2 options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=Template2Options(
            algorithm_name="SPEA2",
            crossover=SimulatedBinaryCrossoverOptions(
                name="SimulatedBinaryCrossover",
                xover_distribution=20,
                pair_xover_probability=1.0,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,
            ),
            selection=SPEA2SelectorOptions(
                name="SPEA2Selector",
                population_size=100,  # the archive size, N-bar
            ),
            # Step 5: binary tournament with replacement on the archive fills the mating pool of N.
            mate_selection=TournamentSelectionOptions(
                name="TournamentSelection",
                tournament_size=2,
                winner_size=100,
            ),
            generator=LHSGeneratorOptions(
                name="LHSGenerator",
                n_points=100,
            ),
            repair=ClipRepairOptions(),
            termination=MaxGenerationsTerminatorOptions(
                name="MaxGenerationsTerminator",
                max_generations=100,
            ),
            use_archive=True,
            verbosity=2,
            seed=42,
        ),
    )


def agemoea2_options() -> EMOOptions:
    """Get default AGE-MOEA-II options as a Pydantic model.

    Not AGE-MOEA: the paper below compares the two on 17 WFG and SMOP problems at 3, 6 and 9
    objectives, and AGE-MOEA-II is significantly better on 41 of the 51 cases and worse on 2.

    References:
        A. Panichella, "An Improved Pareto Front Modeling Algorithm for Large-scale Many-Objective Optimization," in
        Proceedings of the Genetic and Evolutionary Computation Conference (GECCO '22), Boston, MA, USA: ACM, Jul. 2022,
        pp. 565-573, doi: 10.1145/3512290.3528732.

        A. Panichella, "An Adaptive Evolutionary Algorithm based on Non-Euclidean Geometry for Many-objective
        Optimization," in Proceedings of the Genetic and Evolutionary Computation Conference (GECCO '19), Prague, Czech
        Republic: ACM, Jul. 2019, pp. 595-603, doi: 10.1145/3321707.3321839.

    Returns:
        EMOOptions: The default AGE-MOEA-II options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=Template2Options(
            algorithm_name="AGE-MOEA-II",
            crossover=SimulatedBinaryCrossoverOptions(
                name="SimulatedBinaryCrossover",
                xover_distribution=30,  # eta_c = 30, Table 1
                # Table 1's p_c = 1 is per pair; the per-variable rate is Deb and Agrawal's 0.5.
                pair_xover_probability=1.0,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,  # eta_m = 20, Table 1
                mutation_probability=None,  # p_m = 1/n
            ),
            selection=AGEMOEA2SelectorOptions(
                name="AGEMOEA2Selector",
                # Table 1 uses 200, 300 and 400 solutions at 3, 6 and 9 objectives.
                population_size=100,
            ),
            # AGE-MOEA's binary tournament, by front and then survival score (2019, Section 3.1).
            mate_selection=TournamentSelectionOptions(
                name="TournamentSelection",
                tournament_size=2,
                winner_size=100,
            ),
            generator=RandomGeneratorOptions(
                name="RandomGenerator",
                n_points=100,
            ),
            repair=ClipRepairOptions(),
            # Table 1 runs 200 iterations.
            termination=MaxGenerationsTerminatorOptions(
                name="MaxGenerationsTerminator",
                max_generations=100,
            ),
            use_archive=True,
            verbosity=2,
            seed=42,
        ),
    )


def hype_options() -> EMOOptions:
    """Get default HypE options as a Pydantic model.

    The paper's experiments use a population of 50, 10 000 Monte Carlo samples, SBX with eta = 20 and
    polynomial mutation, with the rates of Deb et al.'s DTLZ study (crossover 1.0 per pair, mutation
    1/n). The hypervolume fitness is exact up to three objectives.

    References:
        J. Bader and E. Zitzler, "HypE: An Algorithm for Fast Hypervolume-Based Many-Objective Optimization,"
        Evolutionary Computation, vol. 19, no. 1, pp. 45-76, Mar. 2011, doi: 10.1162/EVCO_a_00009. Implemented from
        the technical report version, TIK Report 286, ETH Zurich, 2008, doi: 10.3929/ethz-a-005703480.

    Returns:
        EMOOptions: The default HypE options as a Pydantic model.
    """
    return EMOOptions(
        preference=None,
        template=Template2Options(
            algorithm_name="HypE",
            crossover=SimulatedBinaryCrossoverOptions(
                name="SimulatedBinaryCrossover",
                xover_distribution=20,
                pair_xover_probability=1.0,
                xover_probability=0.5,
                uniform_xover_probability=0.5,
            ),
            mutation=BoundedPolynomialMutationOptions(
                name="BoundedPolynomialMutation",
                distribution_index=20,
                mutation_probability=None,
            ),
            selection=HypESelectorOptions(
                name="HypESelector",
                population_size=50,
                n_samples=10_000,
                exact_max_objectives=3,
                normalised_reference_point_component=1.1,
            ),
            mate_selection=TournamentSelectionOptions(
                name="TournamentSelection",
                tournament_size=2,
                winner_size=50,
            ),
            generator=RandomGeneratorOptions(
                name="RandomGenerator",
                n_points=50,
            ),
            repair=ClipRepairOptions(),
            # The paper runs 200 generations.
            termination=MaxGenerationsTerminatorOptions(
                name="MaxGenerationsTerminator",
                max_generations=100,
            ),
            use_archive=True,
            verbosity=2,
            seed=42,
        ),
    )


def _mixed_integer(options: EMOOptions, algorithm_name: str) -> EMOOptions:
    """Swap a continuous configuration's variation and initialization for the mixed-integer operators."""
    template = options.template
    template.algorithm_name = algorithm_name
    template.crossover = UniformMixedIntegerCrossoverOptions()
    template.mutation = MixedIntegerRandomMutationOptions()
    template.generator = RandomMixedIntegerGeneratorOptions(n_points=template.generator.n_points)
    template.repair = NoRepairOptions(name="NoRepair")
    return options


def moead_mixed_integer_options() -> EMOOptions:
    """Get default MOEA/D options for mixed integer problems as a Pydantic model.

    References:
        Q. Zhang and H. Li, "MOEA/D: A Multiobjective Evolutionary Algorithm Based on Decomposition," IEEE
        Transactions on Evolutionary Computation, vol. 11, no. 6, pp. 712-731, Dec. 2007,
        doi: 10.1109/TEVC.2007.892759.

    Returns:
        EMOOptions: The default MOEA/D mixed integer options as a Pydantic model.
    """
    return _mixed_integer(moead_options(), "MOEA/D_Mixed_Integer")


def spea2_mixed_integer_options() -> EMOOptions:
    """Get default SPEA2 options for mixed integer problems as a Pydantic model.

    References:
        E. Zitzler, M. Laumanns and L. Thiele, "SPEA2: Improving the Strength Pareto Evolutionary Algorithm," TIK-Report
        103, Computer Engineering and Networks Laboratory (TIK), ETH Zurich, May 2001, doi: 10.3929/ethz-a-004284029.

    Returns:
        EMOOptions: The default SPEA2 mixed integer options as a Pydantic model.
    """
    return _mixed_integer(spea2_options(), "SPEA2_Mixed_Integer")


def agemoea2_mixed_integer_options() -> EMOOptions:
    """Get default AGE-MOEA-II options for mixed integer problems as a Pydantic model.

    References:
        A. Panichella, "An Improved Pareto Front Modeling Algorithm for Large-scale Many-Objective Optimization," in
        Proceedings of the Genetic and Evolutionary Computation Conference (GECCO '22), Boston, MA, USA: ACM, Jul. 2022,
        pp. 565-573, doi: 10.1145/3512290.3528732.

    Returns:
        EMOOptions: The default AGE-MOEA-II mixed integer options as a Pydantic model.
    """
    return _mixed_integer(agemoea2_options(), "AGE-MOEA-II_Mixed_Integer")


def hype_mixed_integer_options() -> EMOOptions:
    """Get default HypE options for mixed integer problems as a Pydantic model.

    References:
        J. Bader and E. Zitzler, "HypE: An Algorithm for Fast Hypervolume-Based Many-Objective Optimization,"
        Evolutionary Computation, vol. 19, no. 1, pp. 45-76, Mar. 2011, doi: 10.1162/EVCO_a_00009.

    Returns:
        EMOOptions: The default HypE mixed integer options as a Pydantic model.
    """
    return _mixed_integer(hype_options(), "HypE_Mixed_Integer")


# The serialized templates under `datasets/emoTemplates` are regenerated by
# `python -m desdeo.emo.options.generate_templates`. That code cannot live in a `__main__` block
# here: `desdeo/emo/__init__.py` imports this module eagerly, so running it with `-m` would execute
# it a second time as `__main__` and make `runpy` warn about unpredictable behaviour.
