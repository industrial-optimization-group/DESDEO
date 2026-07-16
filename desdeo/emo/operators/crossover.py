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

    def __init__(self, problem: Problem, verbosity: int, publisher: Publisher):
        """Initialize a crossover operator."""
        super().__init__(verbosity=verbosity, publisher=publisher)
        self.problem = problem
        self.variable_symbols = [var.symbol for var in problem.get_flattened_variables()]
        self.lower_bounds = [var.lowerbound for var in problem.get_flattened_variables()]
        self.upper_bounds = [var.upperbound for var in problem.get_flattened_variables()]

        self.variable_types = [var.variable_type for var in problem.get_flattened_variables()]
        self.variable_combination: VariableDomainTypeEnum = problem.variable_domain

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


class SimulatedBinaryCrossover(BaseCrossover):
    """A class for creating a simulated binary crossover operator.

    Reference for unbounded version:
        Kalyanmoy Deb and Ram Bhushan Agrawal. 1995. Simulated binary crossover for continuous search space.
            Complex Systems 9, 2 (1995), 115-148.
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
        xover_probability: float = 1.0,
        xover_distribution: float = 30,
        bounded: bool = False,
    ):
        """Initialize a simulated binary crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed for the random number generator.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
            xover_probability (float, optional): the crossover probability parameter.
                This parameter decides whether the decision variable components of the parents are swapped for the
                offspring or not. Ranges between 0 and 1.0. Defaults to 1.0.
            xover_distribution (float, optional): the crossover distribution parameter. Must be positive.
                This parameter controls the distribution of the offspring. A larger value results in a distribution
                that is more concentrated around the parents, while a smaller value results in a distribution that is
                more spread out. Defaults to 30.
            bounded (bool, optional): whether to bound the offspring to the variable bounds. Defaults to False.
        """
        # Subscribes to no topics, so no need to stroe/pass the topics to the super class.
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.problem = problem

        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be between 0 and 1.")
        if xover_distribution <= 0:
            raise ValueError("Crossover distribution must be positive.")
        self.xover_probability = xover_probability
        self.xover_distribution = xover_distribution
        self.bounded = bounded

        self.parent_population: pl.DataFrame
        self.offspring_population: pl.DataFrame
        self.rng = np.random.default_rng(seed)
        self.seed = seed

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
        if self.bounded:
            self.offspring_population = self.bounded_offsprings(population=population, to_mate=to_mate)
        else:
            self.offspring_population = self.unbounded_offsprings(population=population, to_mate=to_mate)
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
        continuous search space." Complex systems 9.2 (1995): 115-148. This implementation is similar to PlatEMO,
        however, differs from deap (potentially incorrect implementation) and pymoo (they implement self-adaptive
        simulated binary crossover, but call it simulated binary crossover).

        Args:
            population (pl.DataFrame): the population to perform the crossover with. The DataFrame
                contains the decision vectors, the target vectors, and the constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            pl.DataFrame: the offspring resulting from the crossover.
        """
        self.parent_population = population
        pop_size = self.parent_population.shape[0]
        num_var = len(self.variable_symbols)

        parent_decvars = self.parent_population[self.variable_symbols].to_numpy()

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = to_mate
        mating_pop = parent_decvars[shuffled_ids]
        mate_size = len(shuffled_ids)

        if len(shuffled_ids) % 2 == 1:
            mating_pop = np.vstack((mating_pop, mating_pop[0]))
            mate_size += 1

        offspring = np.zeros_like(mating_pop)

        HALF = 0.5  # NOQA: N806
        # TODO(@light-weaver): Extract into a numba jitted function.
        for i in range(0, mate_size, 2):
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
            beta = beta * ((-1) ** self.rng.integers(low=0, high=2, size=num_var))
            # If beta = 1, no crossover occurs and the dec var components are basically copied from the parents.
            beta[self.rng.random(num_var) > self.xover_probability] = 1
            # Note that when mu < 0.5, abs(beta) ends up being less than 1, resulting in a contracting crossover.
            # The opposite is true when mu > 0.5, resulting in an expanding crossover.
            avg = (mating_pop[i] + mating_pop[i + 1]) / 2
            diff = (mating_pop[i] - mating_pop[i + 1]) / 2
            offspring[i] = avg - beta * diff
            offspring[i + 1] = avg + beta * diff
        return pl.from_numpy(offspring, schema=self.variable_symbols)

    def bounded_offsprings(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform the bounded simulated binary crossover operation.

        This implementation is similar to pymoo and boundedSBX in deap. I _literally cannot for the life of me_ find out
        an original reference for this. It is not in the original SBX paper, nor in the NSGA-II paper. I suspect that
        it just appeared in the implementation of NSGA-II one day and everyone has been copying it ever since.
        If you know the original reference, change this docstring to include it.

        But I did manage to derive the equations for the bounded version of SBX, and can confirm that the
        implementation _makes sense_. The basic idea is as follows:

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
        """
        self.parent_population = population
        pop_size = self.parent_population.shape[0]
        num_var = len(self.variable_symbols)

        parent_decvars = self.parent_population[self.variable_symbols].to_numpy()

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = to_mate
        mating_pop = parent_decvars[shuffled_ids]
        mate_size = len(shuffled_ids)

        if len(shuffled_ids) % 2 == 1:
            mating_pop = np.vstack((mating_pop, mating_pop[0]))
            mate_size += 1

        offspring = np.zeros_like(mating_pop)

        # TODO(@light-weaver): Extract into a numba jitted function.
        for i in range(0, mate_size, 2):
            beta = np.zeros(num_var)
            miu = self.rng.random(num_var)
            avg = (mating_pop[i] + mating_pop[i + 1]) / 2
            diff = (mating_pop[i] - mating_pop[i + 1]) / 2

            x1 = np.minimum(mating_pop[i], mating_pop[i + 1])
            x2 = np.maximum(mating_pop[i], mating_pop[i + 1])

            # Offspring 1 calculations
            with np.errstate(divide="ignore", invalid="ignore"):  # Handles x1 == x2 case
                beta_max = 1 + 2 * (x1 - self.lower_bounds) / (x2 - x1)
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
            # if beta is negative, the offspring 1 gets decision var component closer to parent 2 and vice versa.
            # In this implementation, there is an equal chance of beta being negative or positive.
            # TBH, this is more similar to uniform crossover than single-point crossover.
            beta = beta * ((-1) ** self.rng.integers(low=0, high=2, size=num_var))
            # If beta = 1, no crossover occurs and the dec var components are basically copied from the parents.
            beta[self.rng.random(num_var) > self.xover_probability] = 1
            offspring[i] = avg - beta * diff

            # Offspring 2 calculations
            with np.errstate(divide="ignore", invalid="ignore"):  # Handles x1 == x2 case
                beta_max = 1 + 2 * (self.upper_bounds - x2) / (x2 - x1)
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
            # if beta is negative, the offspring 1 gets decision var component closer to parent 2 and vice versa.
            # In this implementation, there is an equal chance of beta being negative or positive.
            # TBH, this is more similar to uniform crossover than single-point crossover.
            beta = beta * ((-1) ** self.rng.integers(low=0, high=2, size=num_var))
            # If beta = 1, no crossover occurs and the dec var components are basically copied from the parents.
            beta[self.rng.random(num_var) > self.xover_probability] = 1
            offspring[i + 1] = avg + beta * diff
        return pl.from_numpy(offspring, schema=self.variable_symbols)

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
    """A class that defines the single point binary crossover operation."""

    def __init__(self, *, problem: Problem, seed: int, verbosity: int, publisher: Publisher):
        """Initialize the single point binary crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level.
            publisher (Publisher): the publisher to which the operator will publish messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.seed = seed

        self.parent_population: pl.DataFrame
        self.offspring_population: pl.DataFrame
        self.rng = np.random.default_rng(seed)
        self.seed = seed

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

        cross_over_points = self.rng.integers(1, num_var - 1, mating_pop_size // 2)

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
                source="SimulatedBinaryCrossover",
                value=self.parent_population,
            ),
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.OFFSPRINGS,
                source="SimulatedBinaryCrossover",
                value=self.offspring_population,
            ),
        ]


