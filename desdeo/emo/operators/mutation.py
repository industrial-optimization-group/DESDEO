"""Evolutionary operators for mutation.

Various evolutionary operators for mutation in multiobjective optimization are defined here.
"""

from abc import ABC, abstractmethod

import numpy as np

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

    def __init__(self, *args, **kwargs):
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
