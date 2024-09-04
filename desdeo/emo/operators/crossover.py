"""Evolutionary operators for recombination.

Various evolutionary operators for recombination
in multiobjective optimization are defined here.
"""

from abc import abstractmethod
from collections.abc import Sequence
from random import shuffle

import numpy as np

from desdeo.tools.message import Array2DMessage, CrossoverMessageTopics, FloatMessage, Message, StringMessage
from desdeo.tools.patterns import Subscriber


class BaseCrossover(Subscriber):
    """A base class for crossover operators."""

    def __init__(self, **kwargs):
        """Initialize a crossover operator."""
        super().__init__(**kwargs)

    @abstractmethod
    def do(
        self, *, population: tuple[np.ndarray, np.ndarray | None, np.ndarray | None], to_mate: list[int] | None = None
    ) -> np.ndarray:
        """Perform the crossover operation.

        Args:
            population (tuple[np.ndarray, np.ndarray | None, np.ndarray | None]): the population to perform the
                crossover with. The first element of the tuple are the decision vectors, the second element is the
                corresponding target vectors, the third element is the corresponding constraint vectors. The second
                and third elements may be `None`.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            np.ndarray: the offspring resulting from the crossover.
        """


class TestCrossover(BaseCrossover):
    """Just a test crossover operator."""

    def __init__(self, **kwargs):
        """Initialize a test crossover operator."""
        super().__init__(**kwargs)

    def do(
        self, *, population: tuple[np.ndarray, np.ndarray | None, np.ndarray | None], to_mate: list[int] | None = None
    ) -> np.ndarray:
        """Perform the test crossover operation.

        Args:
            population (tuple[np.ndarray, np.ndarray | None, np.ndarray | None]): the population to perform the
                crossover with. The first element of the tuple are the decision vectors, the second element is the
                corresponding target vectors, the third element is the corresponding constraint vectors. The second
                and third elements may be `None`.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            np.ndarray: the offspring resulting from the crossover.
        """
        return population[0]

    def update(self, *_, **__):
        """Do nothing. This is just the test crossover operator."""

    def state(self) -> Sequence[StringMessage]:
        """Return the state of the crossover operator."""
        return [
            StringMessage(topic=CrossoverMessageTopics.TEST, source="TestCrossover", value="Test crossover operator.")
        ]


class SimulatedBinaryCrossover(BaseCrossover):
    """A class for creating a simulated binary crossover operator.

    Reference:
        Kalyanmoy Deb and Ram Bhushan Agrawal. 1995. Simulated binary crossover for continuous search space.
            Complex Systems 9, 2 (1995), 115-148.
    """

    def __init__(self, *, seed: int, xover_probability: float = 1.0, xover_distribution: float = 30, **kwargs):
        """Initialize a simulated binary crossover operator.

        Args:
            seed (int): the seed for the random number generator.
            xover_probability (float, optional): the crossover probability
                parameter. Ranges between 0 and 1.0. Defaults to 1.0.
            xover_distribution (float, optional): the crossover distribution
                parameter. Must be positive. Defaults to 30.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        # Subscribes to no topics, so no need to stroe/pass the topics to the super class.
        super().__init__(**kwargs)
        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be between 0 and 1.")
        if xover_distribution <= 0:
            raise ValueError("Crossover distribution must be positive.")
        self.xover_probability = xover_probability
        self.xover_distribution = xover_distribution
        self.parent_population: tuple[np.ndarray, np.ndarray | None, np.ndarray | None] | None = None
        self.offspring_population: np.ndarray | None = None
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        match self.verbosity:
            case 0:
                self.provided_topics = []
            case 1:
                self.provided_topics = [
                    CrossoverMessageTopics.XOVER_PROBABILITY,
                    CrossoverMessageTopics.XOVER_DISTRIBUTION,
                ]
            case 2:
                self.provided_topics = [
                    CrossoverMessageTopics.XOVER_PROBABILITY,
                    CrossoverMessageTopics.XOVER_DISTRIBUTION,
                    CrossoverMessageTopics.PARENTS,
                    CrossoverMessageTopics.OFFSPRINGS,
                ]

    def do(
        self,
        *,
        population: tuple[np.ndarray, np.ndarray | None, np.ndarray | None],
        to_mate: list[int] | None = None,
    ) -> np.ndarray:
        """Perform the simulated binary crossover operation.

        Args:
            population (tuple[np.ndarray, np.ndarray | None, np.ndarray | None]): the population to perform the
                crossover with. The first element of the tuple are the decision vectors, the second element is the
                corresponding target vectors, the third element is the corresponding constraint vectors. The second
                and third elements may be `None`.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            np.ndarray: the offspring resulting from the crossover.
        """
        self.parent_population = population
        pop_size, num_var = self.parent_population[0].shape

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            shuffle(shuffled_ids)
        else:
            shuffled_ids = to_mate
        mating_pop = self.parent_population[0][shuffled_ids]
        mate_size = len(shuffled_ids)

        if len(shuffled_ids) % 2 == 1:
            mating_pop = np.vstack((mating_pop, mating_pop[0]))
            mate_size += 1

        offspring = np.zeros_like(mating_pop)

        # TODO(@light-weaver): Extract into a numba jitted function.
        for i in range(0, mate_size, 2):
            beta = np.zeros(num_var)
            miu = self.rng.random(num_var)
            beta[miu <= 0.5] = (2 * miu[miu <= 0.5]) ** (1 / (self.xover_distribution + 1))
            beta[miu > 0.5] = (2 - 2 * miu[miu > 0.5]) ** (-1 / (self.xover_distribution + 1))
            beta = beta * ((-1) ** self.rng.integers(low=0, high=2, size=num_var))
            beta[self.rng.random(num_var) > self.xover_probability] = 1
            avg = (mating_pop[i] + mating_pop[i + 1]) / 2
            diff = (mating_pop[i] - mating_pop[i + 1]) / 2
            offspring[i] = avg + beta * diff
            offspring[i + 1] = avg - beta * diff

        self.offspring_population = offspring
        self.notify()

        return offspring

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
            Array2DMessage(
                topic=CrossoverMessageTopics.PARENTS,
                source="SimulatedBinaryCrossover",
                value=self.parent_population[0].tolist(),
            ),
            Array2DMessage(
                topic=CrossoverMessageTopics.OFFSPRINGS,
                source="SimulatedBinaryCrossover",
                value=self.offspring_population.tolist(),
            ),
        ]
