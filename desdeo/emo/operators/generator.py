"""Class for generating initial population for the evolutionary optimization algorithms."""

from abc import abstractmethod
from collections.abc import Sequence

import numpy as np
from scipy.stats.qmc import LatinHypercube

from desdeo.emo.operators.evaluator import BaseEvaluator
from desdeo.problem import Problem, TensorVariable
from desdeo.tools.message import Array2DMessage, GeneratorMessageTopics, Message, IntMessage
from desdeo.tools.patterns import Subscriber


class BaseGenerator(Subscriber):
    """Base class for generating initial population for the evolutionary optimization algorithms.

    This class should be inherited by the classes that implement the initial population generation
    for the evolutionary optimization algorithms.

    """

    def __init__(self, **kwargs):
        """Initialize the BaseGenerator class."""
        super().__init__(**kwargs)
        self.population: np.ndarray | None = None
        self.objs: np.ndarray | None = None
        self.targets: np.ndarray | None = None
        self.cons: np.ndarray | None = None
        match self.verbosity:
            case 0:
                self.provided_topics = []
            case 1:
                self.provided_topics = [GeneratorMessageTopics.NEW_EVALUATIONS]
            case 2:
                self.provided_topics = [
                    GeneratorMessageTopics.NEW_EVALUATIONS,
                    GeneratorMessageTopics.POPULATION,
                    GeneratorMessageTopics.OBJECTIVES,
                    GeneratorMessageTopics.CONSTRAINTS,
                    GeneratorMessageTopics.TARGETS,
                ]

    @abstractmethod
    def do(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
        """Generate the initial population.

        This method should be implemented by the inherited classes.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray | None]: The initial population, the corresponding objectives,
                the constraint violations, and the targets.
        """

    def state(self) -> Sequence[Message] | None:
        """Return the state of the generator.

        This method should be implemented by the inherited classes.

        Returns:
            dict: The state of the generator.
        """
        if self.population is None or self.targets is None or self.objs is None or self.verbosity == 0:
            return None
        if self.verbosity == 1:
            return [
                IntMessage(
                    topic=GeneratorMessageTopics.NEW_EVALUATIONS,
                    value=self.population.shape[0],
                    source=self.__class__.__name__,
                ),
            ]
        # verbosity == 2
        state = [
            Array2DMessage(
                topic=GeneratorMessageTopics.POPULATION,
                value=self.population.tolist(),
                source=self.__class__.__name__,
            ),
            Array2DMessage(
                topic=GeneratorMessageTopics.OBJECTIVES,
                value=self.objs.tolist(),
                source=self.__class__.__name__,
            ),
            Array2DMessage(
                topic=GeneratorMessageTopics.TARGETS,
                value=self.targets.tolist(),
                source=self.__class__.__name__,
            ),
            IntMessage(
                topic=GeneratorMessageTopics.NEW_EVALUATIONS,
                value=self.population.shape[0],
                source=self.__class__.__name__,
            ),
        ]
        if self.cons is not None:
            state.append(
                Array2DMessage(
                    topic=GeneratorMessageTopics.CONSTRAINTS,
                    value=self.cons.tolist(),
                    source=self.__class__.__name__,
                )
            )
        return state


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
            n_cons (int, optional): The number of constraints in the problem. Defaults to 0.
        """
        super().__init__()
        self.n_points = n_points
        self.n_vars = n_vars
        self.n_objs = n_objs
        self.n_cons = n_cons
        self.population = np.zeros((n_points, n_vars))
        self.objs = np.zeros((n_points, n_objs))
        self.targets = np.ones((n_points, n_objs))
        self.cons = None
        if n_cons > 0:
            self.cons = np.zeros((n_points, 1))

    def do(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
        """Generate the initial population.

        Returns:
            Tuple[np.ndarray, np.ndarray]: The initial population and the corresponding targets.
        """
        if self.population is None or self.targets is None or self.objs is None:
            raise ValueError("Population, objectives, and targets are not set.")
        self.notify()
        return self.population, self.objs, self.targets, self.cons


class RandomGenerator(BaseGenerator):
    """Class for generating random initial population for the evolutionary optimization algorithms.

    This class generates the initial population by randomly sampling the points from the variable bounds. The
    distribution of the points is uniform. If the seed is not provided, the seed is set to 0.
    """

    def __init__(self, problem: Problem, evaluator: BaseEvaluator, n_points: int, seed: int, **kwargs):
        """Initialize the RandomGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int): The seed for the random number generator.
            kwargs: Additional keyword arguments. Check the Subscriber class for more information.
                At the very least, the publisher argument should be provided.
        """
        super().__init__(**kwargs)
        if any(isinstance(var, TensorVariable) for var in problem.variables):
            raise TypeError("RandomGenerator does not support tensor variables yet.")
        self.n_points = n_points
        self.bounds = np.array([[var.lowerbound, var.upperbound] for var in problem.variables])
        self.evaluator = evaluator
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def do(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
        """Generate the initial population.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]: The initial population and the corresponding
                objectives, targets, and constraint violations.
        """
        if self.population is not None and self.targets is not None and self.objs is not None:
            self.notify()
            return self.population, self.objs, self.targets, self.cons
        population = self.rng.uniform(
            low=self.bounds[:, 0], high=self.bounds[:, 1], size=(self.n_points, self.bounds.shape[0])
        )
        objs, targets, cons = self.evaluator.evaluate(population)
        self.population, self.objs, self.targets, self.cons = population, objs, targets, cons
        self.notify()
        return self.population, self.objs, self.targets, self.cons

    def update(self, message) -> None:
        pass


class LHSGenerator(RandomGenerator):
    """Class for generating Latin Hypercube Sampling (LHS) initial population for the MOEAs.

    This class generates the initial population by using the Latin Hypercube Sampling (LHS) method.
    If the seed is not provided, the seed is set to 0.
    """

    def __init__(self, problem: Problem, evaluator: BaseEvaluator, n_points: int, seed: int, **kwargs):
        """Initialize the LHSGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int): The seed for the random number generator.
            kwargs: Additional keyword arguments. Check the Subscriber class for more information.
                At the very least, the publisher argument should be provided.
        """
        super().__init__(problem, evaluator, n_points, seed, **kwargs)
        self.lhsrng = LatinHypercube(d=len(problem.variables), seed=seed)
        self.seed = seed

    def do(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
        """Generate the initial population with Latin Hypercube Sampling.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]: The initial population and the corresponding
                objectives, targets, and constraint violations.
        """
        if self.population is not None and self.targets is not None and self.objs is not None:
            self.notify()
            return self.population, self.objs, self.targets, self.cons
        population = self.lhsrng.random(n=self.n_points) * (self.bounds[:, 1] - self.bounds[:, 0]) + self.bounds[:, 0]
        objs, targets, cons = self.evaluator.evaluate(population)
        self.population, self.objs, self.targets, self.cons = population, objs, targets, cons
        self.notify()
        return self.population, self.objs, self.targets, self.cons
