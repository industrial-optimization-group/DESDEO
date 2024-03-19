"""Evolutionary operators for recombination.

Various evolutionary operators for recombination
in multiobjective optimization are defined here.
"""

from collections.abc import Callable
from random import shuffle

import numpy as np


def create_sbxover_op(
    xover_probability: float = 1.0, xover_distribution: float = 30
) -> Callable[[np.ndarray, list[int]], np.ndarray]:
    """Create a simulated binary crossover operator.

    Crates a simulated binary crossover operator with a given crossover probability and
    distribution.

    Reference:
        Kalyanmoy Deb and Ram Bhushan Agrawal. 1995. Simulated binary crossover for continuous search space.
            Complex Systems 9, 2 (1995), 115-148.

    Args:
        xover_probability (float, optional): the crossover probability
            parameter. Ranges between 0 and 1.0. Defaults to 1.0.
        xover_distribution (float, optional): the crossover distribution parameter. Must be positive. Defaults to 30.

    Returns:
        Callable[[np.ndarray, list[int] | None], np.ndarray]: a simulated binary cross over operator
            that given a population and a list of indices in the population that should mate,
            returns the offspring generated from the crossover.
    """

    def op(population: np.ndarray, to_mate: list[int] | None) -> np.ndarray:
        """A simulated binary crossover operator.

        Args:
            population (np.ndarray): the population to perform the crossover with.
            to_mate (list[int] | None): the indices of the population members that should
                participate in the crossover. If `None`, the whole population is subject
                to the crossover.

        Returns:
            np.array: the offspring resulting from the crossover.
        """
        pop_size, num_var = population.shape

        if to_mate is None:
            shuffled_ids = list(range(pop_size))
            shuffle(shuffled_ids)
        else:
            shuffled_ids = to_mate
        mating_pop = population[shuffled_ids]
        mate_size = len(shuffled_ids)

        if len(shuffled_ids) % 2 == 1:
            # Maybe it should be pop_size-1?
            mating_pop = np.vstack((mating_pop, mating_pop[0]))
            mate_size = mate_size + 1
        # The rest closely follows the matlab code.
        offspring = np.zeros_like(mating_pop)  # empty_like() more efficient?

        for i in range(0, mate_size, 2):
            beta = np.zeros(num_var)
            miu = np.random.rand(num_var)
            beta[miu <= 0.5] = (2 * miu[miu <= 0.5]) ** (1 / (xover_distribution + 1))
            beta[miu > 0.5] = (2 - 2 * miu[miu > 0.5]) ** (-1 / (xover_distribution + 1))
            beta = beta * ((-1) ** np.random.randint(0, high=2, size=num_var))
            beta[np.random.rand(num_var) > xover_probability] = 1  # It was in matlab code
            avg = (mating_pop[i] + mating_pop[i + 1]) / 2
            diff = (mating_pop[i] - mating_pop[i + 1]) / 2
            offspring[i] = avg + beta * diff
            offspring[i + 1] = avg - beta * diff

        return offspring

    return op