class UniformIntegerCrossover(BaseCrossover):
    """A class that defines the uniform integer crossover operation."""

    def __init__(self, *, problem: Problem, seed: int, verbosity: int, publisher: Publisher):
        """Initialize the uniform integer crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.seed = seed

        self.parent_population: pl.DataFrame
        self.offspring_population: pl.DataFrame
        self.rng = np.random.default_rng(seed)
        self.seed = seed

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

        mask = self.rng.choice([True, False], size=num_var)

        offspring1 = np.where(mask, parents1, parents2)  # True, pick from parent1, False, pick from parent2
        offspring2 = np.where(mask, parents2, parents1)  # True, pick from parent2, False, pick from parent1

        # combine the two offspring populations into one, drop the last member if the number of
        # indices (to_mate) is uneven
        self.offspring_population = pl.from_numpy(
            np.vstack((offspring1, offspring2))[
                : (original_mating_pop_size if original_mating_pop_size % 2 == 0 else -1)
            ],
            schema=self.variable_symbols,
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
                source="SimulatedBinaryCrossover",
                value=self.parent_population,
            ),
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.OFFSPRINGS,
                source="SimulatedBinaryCrossover",
                value=self.offspring_population,
            ),
        ]


class UniformMixedIntegerCrossover(BaseCrossover):
    """A class that defines the uniform mixed-integer crossover operation.

    TODO: This is virtually identical to `UniformIntegerCrossover`. The only
    difference is that the `parent_decision_vars` in `do` are not casted to
    `int`. This is not an ideal way to implement crossover for mixed-integer
    stuff...
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
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.seed = seed

        self.parent_population: pl.DataFrame
        self.offspring_population: pl.DataFrame
        self.rng = np.random.default_rng(seed)
        self.seed = seed

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

        mask = self.rng.choice([True, False], size=num_var)

        offspring1 = np.where(mask, parents1, parents2)  # True, pick from parent1, False, pick from parent2
        offspring2 = np.where(mask, parents2, parents1)  # True, pick from parent2, False, pick from parent1

        # combine the two offspring populations into one, drop the last member if the number of
        # indices (to_mate) is uneven
        self.offspring_population = pl.from_numpy(
            np.vstack((offspring1, offspring2))[
                : (original_mating_pop_size if original_mating_pop_size % 2 == 0 else -1)
            ],
            schema=self.variable_symbols,
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
                source="SimulatedBinaryCrossover",
                value=self.parent_population,
            ),
            PolarsDataFrameMessage(
                topic=CrossoverMessageTopics.OFFSPRINGS,
                source="SimulatedBinaryCrossover",
                value=self.offspring_population,
            ),
        ]


