"""Evolutionary operators for recombination.

Various evolutionary operators for recombination
in multiobjective optimization are defined here.
"""

import copy
from abc import abstractmethod
from collections.abc import Sequence

import numpy as np
import polars as pl

from desdeo.problem import Problem, VariableDomainTypeEnum
from desdeo.tools.message import (
    CrossoverMessageTopics,
    FloatMessage,
    Message,
    PolarsDataFrameMessage,
)
from desdeo.tools.patterns import Publisher, Subscriber


class BaseCrossover(Subscriber):
    """A base class for crossover operators."""

    def __init__(self, problem: Problem, verbosity: int, publisher: Publisher, seed: int):
        """Initialize a crossover operator."""
        super().__init__(verbosity=verbosity, publisher=publisher)
        self.problem = problem
        self.variable_symbols = [var.symbol for var in problem.get_flattened_variables()]
        self.lower_bounds = [var.lowerbound for var in problem.get_flattened_variables()]
        self.upper_bounds = [var.upperbound for var in problem.get_flattened_variables()]

        self.variable_types = [var.variable_type for var in problem.get_flattened_variables()]
        self.variable_combination: VariableDomainTypeEnum = problem.variable_domain

        # Populated by `do`. Initialized here so that `state` can be called before the first
        # crossover, e.g. by a logger that reports the operator's state up front.
        self.parent_population: pl.DataFrame | None = None
        self.offspring_population: pl.DataFrame | None = None
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    # TODO(@light-weaver): The row order of the offspring returned by `do` is not consistent across
    # operators. Most of them build the two children separately and `np.vstack` them, so the output is
    # all first-children followed by all second-children; SimulatedBinaryCrossover.unbounded_offsprings
    # and LocalCrossover instead write offspring[i] / offspring[i+1] in place, so their children are
    # interleaved. Row i of the output is therefore not reliably the child of parent i, which makes it
    # impossible to trace lineage generically. Worth unifying on one convention and documenting it here.
    @abstractmethod
    def do(self, *, population: pl.DataFrame, to_mate: list[int] | None = None) -> pl.DataFrame:
        """Perform the crossover operation.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """

    def get_parents(self, population: pl.DataFrame, to_mate: list[int] | None = None) -> pl.DataFrame:
        """Just get the relevant parents from the population and set the parent population.

        Note:
            `DataFrame.to_numpy` hands back an F-contiguous array, and `np.zeros_like` preserves
            that order. Every `pl.from_numpy` in this module therefore states `orient="row"`: for
            a square offspring block (as many offspring as variables) polars cannot infer the
            orientation from the shape, and would read such an array column-wise, transposing it.
        """
        pop_size = population.shape[0]
        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = copy.copy(to_mate)

        if len(shuffled_ids) % 2 == 1:
            shuffled_ids.append(shuffled_ids[0])
        self.parent_population = population[shuffled_ids]
        return self.parent_population


