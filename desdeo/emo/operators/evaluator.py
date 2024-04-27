"""Classes for evaluating the objectives and constraints of the individuals in the population."""

from typing import Callable, Iterable

import numpy as np

from desdeo.problem import Problem
from desdeo.tools.patterns import Subscriber


class BaseEvaluator(Subscriber):
    """Base class for evaluating the objectives and constraints of the individuals in the population.

    This class should be inherited by the classes that implement the evaluation of the objectives
    and constraints of the individuals in the population.

    """

    def __init__(
        self, problem: Problem, obj_evaluator: Callable, cons_evaluator: Callable, verbosity: int = 1, *args, **kwargs
    ):
        """Initialize the BaseEvaluator class."""
        super().__init__(*args, **kwargs)
        self.problem = problem
        self.obj_evaluator = obj_evaluator
        self.cons_evaluator = cons_evaluator
        self.population: Iterable = None
        self.objs: np.ndarray = None
        self.cons: np.ndarray = None
        self.verbosity: int = 1

    def evaluate(self, population: Iterable) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate and return the objectives.

        Args:
            population (Iterable): The set of decision variables to evaluate.

        Returns:
            tuple[np.ndarray, np.ndarray]: Tuple of objective vectors and constraint vectors corresponding to
                the members of population.
        """
        self.population = population
        # TODO: Replace the code below with calls to the Problem object.
        # For now, this is a hack.
        self.objs = self.obj_evaluator(population)
        self.cons = self.cons_evaluator(population)
        self.notify()
        return self.objs, self.cons

    def state(self) -> dict | None:
        """The state of the evaluator sent to the Publisher."""
        if self.verbosity == 0:
            return
        return {
            "decision vectors": self.population,
            "objective vectors": self.objs,
            "constraint vectors": self.cons,
        }

    def update(self, *args, **kwargs):
        """Update the parameters of the evaluator."""
        pass
