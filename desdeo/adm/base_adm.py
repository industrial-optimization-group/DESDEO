"""Base class for Artificial Decision Makers (ADMs).

This module provides the abstract base class that defines the structure and
required methods for implementing an artificial decision maker, which generates
preference information for interactive multiobjective optimization methods.
"""

from abc import ABC, abstractmethod

import numpy as np

from desdeo.problem.schema import Problem


class BaseADM(ABC):
    """Abstract base class for Artificial Decision Makers (ADMs).

    This class provides the basic structure and required methods for implementing
    an ADM. Subclasses must implement the abstract methods to define specific ADM behavior.

    Attributes:
        problem (Problem): The optimization problem to solve.
        it_learning_phase (int): Number of iterations for the learning phase.
        it_decision_phase (int): Number of iterations for the decision phase.
        iteration_counter (int): Counter for the current iteration.
        rng (np.random.Generator): Random number generator used by subclasses.

    Properties:
        max_iterations (int): Total number of iterations (learning + decision).
    """

    def __init__(
        self,
        problem: Problem,
        it_learning_phase: int,
        it_decision_phase: int,
        seed: int | None = None,
    ):
        """Initialize the ADM with the given problem and phase lengths.

        Args:
            problem (Problem): The optimization problem to solve.
            it_learning_phase (int): Number of iterations for the learning phase.
            it_decision_phase (int): Number of iterations for the decision phase.
            seed (int | None): Optional seed for the random number generator used
                by subclasses. Defaults to None.
        """
        self.problem = problem
        self.it_learning_phase = it_learning_phase
        self.it_decision_phase = it_decision_phase
        self.iteration_counter = 0
        self.rng = np.random.default_rng(seed)

    @property
    def max_iterations(self):
        """int: Total number of iterations (learning + decision)."""
        return self.it_learning_phase + self.it_decision_phase

    def has_next(self) -> bool:
        """Check if there are more iterations left to run.

        Returns:
            bool: True if more iterations remain, False otherwise.
        """
        return self.iteration_counter < self.max_iterations

    @abstractmethod
    def generate_initial_preference(self):
        """Generate the initial preference information for the ADM.

        This method must be implemented by subclasses.
        """

    @abstractmethod
    def get_next_preference(self):
        """Get the next preference value according to the current phase.

        This method must be implemented by subclasses.
        """

    @abstractmethod
    def generate_preference_learning(self):
        """Generate preference information during the learning phase.

        This method must be implemented by subclasses.
        """

    @abstractmethod
    def generate_preference_decision(self):
        """Generate preference information during the decision phase.

        This method must be implemented by subclasses.
        """