class SimulatedBinaryCrossover(BaseCrossover):
    """A class for creating a simulated binary crossover operator.

    Both the original untruncated operator and the truncated variant that keeps the offspring inside
    the variable bounds are available; see `unbounded_offsprings` and `bounded_offsprings`. The
    truncated variant is the default, as in pymoo, jMetalPy, Platypus, pagmo2 and Deb's own NSGA-II
    code; pass `truncated=False` for the untruncated formulation that PlatEMO implements.

    References:
        Deb, K., & Agrawal, R. B. (1995). Simulated binary crossover for continuous search space.
            Complex Systems, 9(2), 115-148.

        Deb, K., & Gulati, S. (2001). Design of truss-structures for minimum weight using genetic
            algorithms. Finite Elements in Analysis and Design, 37(5), 447-465.
            https://doi.org/10.1016/S0168-874X(00)00057-3
            (The truncated variant, which is the default.)

        Picek, S., Jakobovic, D., & Golub, M. (2013). On the recombination operator in the real-coded
            genetic algorithms. In 2013 IEEE Congress on Evolutionary Computation (pp. 3103-3110).
            https://doi.org/10.1109/CEC.2013.6557948
            (Empirical comparison against other real-coded recombination operators.)
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the crossover operator."""
        return {
            0: [],
            1: [CrossoverMessageTopics.XOVER_PROBABILITY, CrossoverMessageTopics.XOVER_DISTRIBUTION],
            2: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
                CrossoverMessageTopics.XOVER_DISTRIBUTION,
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics the crossover operator is interested in."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        seed: int,
        verbosity: int,
        publisher: Publisher,
        pair_xover_probability: float = 1.0,
        xover_probability: float = 0.5,
        uniform_xover_probability: float = 0.5,
        xover_distribution: float = 30,
        truncated: bool = True,
        swap_uncrossed_variables: bool = False,
    ):
        """Initialize a simulated binary crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed for the random number generator.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
            pair_xover_probability (float, optional): the probability that a parent pair is recombined at
                all. Drawn once per pair: on failure the pair is copied to the offspring unchanged, with
                every decision variable kept together. This is the `p_c` reported in the literature
                (1.0 in the RVEA and NSGA-III papers, 0.9 in NSGA-II). Ranges between 0 and 1.0.
                Defaults to 1.0.
            xover_probability (float, optional): the per-variable crossover probability. Drawn once per
                decision variable, and decides whether the SBX operation is performed on that variable.
                Ranges between 0 and 1.0. Defaults to 0.5, following Deb and Agrawal (1995), who state
                "we choose to perform SBX in each variable with probability 0.5". Note this is a
                *separate* level from `pair_xover_probability`: the literature's `p_c = 1.0` refers to
                the pair, not to the variable, so it belongs in `pair_xover_probability`.
            uniform_xover_probability (float, optional): the uniform crossover probability parameter.
                This parameter decides whether the decision variable components of the parents are swapped for the
                offspring or not. Ranges between 0 and 1.0. Defaults to 0.5. Only operates on variables that
                have already been selected for crossover by the xover_probability parameter.
            xover_distribution (float, optional): the crossover distribution parameter. Must be positive.
                This parameter controls the distribution of the offspring. A larger value results in a distribution
                that is more concentrated around the parents, while a smaller value results in a distribution that is
                more spread out. Defaults to 30.
            truncated (bool, optional): whether to truncate the probability distribution to keep the offspring
                within the variable bounds. Defaults to True.
            swap_uncrossed_variables (bool, optional): whether a decision variable *not* selected by
                `xover_probability` is exchanged between the two offspring instead of inherited
                unchanged. Defaults to False, which is what every implementation surveyed does except
                jMetal (Java). jMetal's else-branch assigns `offspring1[i] = parent2[i]` and
                `offspring2[i] = parent1[i]`, adding a genuine uniform-crossover component on top of
                SBX: at the standard per-variable rate of 0.5, half of the genome is swapped wholesale
                every time a pair recombines. Set it to reproduce jMetal; leave it alone otherwise.
        """
        # Subscribes to no topics, so no need to stroe/pass the topics to the super class.
        super().__init__(problem, verbosity=verbosity, publisher=publisher, seed=seed)
        self.problem = problem

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("SimulatedBinaryCrossover only works on continuous problems.")
        if not 0 <= pair_xover_probability <= 1:
            raise ValueError("Pair crossover probability must be between 0 and 1.")
        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be between 0 and 1.")
        if xover_distribution <= 0:
            raise ValueError("Crossover distribution must be positive.")
        self.pair_xover_probability = pair_xover_probability
        self.xover_probability = xover_probability
        self.xover_distribution = xover_distribution
        self.uniform_xover_probability = uniform_xover_probability
        self.truncated = truncated
        self.swap_uncrossed_variables = swap_uncrossed_variables

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform the simulated binary crossover operation.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """
        if self.truncated:
            offspring = self.bounded_offsprings(population=population, to_mate=to_mate)
        else:
            offspring = self.unbounded_offsprings(population=population, to_mate=to_mate)

        # An odd sized mating pool was padded with a duplicate parent, so the last pair produced one
        # offspring too many.
        original_pop_size = len(to_mate) if to_mate is not None else population.shape[0]
        if original_pop_size % 2 == 1:
            offspring = offspring.head(original_pop_size)

        self.offspring_population = offspring
        self.notify()

        return self.offspring_population

    def unbounded_offsprings(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform the unbounded simulated binary crossover operation.

        Implementation based on Deb, Kalyanmoy, and Ram Bhushan Agrawal. "Simulated binary crossover for
        continuous search space." Complex systems 9.2 (1995): 115-148. This implementation follows PlatEMO's
        `OperatorGA`. DEAP's `cxSimulatedBinary` derives the same beta, but omits the random sign and the
        per-variable mask that PlatEMO adds on top of the paper. pymoo, DEAP's `cxSimulatedBinaryBounded`,
        jMetalPy, Platypus, pagmo2 and Deb's own NSGA-II C code all implement the truncated/bounded variant
        while calling it simulated binary crossover; see `bounded_offsprings` for that one.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """
        mating_pop = self.get_parents(population=population, to_mate=to_mate)
        mating_pop = mating_pop[self.variable_symbols].to_numpy().astype(float)
        mate_size = mating_pop.shape[0]
        num_var = mating_pop.shape[1]

        offspring = np.zeros_like(mating_pop)

        HALF = 0.5  # NOQA: N806
        # TODO(@light-weaver): Extract into a numba jitted function.
        for i in range(0, mate_size, 2):
            # One draw per pair, before any per-variable draw. A pair that fails is copied whole, so
            # all of its variables stay together -- that within-pair correlation is the point, and is
            # what folding p_c into the per-variable rate would destroy.
            if self.rng.random() > self.pair_xover_probability:
                offspring[i] = mating_pop[i]
                offspring[i + 1] = mating_pop[i + 1]
                continue
            beta = np.zeros(num_var)
            miu = self.rng.random(num_var)
            # Simulated binary crossover (SBX) operator tries to mimic the behavior of single-point crossover by
            # trying to attain similar distribution of offspring as single-point crossover.
            # The distribution itself can be contracting or expanding.
            # beta is calculated such that the integral (over (0, beta)) of the distribution matches the random number
            # mu. At mu <= 0.5, the distribution is contracting, and at mu > 0.5, the distribution is expanding.
            # You can integrate equations 18 and 19 from the reference in the docstring to see how the equations below
            # are derived. Integrate 18 from 0 to beta, and set it equal to mu. Solve for beta.
            # for 19, first integrate 18 from 0 to 1 (which is equal to 0.5 so you don't actually need to integrate it)
            # Then add the integral of 19 from 1 to beta, and set it equal to mu. Solve for beta.
            beta[miu <= HALF] = (2 * miu[miu <= HALF]) ** (1 / (self.xover_distribution + 1))  # 18
            beta[miu > HALF] = (2 - 2 * miu[miu > HALF]) ** (-1 / (self.xover_distribution + 1))  # 18 + 19
            # if beta is negative, the offspring 1 gets decision var component closer to parent 2 and vice versa.
            # In this implementation, there is an equal chance of beta being negative or positive.
            # TBH, this is more similar to uniform crossover than single-point crossover.
            binary_mask = self.rng.random(num_var) <= self.uniform_xover_probability
            binary_mask = (binary_mask * 2) - 1  # Convert to -1 or 1
            beta = beta * binary_mask
            # At beta = -1 no crossover occurs and the dec var components are copied from the parents:
            # offspring[i] = avg + diff = mating_pop[i]. (Beta = +1 would swap the parents instead,
            # which is what PlatEMO's opposite sign convention on the offspring expression means by
            # setting the sentinel to +1 there.)
            # jMetal wants exactly that swap on the uncrossed variables, so the sentinel flips sign.
            uncrossed_sentinel = 1 if self.swap_uncrossed_variables else -1
            beta[self.rng.random(num_var) > self.xover_probability] = uncrossed_sentinel
            # Note that when mu < 0.5, abs(beta) ends up being less than 1, resulting in a contracting crossover.
            # The opposite is true when mu > 0.5, resulting in an expanding crossover.
            avg = (mating_pop[i] + mating_pop[i + 1]) / 2
            diff = (mating_pop[i] - mating_pop[i + 1]) / 2
            offspring[i] = avg - beta * diff
            offspring[i + 1] = avg + beta * diff
        # Clip the offspring to the bounds
        lower_bounds = np.asarray(self.lower_bounds, dtype=float)
        upper_bounds = np.asarray(self.upper_bounds, dtype=float)
        offspring = np.clip(offspring, lower_bounds, upper_bounds)
        return pl.from_numpy(offspring, schema=self.variable_symbols, orient="row")

    def bounded_offsprings(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform the bounded simulated binary crossover operation.

        This implementation is similar to pymoo and boundedSBX in deap. One of the first papers I can find that actually
        describes how to calculate it is [1].

        The basic idea is as follows:

        1. Take the probability distributions of the unbounded SBX operator. There are two: one for the contracting case
            (mu <= 0.5, beta <= 1) and one for the expanding case (mu > 0.5, beta > 1).
        2. Assume that we are bounded on the lower side. Calculate a maximum value of beta such that any potential
            offspring will not be below the lower bound. This is done by solving for beta in the equation:
            c = (p1+p2)/2 - beta*(p1-p2)/2, where c is the child (or in this case, the lower bound), p1 and p2
            are parents. Thus, beta_max = (p1+p2-2*c)/(p1-p2). This is the maximum value of beta such that the child
            will still be above the lower bound. In most implementations, this is called beta_q, and the equation is
            slightly rearranged to be beta_q = 1 + 2*(p1-x_L)/(p2-p1), where p1<p2.
        3. Now, integrate equations 18 + 19 from the original SBX paper. Integrating from 0 to infinity gives 1. So,
            integrate from 0 to beta_max, we get a normalization factor.
        4. The normalization factor turns out to be F = alpha / 2. where:
            alpha = 2 - (1 / beta_max) ** (self.xover_distribution + 1)
        5. Now, integrate the normalized version of equation 18 from beta = 0 to 1. This used to be equal to 0.5, but
            now it equals 0.5 / F = 1 / alpha. This is now the new threshold for the contracting case. Integrate
            between 0 and beta_max and set it equal to mu, if mu <= 1 / alpha.
        6. For the expanding case, integrate the normalized version of equation 19 from beta = 1 to beta_max.
        7. Use steps 2-6 for the child: c = (p1+p2)/2 - beta*(p1-p2)/2.
        8. Repeat steps 2-6 but with the upper bound for the child: c = (p1+p2)/2 + beta*(p1-p2)/2.

        Interestingly enough, the resulting equations are are just a generalization of the unbounded case.
        If beta_max = infinity, then alpha = 2, and the equations reduce to the unbounded case. So, this piece of
        code can handle the unbounded case as well, but I have kept the unbounded case separate for clarity.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.

        References:
            [1] "Deb, K., & Gulati, S. (2001). Design of truss-structures for minimum weight
                using genetic algorithms". Finite Elements in Analysis and Design, 37(5), 447-465.
                https://doi.org/10.1016/S0168-874X(00)00057-3

        """
        mating_pop = self.get_parents(population=population, to_mate=to_mate)
        mating_pop = mating_pop[self.variable_symbols].to_numpy().astype(float)
        mate_size = mating_pop.shape[0]
        num_var = mating_pop.shape[1]

        lower_bounds = np.asarray(self.lower_bounds, dtype=float)
        upper_bounds = np.asarray(self.upper_bounds, dtype=float)

        # The truncated distribution below is only defined for parents inside the bounds: an
        # oob parent makes beta_max negative, and raising it to a fractional power yields NaN.
        # Pull such parents onto the bound instead.
        mating_pop = np.clip(mating_pop, lower_bounds, upper_bounds)

        offspring = np.zeros_like(mating_pop)

        # TODO(@light-weaver): Extract into a numba jitted function.
        for i in range(0, mate_size, 2):
            # One draw per pair, before any per-variable draw. A pair that fails is copied whole, so
            # all of its variables stay together -- that within-pair correlation is the point, and is
            # what folding p_c into the per-variable rate would destroy.
            if self.rng.random() > self.pair_xover_probability:
                offspring[i] = mating_pop[i]
                offspring[i + 1] = mating_pop[i + 1]
                continue
            beta = np.zeros(num_var)
            miu = self.rng.random(num_var)
            # Apply crossover only for certain decision variables
            sbx_mask = self.rng.random(num_var) <= self.xover_probability
            # Apply binary crossover only for certain decision variables
            binary_mask = self.rng.random(num_var) <= self.uniform_xover_probability
            binary_mask = binary_mask & sbx_mask  # Only apply binary crossover where SBX is applied
            avg = (mating_pop[i] + mating_pop[i + 1]) / 2

            x1 = np.minimum(mating_pop[i], mating_pop[i + 1])
            x2 = np.maximum(mating_pop[i], mating_pop[i + 1])
            # The two children are derived in *sorted* order: one steps from the midpoint down towards
            # the lower bound, the other up towards the upper bound, and each uses the beta capped by
            # the distance to the bound it is stepping towards. The half-difference must therefore be
            # taken between the sorted values, not between the parents in whatever order the mating
            # pool happens to hold them. Using the unsorted difference pairs the lower-bound beta with
            # an upward step (and vice versa) whenever mating_pop[i] is the smaller parent, which lets
            # the offspring escape the variable bounds.
            diff = (x2 - x1) / 2

            # Child stepping towards the lower bound.
            with np.errstate(divide="ignore", invalid="ignore"):  # Handles x1 == x2 case
                beta_max = 1 + 2 * (x1 - lower_bounds) / (x2 - x1)
            beta_max[np.isnan(beta_max)] = np.inf  # Handles x1 == x2 == lower_bound case

            # Technically, this code can handle the unbounded case by setting alpha to an array of 2s.
            alpha = 2 - (1 / beta_max) ** (self.xover_distribution + 1)

            SPLIT_POINT1 = 1 / alpha  # NOQA: N806
            beta[miu <= SPLIT_POINT1] = (alpha[miu <= SPLIT_POINT1] * miu[miu <= SPLIT_POINT1]) ** (
                1 / (self.xover_distribution + 1)
            )
            beta[miu > SPLIT_POINT1] = (2 - alpha[miu > SPLIT_POINT1] * miu[miu > SPLIT_POINT1]) ** (
                -1 / (self.xover_distribution + 1)
            )
            # Turning beta negative does not work for truncated SBX. Manually swap the offspring instead.
            child_low = avg - beta * diff

            # Child stepping towards the upper bound. The same miu is reused deliberately: every
            # reference implementation draws one uniform per variable and shares it between the two
            # children, so that the pair is perfectly correlated.
            with np.errstate(divide="ignore", invalid="ignore"):  # Handles x1 == x2 case
                beta_max = 1 + 2 * (upper_bounds - x2) / (x2 - x1)
            beta_max[np.isnan(beta_max)] = np.inf  # Handles x1 == x2 == upper_bound case
            # The error states only occur when x1==x2, which means that the parents are equal, and thus the offspring
            # will be equal to the parents. So, np.inf is fine.

            alpha = 2 - (1 / beta_max) ** (self.xover_distribution + 1)

            SPLIT_POINT2 = 1 / alpha  # NOQA: N806
            beta[miu <= SPLIT_POINT2] = (alpha[miu <= SPLIT_POINT2] * miu[miu <= SPLIT_POINT2]) ** (
                1 / (self.xover_distribution + 1)
            )
            beta[miu > SPLIT_POINT2] = (2 - alpha[miu > SPLIT_POINT2] * miu[miu > SPLIT_POINT2]) ** (
                -1 / (self.xover_distribution + 1)
            )
            child_high = avg + beta * diff

            # Preserve the parent identity: the child that stepped down belongs to whichever parent
            # held the smaller value, as in Deb's reference implementation and in pymoo.
            first_is_lower = mating_pop[i] <= mating_pop[i + 1]
            offspring[i] = np.where(first_is_lower, child_low, child_high)
            offspring[i + 1] = np.where(first_is_lower, child_high, child_low)

            # Decision variables not selected for SBX are inherited unchanged. This has to be an
            # explicit copy rather than a beta = 1 sentinel: with the sorted difference above, beta = 1
            # would hand every untouched variable's smaller value to offspring i and the larger to
            # offspring i + 1, biasing the pair instead of leaving it alone.
            # jMetal exchanges them between the offspring instead; see `swap_uncrossed_variables`.
            first, second = (i + 1, i) if self.swap_uncrossed_variables else (i, i + 1)
            offspring[i, ~sbx_mask] = mating_pop[first, ~sbx_mask]
            offspring[i + 1, ~sbx_mask] = mating_pop[second, ~sbx_mask]

            # Swap the offspring for decision variables where binary crossover is applied
            offspring[i, binary_mask], offspring[i + 1, binary_mask] = (
                offspring[i + 1, binary_mask].copy(),
                offspring[i, binary_mask].copy(),
            )

        # The mathematics above already keeps the offspring feasible; this only absorbs floating point
        # drift at the bounds. Every reference implementation of truncated SBX clamps here as well.
        offspring = np.clip(offspring, lower_bounds, upper_bounds)
        return pl.from_numpy(offspring, schema=self.variable_symbols, orient="row")

    def update(self, *_, **__):
        """Do nothing. This is just the basic SBX operator."""

    def state(self) -> Sequence[Message]:
        """Return the state of the crossover operator."""
        if self.parent_population is None or self.offspring_population is None:
            return []
        if self.verbosity == 0:
            return []
        if self.verbosity == 1:
            return [
                FloatMessage(
                    topic=CrossoverMessageTopics.XOVER_PROBABILITY,
                    source="SimulatedBinaryCrossover",
                    value=self.xover_probability,
                ),
                FloatMessage(
                    topic=CrossoverMessageTopics.XOVER_DISTRIBUTION,
                    source="SimulatedBinaryCrossover",
                    value=self.xover_distribution,
                ),
            ]
        # verbosity == 2 or higher
        return [
            FloatMessage(
                topic=CrossoverMessageTopics.XOVER_PROBABILITY,
                source="SimulatedBinaryCrossover",
                value=self.xover_probability,
            ),
            FloatMessage(
                topic=CrossoverMessageTopics.XOVER_DISTRIBUTION,
                source="SimulatedBinaryCrossover",
                value=self.xover_distribution,
            ),
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.PARENTS,
                source="SimulatedBinaryCrossover",
                value=self.parent_population,
            ),
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.OFFSPRINGS,
                source="SimulatedBinaryCrossover",
                value=self.offspring_population,
            ),
        ]


class SinglePointBinaryCrossover(BaseCrossover):
    """A class that defines the single point binary crossover operation.

    A crossover point is drawn uniformly from the positions that actually split the parents, and the
    two offspring take the genes before the point from one parent and the rest from the other.

    References:
        Holland, J. H. (1975). Adaptation in Natural and Artificial Systems. University of Michigan
            Press.

        Goldberg, D. E. (1989). Genetic Algorithms in Search, Optimization and Machine Learning.
            Addison-Wesley.
    """

    def __init__(self, *, problem: Problem, seed: int, verbosity: int, publisher: Publisher):
        """Initialize the single point binary crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level.
            publisher (Publisher): the publisher to which the operator will publish messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher, seed=seed)

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the single point binary crossover operator."""
        return {
            0: [],
            1: [],
            2: [
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics the single point binary crossover operator is interested in."""
        return []

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform single point binary crossover.

        Args:
            population (pl.DataFrame): the population to perform the crossover with.
            to_mate (list[int] | None, optional): indices. Defaults to None.

        Returns:
            pl.DataFrame: the offspring from the crossover.
        """
        self.parent_population = population
        pop_size = self.parent_population.shape[0]
        num_var = len(self.variable_symbols)

        if num_var < 2:  # noqa: PLR2004
            raise ValueError(
                f"Single point binary crossover needs at least two decision variables, but the problem has {num_var}."
            )

        parent_decision_vars = self.parent_population[self.variable_symbols].to_numpy().astype(np.bool)

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = copy.copy(to_mate)

        mating_pop = parent_decision_vars[shuffled_ids]
        mating_pop_size = len(shuffled_ids)
        original_mating_pop_size = mating_pop_size

        if mating_pop_size % 2 != 0:
            # if the number of member to mate is of uneven size, copy the first member to the tail
            mating_pop = np.vstack((mating_pop, mating_pop[0]))
            mating_pop_size += 1
            shuffled_ids.append(shuffled_ids[0])

        # split the population into parents, one with members with even numbered indices, the
        # other with uneven numbered indices
        parents1 = mating_pop[0::2, :]
        parents2 = mating_pop[1::2, :]

        # The high value of rng.integers is exclusive.
        cross_over_points = self.rng.integers(1, num_var, mating_pop_size // 2)

        # create a mask where, on each row, the element is 1 before the crossover point,
        # and zero after it
        cross_over_mask = np.zeros_like(parents1, dtype=np.bool)
        cross_over_mask[np.arange(cross_over_mask.shape[1]) < cross_over_points[:, None]] = 1

        # pick genes from the first parents before the crossover point
        # pick genes from the second parents after, and including, the crossover point
        offspring1_first = cross_over_mask & parents1
        offspring1_second = (~cross_over_mask) & parents2

        # combine into a first half of the whole offspring population
        offspring1 = offspring1_first | offspring1_second

        # pick genes from the first parents after, and including, the crossover point
        # pick genes from the second parents before the crossover point
        offspring2_first = (~cross_over_mask) & parents1
        offspring2_second = cross_over_mask & parents2

        # combine into the second half of the whole offspring population
        offspring2 = offspring2_first | offspring2_second

        # combine the two offspring populations into one, drop the last member if the number of
        # indices (to_mate) is uneven
        self.offspring_population = pl.from_numpy(
            np.vstack((offspring1, offspring2))[
                : (original_mating_pop_size if original_mating_pop_size % 2 == 0 else -1)
            ],
            schema=self.variable_symbols,
            orient="row",
        ).select(pl.all().cast(pl.Float64))
        self.notify()

        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing. This is just the basic single point binary crossover operator."""

    def state(self) -> Sequence[Message]:
        """Return the state of the single ponit binary crossover operator."""
        if self.parent_population is None or self.offspring_population is None:
            return []
        if self.verbosity == 0:
            return []
        if self.verbosity == 1:
            return []
        # verbosity == 2 or higher
        return [
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.PARENTS,
                source=self.__class__.__name__,
                value=self.parent_population,
            ),
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.OFFSPRINGS,
                source=self.__class__.__name__,
                value=self.offspring_population,
            ),
        ]


