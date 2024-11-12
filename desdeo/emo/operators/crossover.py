"""Evolutionary operators for recombination.

Various evolutionary operators for recombination
in multiobjective optimization are defined here.
"""

from abc import abstractmethod
from collections.abc import Sequence
from random import shuffle

import numpy as np
import polars as pl

from desdeo.problem import Problem, VariableDomainTypeEnum
from desdeo.tools.message import (
    CrossoverMessageTopics,
    FloatMessage,
    Message,
    PolarsDataFrameMessage,
)
from desdeo.tools.patterns import Subscriber


class BaseCrossover(Subscriber):
    """A base class for crossover operators."""

    def __init__(self, problem: Problem, **kwargs):
        """Initialize a crossover operator."""
        super().__init__(**kwargs)
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

    Reference:
        Kalyanmoy Deb and Ram Bhushan Agrawal. 1995. Simulated binary crossover for continuous search space.
            Complex Systems 9, 2 (1995), 115-148.
    """

    @property
    def provided_topics(self) -> dict[str, Sequence[CrossoverMessageTopics]]:
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
        self, *, problem: Problem, seed: int, xover_probability: float = 1.0, xover_distribution: float = 30, **kwargs
    ):
        """Initialize a simulated binary crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed for the random number generator.
            xover_probability (float, optional): the crossover probability
                parameter. Ranges between 0 and 1.0. Defaults to 1.0.
            xover_distribution (float, optional): the crossover distribution
                parameter. Must be positive. Defaults to 30.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        # Subscribes to no topics, so no need to stroe/pass the topics to the super class.
        super().__init__(problem, **kwargs)
        self.problem = problem

        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be between 0 and 1.")
        if xover_distribution <= 0:
            raise ValueError("Crossover distribution must be positive.")
        self.xover_probability = xover_probability
        self.xover_distribution = xover_distribution
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
        self.parent_population = population
        pop_size = self.parent_population.shape[0]
        num_var = len(self.variable_symbols)

        parent_decvars = self.parent_population[self.variable_symbols].to_numpy()

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            shuffle(shuffled_ids)
        else:
            shuffled_ids = to_mate
        mating_pop = parent_decvars[shuffled_ids]
        mate_size = len(shuffled_ids)

        if len(shuffled_ids) % 2 == 1:
            mating_pop = np.vstack((mating_pop, mating_pop[0]))
            mate_size += 1

        offspring = np.zeros_like(mating_pop)

        HALF = 0.5 # NOQA: N806
        # TODO(@light-weaver): Extract into a numba jitted function.
        for i in range(0, mate_size, 2):
            beta = np.zeros(num_var)
            miu = self.rng.random(num_var)
            beta[miu <= HALF] = (2 * miu[miu <= HALF]) ** (1 / (self.xover_distribution + 1))
            beta[miu > HALF] = (2 - 2 * miu[miu > HALF]) ** (-1 / (self.xover_distribution + 1))
            beta = beta * ((-1) ** self.rng.integers(low=0, high=2, size=num_var))
            beta[self.rng.random(num_var) > self.xover_probability] = 1
            avg = (mating_pop[i] + mating_pop[i + 1]) / 2
            diff = (mating_pop[i] - mating_pop[i + 1]) / 2
            offspring[i] = avg + beta * diff
            offspring[i + 1] = avg - beta * diff

        self.offspring_population = pl.from_numpy(offspring, schema=self.variable_symbols)
        self.notify()

        return self.offspring_population

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