class BlendAlphaCrossover(BaseCrossover):
    """Blend-alpha (BLX-alpha) crossover for continuous problems."""

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the blend alpha crossover operator."""
        return {
            0: [],
            1: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
                CrossoverMessageTopics.ALPHA,
            ],
            2: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
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
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("BlendAlphaCrossover only works on continuous problems.")
        if alpha < 0:
            raise ValueError("Alpha must be non-negative.")

        self.alpha = alpha
        self.seed = seed
        self.rng = np.random.default_rng(self.seed)
        self.repeats = repeats
        self.sample_each_component = sample_each_component

        self.parent_population: pl.DataFrame | None = None
        self.offspring_population: pl.DataFrame | None = None

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
        self.parent_population = population
        pop_size = population.shape[0]
        num_var = len(self.variable_symbols)

        parent_decision_vars = population[self.variable_symbols].to_numpy()
        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = copy.copy(to_mate)

        mating_pop_size = len(shuffled_ids)
        if mating_pop_size % 2 == 1:
            shuffled_ids.append(shuffled_ids[0])
            mating_pop_size += 1

        mating_pop = parent_decision_vars[shuffled_ids]

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
        self.offspring_population = pl.from_numpy(offsprings, schema=self.variable_symbols)
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
    """Single Arithmetic Crossover for continuous problems."""

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
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher)

        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be in [0, 1].")

        self.xover_probability = xover_probability
        self.seed = seed
        self.parent_population: pl.DataFrame | None = None
        self.offspring_population: pl.DataFrame | None = None
        self.rng = np.random.default_rng(self.seed)

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
        self.parent_population = population
        pop_size = population.shape[0]
        num_vars = len(self.variable_symbols)

        parents = population[self.variable_symbols].to_numpy()

        if to_mate is None:
            mating_indices = list(range(pop_size))
            self.rng.shuffle(mating_indices)
        else:
            mating_indices = copy.copy(to_mate)

        mating_pop_size = len(mating_indices)
        original_pop_size = mating_pop_size

        if mating_pop_size % 2 == 1:
            mating_indices.append(mating_indices[0])
            mating_pop_size += 1

        mating_pool = parents[mating_indices, :]

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

        # Use advanced indexing to set arithmetic crossover gene
        offspring1[row_idx, col_idx] = avg
        offspring2[row_idx, col_idx] = avg

        for i, k in zip(row_idx, col_idx, strict=True):
            offspring1[i, k + 1 :] = parents2[i, k + 1 :]
            offspring2[i, k + 1 :] = parents1[i, k + 1 :]
            offspring1[i, :k] = parents1[i, :k]
            offspring2[i, :k] = parents2[i, :k]

        offspring = np.vstack((offspring1, offspring2))
        if original_pop_size % 2 == 1:
            offspring = offspring[:-1, :]

        self.offspring_population = pl.from_numpy(offspring, schema=self.variable_symbols).select(
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

    Reference: D. Dumitrescu, B. Lazzerini, L. C. Jain, and A. Dumitrescu, Evolutionary Computation.
        CRC Press, Florida, USA, 2000
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the local crossover operator."""
        return {
            0: [],
            1: [],
            2: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
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
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher)

        self.seed = seed
        self.rng = np.random.default_rng(self.seed)
        self.parent_population: pl.DataFrame | None = None
        self.offspring_population: pl.DataFrame | None = None

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
        self.parent_population = population
        pop_size = population.shape[0]
        num_var = len(self.variable_symbols)

        parent_decision_vars = population[self.variable_symbols].to_numpy()

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = to_mate.copy()

        mating_pop_size = len(shuffled_ids)
        if mating_pop_size % 2 == 1:
            shuffled_ids.append(shuffled_ids[0])
            mating_pop_size += 1

        mating_pop = parent_decision_vars[shuffled_ids]
        parents1 = mating_pop[0::2]
        parents2 = mating_pop[1::2]

        offspring = np.empty((mating_pop_size, num_var))

        for i in range(mating_pop_size // 2):
            alpha = self.rng.random(num_var)

            offspring[2 * i] = alpha * parents1[i] + (1 - alpha) * parents2[i]
            offspring[2 * i + 1] = (1 - alpha) * parents1[i] + alpha * parents2[i]

        self.offspring_population = pl.from_numpy(offspring, schema=self.variable_symbols).select(
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
    """Bounded-exponential (BEX) crossover for continuous problems."""

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
        lambda_: float = 1.0,
        xover_probability: float = 1.0,
    ):
        """Initialize the bounded-exponential crossover operator.

        Args:
            problem (Problem): the problem object.
            verbosity (int): the verbosity level of the component. The keys in `provided_topics` tell what
                topics are provided by the operator at each verbosity level. Recommended to be set to 1.
            publisher (Publisher): the publisher to which the operator will publish messages.
            seed (int): random seed for the internal generator.
            lambda_ (float, optional): positive scale λ for the exponential distribution.
                Defaults to 1.0.
            xover_probability (float, optional): probability of applying crossover
                to each pair. Defaults to 1.0.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("BoundedExponentialCrossover only works on continuous problems.")
        if lambda_ <= 0:
            raise ValueError("lambda_ must be positive.")
        if not 0 <= xover_probability <= 1:
            raise ValueError("xover_probability must be in [0,1].")

        self.lambda_ = lambda_
        self.xover_probability = xover_probability
        self.seed = seed
        self.rng = np.random.default_rng(self.seed)

        self.parent_population: pl.DataFrame | None = None
        self.offspring_population: pl.DataFrame | None = None

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
        self.parent_population = population
        pop_size = population.shape[0]
        num_var = len(self.variable_symbols)

        parent_decision_vars = population[self.variable_symbols].to_numpy()
        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            self.rng.shuffle(shuffled_ids)
        else:
            shuffled_ids = copy.copy(to_mate)

        mating_pop_size = len(shuffled_ids)
        original_pop_size = mating_pop_size
        if mating_pop_size % 2 == 1:
            shuffled_ids.append(shuffled_ids[0])
            mating_pop_size += 1

        mating_pop = parent_decision_vars[shuffled_ids]

        parents1 = mating_pop[0::2, :]
        parents2 = mating_pop[1::2, :]

        x_lower = np.array(self.lower_bounds)
        x_upper = np.array(self.upper_bounds)
        span = parents2 - parents1  # y_i - x_1

        u_i = self.rng.random((mating_pop_size // 2, num_var))  # random integers
        r_i = self.rng.random((mating_pop_size // 2, num_var))

        # Both branches of each np.where below are evaluated eagerly; the unused branch can legitimately
        # overflow or divide by zero (e.g. zero-width spans), producing inf/nan that np.where discards.
        # Silence the resulting benign numpy floating-point warnings.
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            exp_lower_1 = np.exp((x_lower - parents1) / (self.lambda_ * span))
            exp_upper_1 = np.exp((parents1 - x_upper) / (self.lambda_ * span))

            exp_lower_2 = np.exp((x_lower - parents2) / (self.lambda_ * span))
            exp_upper_2 = np.exp((parents2 - x_upper) / (self.lambda_ * span))

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

        offspring1 = parents1 + beta_1 * span
        offspring2 = parents2 + beta_2 * span

        mask = self.rng.random(mating_pop_size // 2) > self.xover_probability
        offspring1[mask, :] = parents1[mask, :]
        offspring2[mask, :] = parents2[mask, :]

        children = np.vstack((offspring1, offspring2))
        if original_pop_size % 2 == 1:
            children = children[:-1, :]

        self.offspring_population = pl.from_numpy(children, schema=self.variable_symbols).select(
            pl.all().cast(pl.Float64)
        )
        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the crossover operator."""
        if getattr(self, "parent_population", None) is None:
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
