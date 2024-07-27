"""The base class for termination criteria.

The termination criterion is used to determine when the optimization process should stop. In this implementation, it
also includes a simple counter for the number of elapsed generations. This counter is increased by one each time the
termination criterion is called. The simplest termination criterion is reaching the maximum number of generations.

Warning:
    Each subclass of BaseTerminator must implement the do method. The do method should always call the
    super().do method to increment the generation counter _before_ conducting the termination check.
"""

from abc import ABC, abstractmethod

import numpy as np

from desdeo.tools.patterns import Subscriber


class BaseTerminator(Subscriber):
    """The base class for the termination criteria.

    Also includes a simple counter for number of elapsed generations. This counter is increased by one each time the
    termination criterion is called.
    """

    def __init__(self, **kwargs):
        """Initialize a termination criterion."""
        super().__init__(**kwargs)
        self.current_generation = 1

    def check(self) -> bool:
        """Check if the termination criterion is reached.

        Returns:
            bool: True if the termination criterion is reached, False otherwise.
        """
        self.current_generation += 1


class MaxGenerationsTerminator(BaseTerminator):
    """A class for a termination criterion based on the number of generations."""

    def __init__(self, max_generations: int, **kwargs):
        """Initialize a termination criterion based on the number of generations.

        Args:
            max_generations (int): the maximum number of generations.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(**kwargs)
        self.max_generations = max_generations

    def check(self) -> bool:
        """Check if the termination criterion based on the number of generations is reached.

        Args:
            new_generation (bool, optional): Increment the generation counter. Defaults to True.

        Returns:
            bool: True if the termination criterion is reached, False otherwise.
        """
        super().check()
        self.notify()
        return self.current_generation >= self.max_generations

    def state(self) -> dict:
        """Return the state of the termination criterion."""
        return {"current_generation": self.current_generation, "max_generations": self.max_generations}

    def update(self, message: dict) -> None: ...


class MaxEvaluationsTerminator(BaseTerminator):
    """A class for a termination criterion based on the number of evaluations."""

    def __init__(self, max_evaluations: int, **kwargs):
        """Initialize a termination criterion based on the number of evaluations.

        Looks for messages with key "num_evaluations" to update the number of evaluations.

        Args:
            max_evaluations (int): the maximum number of evaluations.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(**kwargs)
        self.max_evaluations = max_evaluations
        self.current_evaluations = 0

    def check(self) -> bool:
        """Check if the termination criterion based on the number of evaluations is reached.

        Returns:
            bool: True if the termination criterion is reached, False otherwise.
        """
        super().check()
        return self.current_evaluations >= self.max_evaluations

    def state(self) -> dict:
        """Return the state of the termination criterion."""
        return {"current_evaluations": self.current_evaluations, "max_evaluations": self.max_evaluations}

    def update(self, message: dict) -> None:
        """Update the number of evaluations.

        Note that for this method to work, this class must be registered as an observer of a subject that sends
        messages with the key "num_evaluations". The Evaluator class does this.

        Args:
            message (dict): the message from the subject, must contain the key "num_evaluations".
        """
        if "num_evaluations" in message:
            self.current_evaluations = message["num_evaluations"]
