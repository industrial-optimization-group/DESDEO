"""Evolutionary operators for recombination.

Various evolutionary operators for recombination
in multiobjective optimization are defined here.
"""

import copy
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

        HALF = 0.5  # NOQA: N806
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


class SinglePointBinaryCrossover(BaseCrossover):
    """A class that defines the single point binary crossover operation."""

    def __init__(self, *, problem: Problem, seed: int, **kwargs):
        """Initialize the single point binary crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(problem, **kwargs)
        self.seed = seed

        self.parent_population: pl.DataFrame
        self.offspring_population: pl.DataFrame
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    @property
    def provided_topics(self) -> dict[str, Sequence[CrossoverMessageTopics]]:
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
            shuffle(shuffled_ids)
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
        parents1 = mating_pop[[shuffled_ids[i] for i in range(0, mating_pop_size, 2)]]
        parents2 = mating_pop[[shuffled_ids[i] for i in range(1, mating_pop_size, 2)]]

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

    def __init__(self, *, problem: Problem, seed: int, **kwargs):
        """Initialize the uniform integer crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(problem, **kwargs)
        self.seed = seed

        self.parent_population: pl.DataFrame
        self.offspring_population: pl.DataFrame
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    @property
    def provided_topics(self) -> dict[str, Sequence[CrossoverMessageTopics]]:
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
            shuffle(shuffled_ids)
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
        parents1 = mating_pop[[shuffled_ids[i] for i in range(0, mating_pop_size, 2)]]
        parents2 = mating_pop[[shuffled_ids[i] for i in range(1, mating_pop_size, 2)]]

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

    def __init__(self, *, problem: Problem, seed: int, **kwargs):
        """Initialize the uniform integer crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(problem, **kwargs)
        self.seed = seed

        self.parent_population: pl.DataFrame
        self.offspring_population: pl.DataFrame
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    @property
    def provided_topics(self) -> dict[str, Sequence[CrossoverMessageTopics]]:
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
            shuffle(shuffled_ids)
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
        parents1 = mating_pop[[shuffled_ids[i] for i in range(0, mating_pop_size, 2)]]
        parents2 = mating_pop[[shuffled_ids[i] for i in range(1, mating_pop_size, 2)]]

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
        seed: int = 0,
        alpha: float = 0.5,
        xover_probability: float = 1.0,
        **kwargs,
    ):
        """Initialize the blend alpha crossover operator.

        Args:
            problem (Problem): the problem object.
            seed (int): the seed used in the random number generator for choosing the crossover point.
            alpha (float, optional): non-negative blending factor 'alpha' that controls the extent to which
                offspring may be sampled outside the interval defined by each pair of parent
                genes. alpha = 0 restricts children strictly within the
                parents range, larger alpha allows some outliers. Defaults to 0.5.
            xover_probability (float, optional): the crossover probability parameter.
                Ranges between 0 and 1.0. Defaults to 1.0.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(problem=problem, **kwargs)

        if problem.variable_domain is not VariableDomainTypeEnum.continuous:
            raise ValueError("BlendAlphaCrossover only works on continuous problems.")

        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be in [0,1].")
        if alpha < 0:
            raise ValueError("Alpha must be non-negative.")

        self.alpha = alpha
        self.xover_probability = xover_probability
        self.seed = seed

        self.parent_population: pl.DataFrame | None = None
        self.offspring_population: pl.DataFrame | None = None

    def do(
        self,
        *,
        population: pl.DataFrame,
        to_mate: list[int] | None = None,
    ) -> pl.DataFrame:
        """Perform BLX-alpha crossover.

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
            shuffle(shuffled_ids)
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

        c_min = np.minimum(parents1, parents2)
        c_max = np.maximum(parents1, parents2)
        span = c_max - c_min

        lower = c_min - self.alpha * span
        upper = c_max + self.alpha * span

        rng = np.random.default_rng(self.seed)

        unoform_1 = rng.random((mating_pop_size // 2, num_var))
        uniform_2 = rng.random((mating_pop_size // 2, num_var))

        offspring1 = lower + unoform_1 * (upper - lower)
        offspring2 = lower + uniform_2 * (upper - lower)

        mask = rng.random(mating_pop_size // 2) > self.xover_probability
        offspring1[mask, :] = parents1[mask, :]
        offspring2[mask, :] = parents2[mask, :]

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
        """Return the state of the blend-alpha crossover operator."""
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

    def __init__(self, problem: Problem, xover_probability: float = 1.0, seed: int = 0, **kwargs):
        """Initialize the single arithmetic crossover operator.

        Args:
            problem (Problem): the problem object.
            xover_probability (float): probability of performing crossover.
            seed (int): random seed for reproducibility.
            kwargs: additional keyword arguments.
        """
        super().__init__(problem=problem, **kwargs)

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
            shuffle(mating_indices)
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

        for i, k in zip(row_idx, col_idx):
            offspring1[i, k + 1:] = parents2[i, k + 1:]
            offspring2[i, k + 1:] = parents1[i, k + 1:]
            offspring1[i, :k] = parents1[i, :k]
            offspring2[i, :k] = parents2[i, :k]

        offspring = np.vstack((offspring1, offspring2))
        if original_pop_size % 2 == 1:
            offspring = offspring[:-1, :]

        self.offspring_population = (
            pl.from_numpy(offspring, schema=self.variable_symbols)
            .select(pl.all().cast(pl.Float64))
        )
        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""
        pass

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
        if self.verbosity >= 2:  # More detailed info
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
    """Local Crossover for continuous problems."""

    @property
    def provided_topics(self) -> dict[int, Sequence[CrossoverMessageTopics]]:
        """The message topics provided by the local crossover operator."""
        return {
            0: [],
            1: [
                CrossoverMessageTopics.XOVER_PROBABILITY,
            ],
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

    def __init__(self, problem: Problem, xover_probability: float = 1.0, seed: int = 0, **kwargs):
        """Initialize the local crossover operator.

        Args:
            problem (Problem): the problem object.
            xover_probability (float): probability of performing crossover.
            seed (int): random seed for reproducibility.
            kwargs: additional keyword arguments.
        """
        super().__init__(problem=problem, **kwargs)

        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be in [0, 1].")

        self.xover_probability = xover_probability
        self.seed = seed
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
            np.random.shuffle(shuffled_ids)
        else:
            shuffled_ids = to_mate.copy()

        mating_pop_size = len(shuffled_ids)
        if mating_pop_size % 2 == 1:
            shuffled_ids.append(shuffled_ids[0])
            mating_pop_size += 1

        mating_pop = parent_decision_vars[shuffled_ids]
        parents1 = mating_pop[0::2]
        parents2 = mating_pop[1::2]

        rng = np.random.default_rng(self.seed)
        offspring = np.empty((mating_pop_size, num_var))

        for i in range(mating_pop_size // 2):
            if rng.random() < self.xover_probability:
                alpha = rng.random(num_var)

                offspring[2 * i] = alpha * parents1[i] + (1 - alpha) * parents2[i]
                offspring[2 * i + 1] = (1 - alpha) * parents1[i] + alpha * parents2[i]
            else:
                offspring[2 * i] = parents1[i]
                offspring[2 * i + 1] = parents2[i]

        self.offspring_population = pl.from_numpy(offspring, schema=self.variable_symbols).select(
            pl.all().cast(pl.Float64)
        )

        self.notify()
        return self.offspring_population

    def update(self, *_, **__):
        """Do nothing."""
        pass

    def state(self) -> Sequence[Message]:
        """Return the state of the local crossover operator."""
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

        if self.verbosity >= 2:
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