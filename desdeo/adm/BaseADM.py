from desdeo.problem.schema import Problem
from abc import ABC, abstractmethod

"""Base class for Artificial Decision Makers (ADMs).
This class provides the basic structure and methods for implementing
an ADM.

    Attributes:
        problem (Problem): The optimization problem to solve.
        it_learning_phase (int): Number of iterations for the learning phase.
        it_decision_phase (int): Number of iterations for the decision phase.
        iteration_counter (int): Counter for the current iteration.
        max_iterations (int): Total number of iterations (learning + decision).
        
    Methods:
        has_next():
            Check if there are more iterations left to run.

        generate_initial_reference_point():
            Abstract method to generate the initial preference information for the ADM.

        get_next_preference():
            Abstract method to get the next preference value according to the current phase.

        generate_preference_learning():
            Abstract method to generate preference information during the learning phase.

        generate_preference_decision():
            Abstract method to generate preference information during the decision phase.
"""


class BaseADM(ABC):
    """
    Abstract base class for Artificial Decision Makers (ADMs).

    This class provides the basic structure and required methods for implementing
    an ADM. Subclasses must implement the abstract methods to define specific ADM behavior.

    Attributes:
        problem (Problem): The optimization problem to solve.
        it_learning_phase (int): Number of iterations for the learning phase.
        it_decision_phase (int): Number of iterations for the decision phase.
        iteration_counter (int): Counter for the current iteration.

    Properties:
        max_iterations (int): Total number of iterations (learning + decision).
    """

    def __init__(
        self,
        problem: Problem,
        it_learning_phase: int,
        it_decision_phase: int,
    ):
        """
        Initialize the ADM with the given problem and phase lengths.

        Args:
            problem (Problem): The optimization problem to solve.
            it_learning_phase (int): Number of iterations for the learning phase.
            it_decision_phase (int): Number of iterations for the decision phase.
        """
        self.problem = problem
        self.it_learning_phase = it_learning_phase
        self.it_decision_phase = it_decision_phase
        self.iteration_counter = 0

    @property
    def max_iterations(self):
        """
        int: Total number of iterations (learning + decision).
        """
        return self.it_learning_phase + self.it_decision_phase

    def has_next(self):
        """
        Check if there are more iterations left to run.

        Returns:
            bool: True if more iterations remain, False otherwise.
        """
        return self.iteration_counter < self.max_iterations

    @abstractmethod
    def generate_initial_preference(self):
        """
        Generate the initial preference information for the ADM.

        This method must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def get_next_preference(self):
        """
        Get the next preference value according to the current phase.

        This method must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def generate_preference_learning(self):
        """
        Generate preference information during the learning phase.

        This method must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def generate_preference_decision(self):
        """
        Generate preference information during the decision phase.

        This method must be implemented by subclasses.
        """
        pass
