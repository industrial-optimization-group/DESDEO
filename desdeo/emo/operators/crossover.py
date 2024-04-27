"""Evolutionary operators for recombination.

Various evolutionary operators for recombination
in multiobjective optimization are defined here.
"""

from abc import abstractmethod
from random import shuffle

import numpy as np

from desdeo.tools.patterns import Subscriber


class BaseCrossover(Subscriber):
    """A base class for crossover operators."""

    def __init__(self, *args, **kwargs):
        """Initialize a crossover operator."""
        super().__init__(*args, **kwargs)

    @abstractmethod
    def do(self, population: np.ndarray, to_mate: list[int] | None = None) -> np.ndarray:
        """Perform the crossover operation.

        Args:
            population (np.ndarray): the population to perform the crossover with.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            np.ndarray: the offspring resulting from the crossover.
        """


class TestCrossover(BaseCrossover):
    """Just a test crossover operator."""

    def __init__(self, *args, **kwargs):
        """Initialize a test crossover operator."""
        super().__init__(*args, **kwargs)

    def do(self, population: np.ndarray, to_mate: list[int] | None = None) -> np.ndarray:
        """Perform the test crossover operation.

        Args:
            population (np.ndarray): the population to perform the crossover with.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            np.ndarray: the offspring resulting from the crossover.
        """
        return population

    def update(self, *args, **kwargs):
        """Do nothing. This is just the test crossover operator."""

    def state(self) -> dict:
        """Return the state of the crossover operator."""
        return {"Test Crossover": "Called"}


class SimulatedBinaryCrossover(BaseCrossover):
    """A class for creating a simulated binary crossover operator.

    Reference:
        Kalyanmoy Deb and Ram Bhushan Agrawal. 1995. Simulated binary crossover for continuous search space.
            Complex Systems 9, 2 (1995), 115-148.
    """

    def __init__(self, xover_probability: float = 1.0, xover_distribution: float = 30, *args, **kwargs):
        """Initialize a simulated binary crossover operator.

        Args:
            xover_probability (float, optional): the crossover probability
                parameter. Ranges between 0 and 1.0. Defaults to 1.0.
            xover_distribution (float, optional): the crossover distribution
                parameter. Must be positive. Defaults to 30.
        """
        super().__init__(*args, **kwargs)
        if not 0 <= xover_probability <= 1:
            raise ValueError("Crossover probability must be between 0 and 1.")
        if xover_distribution <= 0:
            raise ValueError("Crossover distribution must be positive.")
        self.xover_probability = xover_probability
        self.xover_distribution = xover_distribution
        self.parent_population: tuple[np.ndarray, np.ndarray] = None
        self.offspring_population: np.ndarray = None

    def do(
        self,
        parent_population: tuple[np.ndarray, np.ndarray, np.ndarray],
        to_mate: list[int] | None = None,
        *args,
        **kwargs,
    ) -> np.ndarray:
        """Perform the simulated binary crossover operation.

        Args:
            parent_population tuple[np.ndarray, np.ndarray]: the population to perform the crossover with. The first
                element of the tuple are the decision vectors, the second element is the corresponding objective
                    vectors, the third element is the corresponding constraint vectors.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            np.ndarray: the offspring resulting from the crossover.
        """
        self.parent_population = parent_population
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

        for i in range(0, mate_size, 2):
            beta = np.zeros(num_var)
            miu = np.random.rand(num_var)
            beta[miu <= 0.5] = (2 * miu[miu <= 0.5]) ** (1 / (self.xover_distribution + 1))
            beta[miu > 0.5] = (2 - 2 * miu[miu > 0.5]) ** (-1 / (self.xover_distribution + 1))
            beta = beta * ((-1) ** np.random.randint(0, high=2, size=num_var))
            beta[np.random.rand(num_var) > self.xover_probability] = 1
            avg = (mating_pop[i] + mating_pop[i + 1]) / 2
            diff = (mating_pop[i] - mating_pop[i + 1]) / 2
            offspring[i] = avg + beta * diff
            offspring[i + 1] = avg - beta * diff

        self.offspring_population = offspring
        self.notify()

        return offspring

    def update(self, *args, **kwargs):
        """Do nothing. This is just the basic SBX operator."""

    def state(self) -> dict:
        """Return the state of the crossover operator."""
        if self.verbosity == 0:
            return {}
        if self.verbosity == 1:
            return {
                "xover_probability": self.xover_probability,
                "xover_distribution": self.xover_distribution,
            }
        # verbosity == 2 or higher
        return {
            "xover_probability": self.xover_probability,
            "xover_distribution": self.xover_distribution,
            "parent_population": self.parent_population,
            "offspring_population": self.offspring_population,
        }