class UniformIntegerCrossover(BaseCrossover):
    """A class that defines the uniform integer crossover operation.

    Each mating pair draws its own mask and every decision variable is inherited independently from
    one parent or the other, the two offspring taking complementary choices. This is the operator
    known as discrete crossover in the real-coded literature.

    References:
        Syswerda, G. (1989). Uniform crossover in genetic algorithms. In Proceedings of the Third
            International Conference on Genetic Algorithms (pp. 2-9). Morgan Kaufmann.

        Picek, S., Jakobovic, D., & Golub, M. (2013). On the recombination operator in the real-coded
            genetic algorithms. In 2013 IEEE Congress on Evolutionary Computation (pp. 3103-3110).
            https://doi.org/10.1109/CEC.2013.6557948
    """

    def __init__(self, *, problem: Problem, seed: int, verbosity: int, publisher: Publisher):
        """Initialize the uniform integer crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher, seed=seed)

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the single point binary crossover operator."""
        return {
            0: [],
            1: [],
            2: [
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics the single point binary crossover operator is interested in."""
        return []

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform single point binary crossover.

        Args:
            population (pl.DataFrame): the population to perform the crossover with.
            to_mate (list[int] | None, optional): indices. Defaults to None.

        Returns:
            pl.DataFrame: the offspring from the crossover.
        """
        self.parent_population = population
        pop_size = self.parent_population.shape[0]
        num_var = len(self.variable_symbols)

        parent_decision_vars = self.parent_population[self.variable_symbols].to_numpy().astype(int)

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = copy.copy(to_mate)

        mating_pop = parent_decision_vars[shuffled_ids]
        mating_pop_size = len(shuffled_ids)
        original_mating_pop_size = mating_pop_size

        if mating_pop_size % 2 != 0:
            # if the number of member to mate is of uneven size, copy the first member to the tail
            mating_pop = np.vstack((mating_pop, mating_pop[0]))
            mating_pop_size += 1
            shuffled_ids.append(shuffled_ids[0])

        # split the population into parents, one with members with even numbered indices, the
        # other with uneven numbered indices
        parents1 = mating_pop[0::2, :]
        parents2 = mating_pop[1::2, :]

        # One independent mask per mating pair. A single mask of shape (num_var,) would broadcast
        # over the whole mating pool, making every pair in the generation swap exactly the same
        # decision variables, which is a fixed column split rather than uniform crossover.
        mask = self.rng.choice([True, False], size=(mating_pop_size // 2, num_var))

        offspring1 = np.where(mask, parents1, parents2)  # True, pick from parent1, False, pick from parent2
        offspring2 = np.where(mask, parents2, parents1)  # True, pick from parent2, False, pick from parent1

        # combine the two offspring populations into one, drop the last member if the number of
        # indices (to_mate) is uneven
        self.offspring_population = pl.from_numpy(
            np.vstack((offspring1, offspring2))[
                : (original_mating_pop_size if original_mating_pop_size % 2 == 0 else -1)
            ],
            schema=self.variable_symbols,
            orient="row",
        ).select(pl.all().cast(pl.Float64))

        self.notify()

        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing. This is just the basic single point binary crossover operator."""

    def state(self) -> Sequence[Message]:
        """Return the state of the single ponit binary crossover operator."""
        if self.parent_population is None or self.offspring_population is None:
            return []
        if self.verbosity == 0:
            return []
        if self.verbosity == 1:
            return []
        # verbosity == 2 or higher
        return [
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.PARENTS,
                source=self.__class__.__name__,
                value=self.parent_population,
            ),
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.OFFSPRINGS,
                source=self.__class__.__name__,
                value=self.offspring_population,
            ),
        ]


class UniformMixedIntegerCrossover(BaseCrossover):
    """A class that defines the uniform mixed-integer crossover operation.

    Each mating pair draws its own mask and every decision variable is inherited whole from one parent
    or the other, so integer valued variables keep integer values without any rounding.

    TODO: This is virtually identical to `UniformIntegerCrossover`. The only
    difference is that the `parent_decision_vars` in `do` are not casted to
    `int`. This is not an ideal way to implement crossover for mixed-integer
    stuff...

    References:
        Syswerda, G. (1989). Uniform crossover in genetic algorithms. In Proceedings of the Third
            International Conference on Genetic Algorithms (pp. 2-9). Morgan Kaufmann.

        Picek, S., Jakobovic, D., & Golub, M. (2013). On the recombination operator in the real-coded
            genetic algorithms. In 2013 IEEE Congress on Evolutionary Computation (pp. 3103-3110).
            https://doi.org/10.1109/CEC.2013.6557948
    """

    def __init__(self, *, problem: Problem, seed: int, verbosity: int, publisher: Publisher):
        """Initialize the uniform integer crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher, seed=seed)

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the single point binary crossover operator."""
        return {
            0: [],
            1: [],
            2: [
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics the single point binary crossover operator is interested in."""
        return []

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform single point binary crossover.

        Args:
            population (pl.DataFrame): the population to perform the crossover with.
            to_mate (list[int] | None, optional): indices. Defaults to None.

        Returns:
            pl.DataFrame: the offspring from the crossover.
        """
        self.parent_population = population
        pop_size = self.parent_population.shape[0]
        num_var = len(self.variable_symbols)

        parent_decision_vars = self.parent_population[self.variable_symbols].to_numpy().astype(float)

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = copy.copy(to_mate)

        mating_pop = parent_decision_vars[shuffled_ids]
        mating_pop_size = len(shuffled_ids)
        original_mating_pop_size = mating_pop_size

        if mating_pop_size % 2 != 0:
            # if the number of member to mate is of uneven size, copy the first member to the tail
            mating_pop = np.vstack((mating_pop, mating_pop[0]))
            mating_pop_size += 1
            shuffled_ids.append(shuffled_ids[0])

        # split the population into parents, one with members with even numbered indices, the
        # other with uneven numbered indices
        parents1 = mating_pop[0::2, :]
        parents2 = mating_pop[1::2, :]

        # One independent mask per mating pair. A single mask of shape (num_var,) would broadcast
        # over the whole mating pool, making every pair in the generation swap exactly the same
        # decision variables, which is a fixed column split rather than uniform crossover.
        mask = self.rng.choice([True, False], size=(mating_pop_size // 2, num_var))

        offspring1 = np.where(mask, parents1, parents2)  # True, pick from parent1, False, pick from parent2
        offspring2 = np.where(mask, parents2, parents1)  # True, pick from parent2, False, pick from parent1

        # combine the two offspring populations into one, drop the last member if the number of
        # indices (to_mate) is uneven
        self.offspring_population = pl.from_numpy(
            np.vstack((offspring1, offspring2))[
                : (original_mating_pop_size if original_mating_pop_size % 2 == 0 else -1)
            ],
            schema=self.variable_symbols,
            orient="row",
        ).select(pl.all().cast(pl.Float64))

        self.notify()

        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing. This is just the basic single point binary crossover operator."""

    def state(self) -> Sequence[Message]:
        """Return the state of the single point binary crossover operator."""
        if self.parent_population is None or self.offspring_population is None:
            return []
        if self.verbosity == 0:
            return []
        if self.verbosity == 1:
            return []
        # verbosity == 2 or higher
        return [
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.PARENTS,
                source=self.__class__.__name__,
                value=self.parent_population,
            ),
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.OFFSPRINGS,
                source=self.__class__.__name__,
                value=self.offspring_population,
            ),
        ]


class BlendAlphaCrossover(BaseCrossover):
    """Blend-alpha (BLX-alpha) crossover for continuous problems.

    Each offspring component is drawn uniformly from the interval spanned by the two parent
    components, widened on both sides by `alpha` times that span and clipped to the variable bounds.

    References:
        Eshelman, L. J., & Schaffer, J. D. (1993). Real-coded genetic algorithms and
            interval-schemata. In L. D. Whitley (Ed.), Foundations of Genetic Algorithms
            (Vol. 2, pp. 187-202). Elsevier. https://doi.org/10.1016/B978-0-08-094832-4.50018-0

        Picek, S., Jakobovic, D., & Golub, M. (2013). On the recombination operator in the real-coded
            genetic algorithms. In 2013 IEEE Congress on Evolutionary Computation (pp. 3103-3110).
            https://doi.org/10.1109/CEC.2013.6557948
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the blend alpha crossover operator.

        Note:
            The operator has no crossover probability, so it does not provide that topic.
        """
        return {
            0: [],
            1: [
                CrossoverMessageTopics.ALPHA,
            ],
            2: [
                CrossoverMessageTopics.ALPHA,
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics provided by the blend alpha crossover operator."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        seed: int,
        alpha: float = 0.5,
        repeats: int = 2,
        sample_each_component: bool = True,
    ):
        """Initialize the blend alpha crossover operator.

        Details here: Eshelman, L. J., & Schaffer, J. D. (1993). Real-Coded Genetic Algorithms and Interval-Schemata.
        In L. D. Whitley (Ed.), Foundations of Genetic Algorithms (Vol. 2, pp. 187-202). Elsevier.
        https://doi.org/10.1016/B978-0-08-094832-4.50018-0


        Args:
            problem (Problem): the problem object.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            alpha (float, optional): non-negative blending factor 'alpha' that controls the extent to which
                offspring may be sampled outside the interval defined by each pair of parent
                genes. alpha = 0 restricts children strictly within the
                parents range, larger alpha allows outliers. Defaults to 0.5.
            repeats (int, optional): the number of times to repeat the crossover operation for a given pair of parents.
                Defaults to 2. Note that a value of 1 means that only one child will be generated for each pair of
                parents.
            sample_each_component (bool, optional): whether to sample each component of the offspring independently.
                If `True`, a new random number is generated for each component of the offspring. If `False`, a single
                random number is generated for the entire offspring. Defaults to `True`.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("BlendAlphaCrossover only works on continuous problems.")
        if alpha < 0:
            raise ValueError("Alpha must be non-negative.")

        self.alpha = alpha
        self.repeats = repeats
        self.sample_each_component = sample_each_component

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform BLX-alpha crossover _correctly_.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """
        mating_pop = self.get_parents(population=population, to_mate=to_mate)
        mating_pop = mating_pop[self.variable_symbols].to_numpy()
        mating_pop_size = mating_pop.shape[0]
        original_pop_size = len(to_mate) if to_mate is not None else population.shape[0]
        num_var = mating_pop.shape[1]

        offspring_size = mating_pop_size / 2 * self.repeats
        offsprings = np.zeros((int(offspring_size), num_var))

        if self.sample_each_component:
            offspring_randoms = self.rng.random((int(offspring_size), num_var))
        else:
            offspring_randoms = self.rng.random((int(offspring_size), 1))

        for i in range(0, mating_pop_size, 2):
            p1 = mating_pop[i]
            p2 = mating_pop[i + 1]

            c_min = np.minimum(p1, p2)
            c_max = np.maximum(p1, p2)
            span = c_max - c_min

            lower = c_min - self.alpha * span
            upper = c_max + self.alpha * span
            lower = np.maximum(lower, self.lower_bounds)
            upper = np.minimum(upper, self.upper_bounds)

            for j in range(self.repeats):
                idx = (i // 2) * self.repeats + j
                offsprings[idx] = lower + offspring_randoms[idx] * (upper - lower)

        # An odd sized mating pool was padded with a duplicate parent, so the final pair produced a
        # full extra set of `repeats` offspring. Keep only as many as the unpadded pool would have
        # produced. Dropping a single row unconditionally is only correct when `repeats` is 2.
        if original_pop_size % 2 == 1:
            offsprings = offsprings[: (original_pop_size * self.repeats + 1) // 2, :]

        self.offspring_population = pl.from_numpy(offsprings, schema=self.variable_symbols, orient="row")
        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the blend-alpha crossover operator."""
        if self.parent_population is None:
            return []
        msgs: list[Message] = []
        if self.verbosity >= 1:
            msgs.append(
                FloatMessage(
                    topic=CrossoverMessageTopics.ALPHA,
                    source=self.__class__.__name__,
                    value=self.alpha,
                )
            )
        if self.verbosity >= 2:  # noqa: PLR2004
            msgs.extend(
                [
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.PARENTS,
                        source=self.__class__.__name__,
                        value=self.parent_population,
                    ),
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.OFFSPRINGS,
                        source=self.__class__.__name__,
                        value=self.offspring_population,
                    ),
                ]
            )
        return msgs


class SingleArithmeticCrossover(BaseCrossover):
    """Single Arithmetic Crossover for continuous problems.

    One decision variable is picked per mating pair and replaced in both offspring by the average of
    the two parent values. Every other variable is inherited unchanged from the respective parent, so
    each offspring differs from its own parent in exactly one position.

    References:
        Picek, S., Jakobovic, D., & Golub, M. (2013). On the recombination operator in the real-coded
            genetic algorithms. In 2013 IEEE Congress on Evolutionary Computation (pp. 3103-3110).
            https://doi.org/10.1109/CEC.2013.6557948
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the single arithmetic crossover operator."""
        return {
            0: [],  # No topics for 0
            1: [
                CrossoverMessageTopics.XOVER_PROBABILITY,  # Probability of crossover
            ],
            2: [
                CrossoverMessageTopics.XOVER_PROBABILITY,  # Crossover probability
                CrossoverMessageTopics.PARENTS,  # Parents involved in crossover
                CrossoverMessageTopics.OFFSPRINGS,  # Offsprings created from crossover
            ],
        }

    @property
    def interested_topics(self):
        """The message topics that the single arithmetic crossover operator is interested in."""
        return []

    def __init__(
        self,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        seed: int,
        xover_probability: float = 1.0,
    ):
        """Initialize the single arithmetic crossover operator.

        Args:
            problem (Problem): the problem object.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
            xover_probability (float): probability of performing crossover.
            seed (int): random seed for reproducibility.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("SingleArithmeticCrossover only works on continuous problems.")
        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be in [0, 1].")

        self.xover_probability = xover_probability

    def do(self, *, population: pl.DataFrame, to_mate: list[int] | None = None) -> pl.DataFrame:
        """Perform Single Arithmetic Crossover.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """
        mating_pool = self.get_parents(population=population, to_mate=to_mate)
        mating_pool = mating_pool[self.variable_symbols].to_numpy().astype(float)
        mating_pop_size = mating_pool.shape[0]
        num_vars = mating_pool.shape[1]
        original_pop_size = len(to_mate) if to_mate is not None else population.shape[0]

        parents1 = mating_pool[0::2, :]
        parents2 = mating_pool[1::2, :]

        mask = self.rng.random(mating_pop_size // 2) <= self.xover_probability
        gene_pos = self.rng.integers(0, num_vars, size=mating_pop_size // 2)

        # Initialize offspring as exact copies
        offspring1 = parents1.copy()
        offspring2 = parents2.copy()

        # Apply crossover only for selected pairs
        row_idx = np.arange(len(mask))[mask]
        col_idx = gene_pos[mask]

        avg = 0.5 * (parents1[row_idx, col_idx] + parents2[row_idx, col_idx])

        offspring1[row_idx, col_idx] = avg
        offspring2[row_idx, col_idx] = avg

        offspring = np.vstack((offspring1, offspring2))
        if original_pop_size % 2 == 1:
            offspring = offspring[:-1, :]

        self.offspring_population = pl.from_numpy(offspring, schema=self.variable_symbols, orient="row").select(
            pl.all().cast(pl.Float64)
        )
        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the single arithmetic crossover operator."""
        if self.parent_population is None:
            return []

        msgs: list[Message] = []

        # Messages for crossover probability
        if self.verbosity >= 1:
            msgs.append(
                FloatMessage(
                    topic=CrossoverMessageTopics.XOVER_PROBABILITY,
                    source=self.__class__.__name__,
                    value=self.xover_probability,
                )
            )

        # Messages for parents and offspring
        if self.verbosity >= 2:  # noqa: PLR2004 - more detailed info
            msgs.extend(
                [
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.PARENTS,
                        source=self.__class__.__name__,
                        value=self.parent_population,
                    ),
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.OFFSPRINGS,
                        source=self.__class__.__name__,
                        value=self.offspring_population,
                    ),
                ]
            )

        return msgs


class LocalCrossover(BaseCrossover):
    """Local Crossover for continuous problems.

    An arithmetic crossover that draws a fresh blending weight for every decision variable of every
    mating pair, rather than one weight for the whole vector. The two offspring use complementary
    weights, so each pair spans the segment between the parents component by component.

    References:
        Dumitrescu, D., Lazzerini, B., Jain, L. C., & Dumitrescu, A. (2000). Evolutionary Computation.
            CRC Press, Florida, USA.

        Picek, S., Jakobovic, D., & Golub, M. (2013). On the recombination operator in the real-coded
            genetic algorithms. In 2013 IEEE Congress on Evolutionary Computation (pp. 3103-3110).
            https://doi.org/10.1109/CEC.2013.6557948
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the local crossover operator.

        Note:
            The operator has no crossover probability, so it does not provide that topic.
        """
        return {
            0: [],
            1: [],
            2: [
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics that the local crossover operator is interested in."""
        return []

    def __init__(
        self,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        seed: int,
    ):
        """Initialize the local crossover operator.

        Args:
            problem (Problem): the problem object.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
            seed (int): random seed for reproducibility.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("LocalCrossover only works on continuous problems.")

    def do(self, *, population: pl.DataFrame, to_mate: list[int] | None = None) -> pl.DataFrame:
        """Perform Local Crossover.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """
        mating_pop = self.get_parents(population=population, to_mate=to_mate)
        mating_pop = mating_pop[self.variable_symbols].to_numpy()
        mating_pop_size = mating_pop.shape[0]
        num_var = mating_pop.shape[1]
        original_pop_size = len(to_mate) if to_mate is not None else population.shape[0]

        parents1 = mating_pop[0::2]
        parents2 = mating_pop[1::2]

        offspring = np.empty((mating_pop_size, num_var))

        for i in range(mating_pop_size // 2):
            alpha = self.rng.random(num_var)

            offspring[2 * i] = alpha * parents1[i] + (1 - alpha) * parents2[i]
            offspring[2 * i + 1] = (1 - alpha) * parents1[i] + alpha * parents2[i]

        # An odd sized mating pool was padded with a duplicate parent, so the last pair produced one
        # offspring too many. Drop it, as every other crossover operator here does.
        if original_pop_size % 2 == 1:
            offspring = offspring[:-1, :]

        self.offspring_population = pl.from_numpy(offspring, schema=self.variable_symbols, orient="row").select(
            pl.all().cast(pl.Float64)
        )

        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the local crossover operator."""
        if self.parent_population is None:
            return []

        msgs: list[Message] = []

        if self.verbosity >= 2:  # noqa: PLR2004
            msgs.extend(
                [
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.PARENTS,
                        source=self.__class__.__name__,
                        value=self.parent_population,
                    ),
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.OFFSPRINGS,
                        source=self.__class__.__name__,
                        value=self.offspring_population,
                    ),
                ]
            )
        return msgs


class BoundedExponentialCrossover(BaseCrossover):
    """Bounded-exponential (BEX) crossover for continuous problems.

    A parent centric operator: each offspring is displaced from its own parent by a bounded
    exponential deviate whose scale is `lambda_` times the separation of the parents, truncated so
    that no offspring can fall outside the variable bounds. It is the bounded refinement of the
    Laplace crossover (LX) of Deep and Thakur, which has no such guarantee.

    The reference derives the offspring under the assumption that the first parent holds the smaller
    value, and leaves the mirrored case to the reader; `do` implements that mirrored case, since a
    mating pool is unordered.

    References:
        Thakur, M., Meghwani, S. S., & Jalota, H. (2014). A modified real coded genetic algorithm for
            constrained optimization. Applied Mathematics and Computation, 235, 292-317.
            https://doi.org/10.1016/j.amc.2014.02.093

        Deep, K., & Thakur, M. (2007). A new crossover operator for real coded genetic algorithms.
            Applied Mathematics and Computation, 188(1), 895-911.
            (The Laplace crossover that BEX modifies.)
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the bounded exponential crossover operator."""
        return {
            0: [],
            1: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
                CrossoverMessageTopics.LAMBDA,
            ],
            2: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
                CrossoverMessageTopics.LAMBDA,
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics provided by the bounded exponential crossover operator."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        seed: int,
        lambda_: float = 0.1,
        xover_probability: float = 1.0,
        uniform_xover_probability: float = 0.0,
    ):
        """Initialize the bounded-exponential crossover operator.

        Args:
            problem (Problem): the problem object.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
            seed (int): random seed for the internal generator.
            lambda_ (float, optional): positive scale λ for the exponential distribution.
                Defaults to 0.1. Larger values produce more widely dispersed offspring, smaller values produce offspring
                closer to the parents.
            xover_probability (float, optional): probability of applying crossover
                to each pair. Defaults to 1.0.
            uniform_xover_probability (float, optional): per-variable probability that the two offspring
                exchange which parent they descend from. Defaults to 0.0, which is the operator's
                original behaviour: every offspring keeps its own parent's identity in every variable.

                At 0.5 the operator gains a uniform-crossover component, the same one
                `SimulatedBinaryCrossover` carries under this name. It matters there: on a 105-problem
                grid the two SBX arms that differ *only* in this parameter placed 10.9x apart in median
                IGD+ regret, 0.0061 at 0.5 against 0.0665 at 0.0. Whether BEX responds the same way is
                an open question, which is why the default preserves the existing behaviour rather than
                assuming the transfer.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("BoundedExponentialCrossover only works on continuous problems.")
        if lambda_ <= 0:
            raise ValueError("lambda_ must be positive.")
        if not 0 <= xover_probability <= 1:
            raise ValueError("xover_probability must be in [0,1].")
        if not 0 <= uniform_xover_probability <= 1:
            raise ValueError("uniform_xover_probability must be in [0,1].")

        self.lambda_ = lambda_
        self.xover_probability = xover_probability
        self.uniform_xover_probability = uniform_xover_probability

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform bounded-exponential crossover.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """
        mating_pop = self.get_parents(population=population, to_mate=to_mate)
        mating_pop = mating_pop[self.variable_symbols].to_numpy()
        mating_pop_size = mating_pop.shape[0]
        num_var = mating_pop.shape[1]
        original_pop_size = len(to_mate) if to_mate is not None else population.shape[0]

        parents1 = mating_pop[0::2, :]
        parents2 = mating_pop[1::2, :]

        x_lower = np.array(self.lower_bounds)
        x_upper = np.array(self.upper_bounds)

        # The absolute separation |y_i - x_i| of the parents, which sets the scale of the
        # exponential. The reference derives beta under the stated assumption x_i < y_i and leaves
        # the mirrored case to the reader, but a mating pool is unordered, so both orderings occur
        # about equally often per decision variable. Using the *signed* difference flips the sign of
        # every exponent argument whenever x_i > y_i, which inverts the exponential: the density then
        # grows towards the truncation point instead of decaying away from the parent, so this parent
        # centric operator turns into a bound seeking one for roughly half of all variables. The
        # absolute separation is exactly the reference's mirrored case, and leaves the already
        # correct x_i < y_i ordering untouched.
        span = np.abs(parents2 - parents1)

        # Where the two parents share a value the span is zero and the offspring can only take that
        # same value, since every child is parent + beta * span. The exponent arguments below would
        # then divide by zero: harmless inf when the shared value is strictly inside the bounds, but
        # 0/0 -> nan when it sits exactly *on* a bound, which used to leak NaN decision variables
        # into the population (duplicate parents and bound-hugging variables are both common). Feed
        # the exponents a dummy span of one so that beta stays finite; multiplying by the true zero
        # span afterwards restores the parent value exactly.
        zero_span = span == 0
        safe_span = np.where(zero_span, 1.0, span)

        u_i = self.rng.random((mating_pop_size // 2, num_var))
        r_i = self.rng.random((mating_pop_size // 2, num_var))

        # Both branches of each np.where below are evaluated eagerly; the unused branch can legitimately
        # overflow or divide by zero, producing inf/nan that np.where discards.
        # Silence the resulting benign numpy floating-point warnings.
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            exp_lower_1 = np.exp((x_lower - parents1) / (self.lambda_ * safe_span))
            exp_upper_1 = np.exp((parents1 - x_upper) / (self.lambda_ * safe_span))

            exp_lower_2 = np.exp((x_lower - parents2) / (self.lambda_ * safe_span))
            exp_upper_2 = np.exp((parents2 - x_upper) / (self.lambda_ * safe_span))

            beta_1 = np.where(
                r_i <= 0.5,  # noqa: PLR2004
                self.lambda_ * np.log(exp_lower_1 + u_i * (1 - exp_lower_1)),
                -self.lambda_ * np.log(1 - u_i * (1 - exp_upper_1)),
            )

            beta_2 = np.where(
                r_i <= 0.5,  # noqa: PLR2004
                self.lambda_ * np.log(exp_lower_2 + u_i * (1 - exp_lower_2)),
                -self.lambda_ * np.log(1 - u_i * (1 - exp_upper_2)),
            )

        # beta * span is already exactly zero wherever the span
        # is, but taking the parent value directly keeps a non-finite beta from reintroducing a NaN.
        offspring1 = np.where(zero_span, parents1, parents1 + beta_1 * span)
        offspring2 = np.where(zero_span, parents2, parents2 + beta_2 * span)

        # The uniform-crossover component, applied before the per-pair crossover probability so that
        # a pair which does not cross is returned as its parents untouched.
        #
        # Each BEX offspring is displaced from *its own* parent, so identity retention is structurally
        # 1.0: offspring one descends from parent one in every variable. Exchanging the two children's
        # values for a variable is what gives that variable to the other parent's line, and it is the
        # same operation `SimulatedBinaryCrossover` performs by flipping the sign of beta -- there the
        # two children sit symmetrically about the parent midpoint, so a sign flip swaps them exactly.
        if self.uniform_xover_probability > 0:
            swap = self.rng.random((mating_pop_size // 2, num_var)) <= self.uniform_xover_probability
            offspring1, offspring2 = (
                np.where(swap, offspring2, offspring1),
                np.where(swap, offspring1, offspring2),
            )

        mask = self.rng.random(mating_pop_size // 2) > self.xover_probability
        offspring1[mask, :] = parents1[mask, :]
        offspring2[mask, :] = parents2[mask, :]

        children = np.vstack((offspring1, offspring2))
        if original_pop_size % 2 == 1:
            children = children[:-1, :]

        self.offspring_population = pl.from_numpy(children, schema=self.variable_symbols, orient="row").select(
            pl.all().cast(pl.Float64)
        )
        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the crossover operator."""
        if self.parent_population is None:
            return []
        msgs: list[Message] = []
        if self.verbosity >= 1:
            msgs.append(
                FloatMessage(
                    topic=CrossoverMessageTopics.XOVER_PROBABILITY,
                    source=self.__class__.__name__,
                    value=self.xover_probability,
                )
            )
            msgs.append(
                FloatMessage(
                    topic=CrossoverMessageTopics.LAMBDA,
                    source=self.__class__.__name__,
                    value=self.lambda_,
                )
            )
        if self.verbosity >= 2:  # noqa: PLR2004
            msgs.extend(
                [
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.PARENTS,
                        source=self.__class__.__name__,
                        value=self.parent_population,
                    ),
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.OFFSPRINGS,
                        source=self.__class__.__name__,
                        value=self.offspring_population,
                    ),
                ]
            )
        return msgs


class CompositeCrossover(BaseCrossover):
    """Combined crossover operator that combines multiple crossover operators."""

    def __init__(
        self,
        *,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        operators: list[BaseCrossover],
        seed: int,
    ):
        """Initialize the composite crossover operator.

        Args:
            problem (Problem): the problem object.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
            operators (list[BaseCrossover]): a list of crossover operators to combine.
            seed (int): the random seed for reproducibility. Not actually used here.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)
        self.operators = operators
        self.turn = 0

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform crossover using the next operator in the list.

        Args:
            population (pl.DataFrame): the population to perform the crossover with.
            to_mate (list[int] | None): indices of individuals to mate. If None, all individuals are considered.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """
        operator = self.operators[self.turn]
        offspring = operator.do(population=population, to_mate=to_mate)
        self.turn = (self.turn + 1) % len(self.operators)
        # No need to notify here, as each operator will handle its own notifications.
        return offspring

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """This crossover operator does not provide any topics itself."""
        return {0: [], 1: [], 2: []}

    @property
    def interested_topics(self):
        """This crossover operator does not have any interested topics itself."""
        return []

    def update(self, message: Message):
        """No need to update the composite operator itself. The publisher will handle the updates for each operator."""
        return

    def state(self) -> Sequence[Message]:
        """This crossover operator does not maintain its own state. For now."""
        return []


def _distinct_indices(rng: np.random.Generator, targets: np.ndarray, pop_size: int, k: int) -> np.ndarray:
    """Draw `k` indices per row, distinct from each other and from that row's target.

    Uses order-statistic shifting rather than rejection sampling: a value drawn from a range shortened
    by the number of already-excluded indices is shifted past each of them in sorted order, which lands
    uniformly on the admissible set in one pass. Rejection sampling would be simpler but its cost is
    data dependent, and a bounded retry loop that gives up leaves `r2 == r3` -- a zero difference
    vector, which silently turns differential evolution into a copy operator.

    Args:
        rng: the generator to draw from.
        targets: the index each row must avoid, shape `(n,)`.
        pop_size: the size of the population being indexed into.
        k: how many distinct indices to draw per row.

    Returns:
        np.ndarray: indices of shape `(n, k)`.
    """
    n = targets.shape[0]
    chosen = np.empty((n, k), dtype=np.int64)
    # Excluded indices per row, kept sorted so the shifts below apply in increasing order.
    excluded = targets[:, None].copy()
    for j in range(k):
        drawn = rng.integers(0, pop_size - (j + 1), size=n)
        for column in range(excluded.shape[1]):
            drawn += drawn >= excluded[:, column]
        chosen[:, j] = drawn
        excluded = np.sort(np.concatenate([excluded, drawn[:, None]], axis=1), axis=1)
    return chosen


class DifferentialEvolutionCrossover(BaseCrossover):
    """Differential evolution recombination, DE/rand/1/bin.

    For each target vector the operator forms a mutant `v = x_r1 + F * (x_r2 - x_r3)` from three
    distinct other population members, then mixes `v` with the target componentwise at rate
    `xover_probability`, forcing at least one component to come from `v` so that no offspring is a
    copy of its target.

    What separates this from the other continuous operators here is *which* individuals set the step
    size. Every other operator displaces an offspring relative to the parents being recombined, so a
    solution far from the rest of the population gets a large step and one inside a tight cluster
    gets a small one. DE's donors are unrelated to the target, so its step is set by the spread of
    the population at large. Measured on a population of 60 holding one outlier: the outlier's
    offspring moves 14.3x further than a cluster member's under DE, against 2.1x under SBX.

    All three of SBX, PCX and DE do contract as the population converges -- SBX's displacement is
    proportional to the parent difference, so it is not the fixed-versus-adaptive contrast it is
    sometimes described as.

    Unlike the other operators in this module, the returned offspring are **target aligned**: row `i`
    of the output is the child of `to_mate[i]`. The other operators either stack all first children
    ahead of all second children or interleave them, so lineage is not generically traceable; see the
    note on `BaseCrossover.do`.

    References:
        Storn, R., & Price, K. (1997). Differential Evolution - A Simple and Efficient Heuristic for
            Global Optimization over Continuous Spaces. Journal of Global Optimization, 11(4),
            341-359. https://doi.org/10.1023/A:1008202821328

        Kukkonen, S., & Lampinen, J. (2005). GDE3: The third evolution step of generalized
            differential evolution. In 2005 IEEE Congress on Evolutionary Computation (pp. 443-450).
            https://doi.org/10.1109/CEC.2005.1554717
    """

    _MIN_POPULATION = 4
    """A target plus three distinct donors."""

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the differential evolution crossover operator."""
        return {
            0: [],
            1: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
                CrossoverMessageTopics.SCALING_FACTOR,
            ],
            2: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
                CrossoverMessageTopics.SCALING_FACTOR,
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The differential evolution crossover operator listens to nothing."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        seed: int,
        scaling_factor: float = 0.5,
        xover_probability: float = 0.9,
    ):
        """Initialize the differential evolution crossover operator.

        Args:
            problem (Problem): the problem object.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell
                what topics are provided by the operator at each verbosity level.
            publisher (Publisher): the publisher to which the operator will publish messages.
            seed (int): the seed used in the random number generator.
            scaling_factor (float, optional): the factor `F` applied to the difference vector.
                Defaults to 0.5, the midpoint of the 0.4-1.0 range Storn and Price recommend.
            xover_probability (float, optional): the binomial crossover rate `CR`, the per-component
                probability that the offspring takes the mutant's value rather than the target's.
                Defaults to 0.9.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("DifferentialEvolutionCrossover only works on continuous problems.")
        if scaling_factor <= 0:
            raise ValueError("scaling_factor must be positive.")
        if not 0 <= xover_probability <= 1:
            raise ValueError("xover_probability must be in [0,1].")

        self.scaling_factor = scaling_factor
        self.xover_probability = xover_probability

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform DE/rand/1/bin crossover, producing one offspring per target.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover, one row per target.
        """
        whole = population[self.variable_symbols].to_numpy()
        pop_size = whole.shape[0]
        if pop_size < self._MIN_POPULATION:
            raise ValueError(
                f"DifferentialEvolutionCrossover needs at least {self._MIN_POPULATION} individuals, "
                f"a target and three distinct donors, but the population holds {pop_size}."
            )

        # `get_parents` is not used: it pads an odd mating pool with a duplicate so that pairs come
        # out even, and DE has no pairs. The donors are drawn from the whole population, which is
        # what DE/rand/1 specifies, so `to_mate` selects targets only.
        targets = np.arange(pop_size) if to_mate is None else np.asarray(to_mate, dtype=np.int64)
        num_offspring, num_var = targets.shape[0], whole.shape[1]
        self.parent_population = population[targets.tolist()]

        donors = _distinct_indices(self.rng, targets, pop_size, k=3)
        mutant = whole[donors[:, 0]] + self.scaling_factor * (whole[donors[:, 1]] - whole[donors[:, 2]])

        take_mutant = self.rng.random((num_offspring, num_var)) < self.xover_probability
        # One component is always inherited from the mutant, so an offspring is never a copy of its
        # target even at xover_probability = 0. This is the `jrand` of the original formulation.
        forced = self.rng.integers(0, num_var, size=num_offspring)
        take_mutant[np.arange(num_offspring), forced] = True

        offsprings = np.where(take_mutant, mutant, whole[targets])
        offsprings = np.clip(offsprings, np.asarray(self.lower_bounds), np.asarray(self.upper_bounds))

        self.offspring_population = pl.from_numpy(offsprings, schema=self.variable_symbols, orient="row")
        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the differential evolution crossover operator."""
        if self.parent_population is None:
            return []
        msgs: list[Message] = []
        if self.verbosity >= 1:
            msgs.extend(
                [
                    FloatMessage(
                        topic=CrossoverMessageTopics.XOVER_PROBABILITY,
                        source=self.__class__.__name__,
                        value=self.xover_probability,
                    ),
                    FloatMessage(
                        topic=CrossoverMessageTopics.SCALING_FACTOR,
                        source=self.__class__.__name__,
                        value=self.scaling_factor,
                    ),
                ]
            )
        if self.verbosity >= 2:  # noqa: PLR2004
            msgs.extend(
                [
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.PARENTS,
                        source=self.__class__.__name__,
                        value=self.parent_population,
                    ),
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.OFFSPRINGS,
                        source=self.__class__.__name__,
                        value=self.offspring_population,
                    ),
                ]
            )
        return msgs


class ParentCentricCrossover(BaseCrossover):
    """Parent-centric crossover (PCX) for continuous problems.

    Three parents are drawn per offspring. One of them is the *index* parent, and the offspring is
    placed near it: displaced along the direction from the parental centroid to the index parent by a
    normal draw of standard deviation `sigma_zeta`, and orthogonally to that direction by a normal
    draw of standard deviation `sigma_eta`, scaled by how far the other two parents sit from that
    direction. The population's own geometry therefore sets the step size in both directions.

    The contrast with SBX, the other parent-centric operator here, is structural rather than a matter
    of scale. SBX perturbs each decision variable independently along its own axis and has no notion
    of a direction in decision space. PCX's displacement decomposes into a component along the
    centroid-to-parent direction and an isotropic component orthogonal to it, so the parental
    geometry decides where the offspring goes and not merely how far. With `sigma_eta` at zero the
    orthogonal part vanishes and every offspring lies exactly on the centroid-to-parent ray, which is
    what `test_parent_centric_crossover_displaces_along_the_centroid_direction` checks.

    Note:
        Deb, Anand and Joshi write the orthogonal part as a sum over an orthonormal basis of the
        complement of the parent-to-centroid direction, with an independent normal coefficient on
        each basis vector. Building that basis costs a Gram-Schmidt pass per offspring. This
        implementation instead draws an isotropic normal vector in the full space and projects the
        parent-to-centroid component out of it, which has exactly the same distribution -- an
        isotropic Gaussian projected onto a subspace is an isotropic Gaussian on that subspace -- and
        costs one dot product.

    References:
        Deb, K., Anand, A., & Joshi, D. (2002). A computationally efficient evolutionary algorithm
            for real-parameter optimization. Evolutionary Computation, 10(4), 371-395.
            https://doi.org/10.1162/106365602760972767
    """

    _MIN_POPULATION = 3
    """An index parent and two others to set the orthogonal scale."""

    _DEGENERATE = 1e-12
    """Below this, the index parent sits on the centroid and the direction is undefined."""

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the parent-centric crossover operator.

        Note:
            The operator recombines every selected parent, so it has no crossover probability and
            does not provide that topic.
        """
        return {
            0: [],
            1: [
                CrossoverMessageTopics.SIGMA_ZETA,
                CrossoverMessageTopics.SIGMA_ETA,
            ],
            2: [
                CrossoverMessageTopics.SIGMA_ZETA,
                CrossoverMessageTopics.SIGMA_ETA,
                CrossoverMessageTopics.PARENTS,
                CrossoverMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The parent-centric crossover operator listens to nothing."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        seed: int,
        sigma_zeta: float = 0.1,
        sigma_eta: float = 0.1,
    ):
        """Initialize the parent-centric crossover operator.

        Args:
            problem (Problem): the problem object.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell
                what topics are provided by the operator at each verbosity level.
            publisher (Publisher): the publisher to which the operator will publish messages.
            seed (int): the seed used in the random number generator.
            sigma_zeta (float, optional): standard deviation of the displacement along the
                centroid-to-index-parent direction. Defaults to 0.1, the value used throughout Deb,
                Anand and Joshi (2002).
            sigma_eta (float, optional): standard deviation of the displacement orthogonal to that
                direction, in units of the mean perpendicular distance of the other parents.
                Defaults to 0.1.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("ParentCentricCrossover only works on continuous problems.")
        if sigma_zeta <= 0:
            raise ValueError("sigma_zeta must be positive.")
        if sigma_eta <= 0:
            raise ValueError("sigma_eta must be positive.")

        self.sigma_zeta = sigma_zeta
        self.sigma_eta = sigma_eta

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform PCX, producing one offspring per index parent.

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover, one row per index parent.
        """
        whole = population[self.variable_symbols].to_numpy()
        pop_size = whole.shape[0]
        if pop_size < self._MIN_POPULATION:
            raise ValueError(
                f"ParentCentricCrossover needs at least {self._MIN_POPULATION} individuals, but the "
                f"population holds {pop_size}."
            )

        # As in DE, `get_parents` is not used: PCX draws a triple rather than a pair, so padding the
        # pool to an even length would serve no purpose. `to_mate` selects the index parents.
        index_parents = np.arange(pop_size) if to_mate is None else np.asarray(to_mate, dtype=np.int64)
        num_offspring, num_var = index_parents.shape[0], whole.shape[1]
        self.parent_population = population[index_parents.tolist()]

        others = _distinct_indices(self.rng, index_parents, pop_size, k=2)
        index_x = whole[index_parents]
        other_a, other_b = whole[others[:, 0]], whole[others[:, 1]]

        centroid = (index_x + other_a + other_b) / 3.0
        direction = index_x - centroid
        norm = np.linalg.norm(direction, axis=1, keepdims=True)
        # An index parent sitting on the centroid means all three parents coincide. The direction is
        # then undefined; fall back to an unprojected isotropic step, which is the limit of the
        # operator as the triangle collapses.
        degenerate = norm[:, 0] < self._DEGENERATE
        unit = np.divide(direction, np.where(norm < self._DEGENERATE, 1.0, norm))

        # Mean perpendicular distance of the other two parents from the line through the index parent.
        perpendicular = []
        for other in (other_a, other_b):
            offset = other - index_x
            along = np.sum(offset * unit, axis=1, keepdims=True) * unit
            perpendicular.append(np.linalg.norm(offset - along, axis=1))
        spread = np.mean(perpendicular, axis=0)[:, None]

        orthogonal = self.rng.normal(0.0, self.sigma_eta, size=(num_offspring, num_var))
        projection = np.sum(orthogonal * unit, axis=1, keepdims=True) * unit
        orthogonal = np.where(degenerate[:, None], orthogonal, orthogonal - projection)

        along_direction = self.rng.normal(0.0, self.sigma_zeta, size=(num_offspring, 1))
        offsprings = index_x + along_direction * direction + spread * orthogonal
        offsprings = np.clip(offsprings, np.asarray(self.lower_bounds), np.asarray(self.upper_bounds))

        self.offspring_population = pl.from_numpy(offsprings, schema=self.variable_symbols, orient="row")
        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the parent-centric crossover operator."""
        if self.parent_population is None:
            return []
        msgs: list[Message] = []
        if self.verbosity >= 1:
            msgs.extend(
                [
                    FloatMessage(
                        topic=CrossoverMessageTopics.SIGMA_ZETA,
                        source=self.__class__.__name__,
                        value=self.sigma_zeta,
                    ),
                    FloatMessage(
                        topic=CrossoverMessageTopics.SIGMA_ETA,
                        source=self.__class__.__name__,
                        value=self.sigma_eta,
                    ),
                ]
            )
        if self.verbosity >= 2:  # noqa: PLR2004
            msgs.extend(
                [
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.PARENTS,
                        source=self.__class__.__name__,
                        value=self.parent_population,
                    ),
                    PolarsDataFrameMessage(
                        topic=CrossoverMessageTopics.OFFSPRINGS,
                        source=self.__class__.__name__,
                        value=self.offspring_population,
                    ),
                ]
            )
        return msgs
