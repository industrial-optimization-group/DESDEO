"""Class for generating initial population for the evolutionary optimization algorithms."""

from abc import abstractmethod

import numpy as np
from scipy.stats.qmc import LatinHypercube

from desdeo.emo.operators.evaluator import BaseEvaluator
from desdeo.problem import Problem
from desdeo.tools.patterns import Subscriber


class BaseGenerator(Subscriber):
    """Base class for generating initial population for the evolutionary optimization algorithms.

    This class should be inherited by the classes that implement the initial population generation
    for the evolutionary optimization algorithms.

    """

    def __init__(self, *args, **kwargs):
        """Initialize the BaseGenerator class."""
        super().__init__(*args, **kwargs)
        self.population: np.ndarray | None = None
        self.targets: np.ndarray | None = None
        self.cons: np.ndarray | None = None

    @abstractmethod
    def do(self, *args, **kwargs) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        """Generate the initial population.

        This method should be implemented by the inherited classes.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray | None]: The initial population, the corresponding targets, and
                the constraint violations.
        """

    def update(self, msg: dict) -> None:
        """Update the state of the generator.

        This method is called by the Publisher to update the state of the generator.

        Args:
            msg (dict): The message from the Publisher.
        """

    def state(self) -> dict:
        """Return the state of the generator.

        This method should be implemented by the inherited classes.

        Returns:
            dict: The state of the generator.
        """
        return {
            "initial_population": self.population,
            "initial_targets": self.targets,
            "initial_constraint_violations": self.cons,
        }


class TestGenerator(BaseGenerator):
    """Test Class for generating initial population for the evolutionary optimization algorithms.

    This class generates invalid initial population and targets.
    """

    def __init__(self, n_points: int, n_vars: int, n_objs: int, n_cons: int = 0):
        """Initialize the TestGenerator class.

        Args:
            n_points (int): The number of points to generate for the initial population.
            n_vars (int): The number of variables in the problem.
            n_objs (int): The number of objectives in the problem.
        """
        super().__init__()
        self.n_points = n_points
        self.n_vars = n_vars
        self.n_objs = n_objs
        self.n_cons = n_cons
        self.population = np.zeros((n_points, n_vars))
        self.targets = np.ones((n_points, n_objs))
        self.cons = None
        if n_cons > 0:
            self.cons = np.zeros((n_points, 1))

    def do(self) -> tuple[np.ndarray, np.ndarray]:
        """Generate the initial population.

        Returns:
            Tuple[np.ndarray, np.ndarray]: The initial population and the corresponding targets.
        """
        self.notify()
        return self.population, self.targets, self.cons


class RandomGenerator(BaseGenerator):
    """Class for generating random initial population for the evolutionary optimization algorithms.

    This class generates the initial population by randomly sampling the points from the variable bounds. The
    distribution of the points is uniform. If the seed is not provided, the seed is set to 0.
    """

    def __init__(self, problem: Problem, evaluator: BaseEvaluator, n_points: int, seed: int = 0, *args, **kwargs):
        """Initialize the RandomGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int, optional): The seed for the random number generator. Defaults to 0.
        """
        super().__init__(*args, **kwargs)
        self.n_points = n_points
        self.bounds = np.array([[var.lowerbound, var.upperbound] for var in problem.variables])
        self.evaluator = evaluator
        self.rng = np.random.default_rng(seed)

    def do(self) -> tuple[np.ndarray, np.ndarray]:
        """Generate the initial population.

        Returns:
            Tuple[np.ndarray, np.ndarray]: The initial population and the corresponding targets.
        """
        if self.population is not None and self.targets is not None:
            self.notify()
            return self.population, self.targets, self.cons
        population = self.rng.uniform(self.bounds[:, 0], self.bounds[:, 1], (self.n_points, self.bounds.shape[0]))
        targets, cons = self.evaluator.evaluate(population)
        self.population, self.targets, self.cons = population, targets, cons
        self.notify()
        return self.population, self.targets, self.cons


class LHSGenerator(RandomGenerator):
    """Class for generating Latin Hypercube Sampling (LHS) initial population for the MOEAs.

    This class generates the initial population by using the Latin Hypercube Sampling (LHS) method.
    If the seed is not provided, the seed is set to 0.
    """

    def __init__(self, problem: Problem, evaluator: BaseEvaluator, n_points: int, seed: int = 0, *args, **kwargs):
        """Initialize the LHSGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int, optional): The seed for the random number generator. Defaults to 0.
        """
        super().__init__(problem, evaluator, n_points, seed, *args, **kwargs)
        self.rng = LatinHypercube(d=len(problem.variables), seed=seed)

    def do(self) -> tuple[np.ndarray, np.ndarray]:
        """Generate the initial population.

        Returns:
            Tuple[np.ndarray, np.ndarray]: The initial population and the corresponding targets.
        """
        if self.population is not None and self.targets is not None:
            self.notify()
            return self.population, self.targets, self.cons
        population = self.rng.random(n=self.n_points) * (self.bounds[:, 1] - self.bounds[:, 0]) + self.bounds[:, 0]
        targets, cons = self.evaluator.evaluate(population)
        self.population, self.targets, self.cons = population, targets, cons
        self.notify()
        return self.population, self.targets, self.cons
