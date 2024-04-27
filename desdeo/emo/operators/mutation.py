"""Evolutionary operators for mutation.

Various evolutionary operators for mutation in multiobjective optimization are defined here.
"""

from abc import ABC, abstractmethod

import numpy as np

from desdeo.problem import Problem
from desdeo.tools.patterns import Subscriber


class BaseMutation(Subscriber):
    """A base class for mutation operators."""

    @abstractmethod
    def __init__(self, *args, **kwargs):
        """Initialize a mu operator."""
        super().__init__(*args, **kwargs)

    @abstractmethod
    def do(self, offsprings: np.ndarray, parents: np.ndarray) -> np.ndarray:
        """Perform the mutation operation.

        Args:
            offsprings (np.ndarray): the offspring population to mutate.
            parents (np.ndarray): the parent population from which the offspring
                was generated (via crossover).

        Returns:
            np.ndarray: the offspring resulting from the mutation.
        """


class TestMutation(BaseMutation):
    """Just a test mutation operator."""

    def __init__(self, problem: Problem, *args, **kwargs):
        """Initialize a test mutation operator."""
        super().__init__(*args, **kwargs)

    def do(self, offsprings: np.ndarray, parents: np.ndarray) -> np.ndarray:
        """Perform the test mutation operation.

        Args:
            offsprings (np.ndarray): the offspring population to mutate.
            parents (np.ndarray): the parent population from which the offspring
                was generated (via crossover).

        Returns:
            np.ndarray: the offspring resulting from the mutation.
        """
        return offsprings

    def update(self, *args, **kwargs):
        """Do nothing. This is just the test mutation operator."""

    def state(self) -> dict:
        """Return the state of the mutation operator."""
        return {"Test mutation": "Called"}


import numpy as np


class BP_mutation(BaseMutation):
    def __init__(
        self,
        problem: Problem,
        publisher,
        ProM: float = None,
        DisM: float = 20,
    ):
        super().__init__(publisher=publisher)
        self.bounds = np.array([[var.lowerbound, var.upperbound] for var in problem.variables])
        self.lower_limits = self.bounds[:, 0]
        self.upper_limits = self.bounds[:, 1]
        if ProM is None:
            self.ProM = 1 / len(self.lower_limits)
        else:
            self.ProM = ProM
        self.DisM = DisM

    def do(self, offspring: np.ndarray, parents: np.ndarray) -> np.ndarray:
        """Conduct bounded polynomial mutation. Return the mutated individuals.

        Parameters
        ----------
        offspring : np.ndarray
            The array of offsprings to be mutated.

        Returns
        -------
        np.ndarray
            The mutated offsprings
        """
        min_val = np.ones_like(offspring) * self.lower_limits
        max_val = np.ones_like(offspring) * self.upper_limits
        k = np.random.random(offspring.shape)
        miu = np.random.random(offspring.shape)
        temp = np.logical_and((k <= self.ProM), (miu < 0.5))
        offspring_scaled = (offspring - min_val) / (max_val - min_val)
        offspring[temp] = offspring[temp] + (
            (max_val[temp] - min_val[temp])
            * (
                (2 * miu[temp] + (1 - 2 * miu[temp]) * (1 - offspring_scaled[temp]) ** (self.DisM + 1))
                ** (1 / (self.DisM + 1))
                - 1
            )
        )
        temp = np.logical_and((k <= self.ProM), (miu >= 0.5))
        offspring[temp] = offspring[temp] + (
            (max_val[temp] - min_val[temp])
            * (
                1
                - (2 * (1 - miu[temp]) + 2 * (miu[temp] - 0.5) * offspring_scaled[temp] ** (self.DisM + 1))
                ** (1 / (self.DisM + 1))
            )
        )
        offspring[offspring > max_val] = max_val[offspring > max_val]
        offspring[offspring < min_val] = min_val[offspring < min_val]
        return offspring

    def update(self, *args, **kwargs):
        pass

    def state(self) -> dict:
        return {"BP_mutation": "Called"}
