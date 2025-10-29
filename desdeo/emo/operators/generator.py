"""Class for generating initial population for the evolutionary optimization algorithms."""

from abc import abstractmethod
from collections.abc import Sequence

import numpy as np
import polars as pl
from scipy.stats.qmc import LatinHypercube

from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.problem import Problem, VariableTypeEnum
from desdeo.tools.message import GeneratorMessageTopics, IntMessage, Message, PolarsDataFrameMessage
from desdeo.tools.patterns import Publisher, Subscriber


class BaseGenerator(Subscriber):
    """Base class for generating initial population for the evolutionary optimization algorithms.

    This class should be inherited by the classes that implement the initial population generation
    for the evolutionary optimization algorithms.

    """

    @property
    def provided_topics(self) -> dict[int, Sequence[GeneratorMessageTopics]]:
        """Return the topics provided by the generator.

        Returns:
            dict[int, Sequence[GeneratorMessageTopics]]: The topics provided by the generator.
        """
        return {
            0: [],
            1: [GeneratorMessageTopics.NEW_EVALUATIONS],
            2: [
                GeneratorMessageTopics.NEW_EVALUATIONS,
                GeneratorMessageTopics.VERBOSE_OUTPUTS,
            ],
        }

    @property
    def interested_topics(self):
        """Return the message topics that the generator is interested in."""
        return []

    def __init__(self, problem: Problem, publisher: Publisher, verbosity: int):
        """Initialize the BaseGenerator class."""
        super().__init__(publisher=publisher, verbosity=verbosity)
        self.problem = problem
        self.variable_symbols = [var.symbol for var in problem.get_flattened_variables()]
        self.bounds = np.array([[var.lowerbound, var.upperbound] for var in problem.get_flattened_variables()])
        self.population: pl.DataFrame = None
        self.out: pl.DataFrame = None

    @abstractmethod
    def do(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Generate the initial population.

        This method should be implemented by the inherited classes.

        Returns:
            tuple[pl.DataFrame, pl.DataFrame]: The initial population as the first element,
                the corresponding objectives, the constraint violations, and the targets as the
                second element.
        """

    def state(self) -> Sequence[Message]:
        """Return the state of the generator.

        This method should be implemented by the inherited classes.

        Returns:
            dict: The state of the generator.
        """
        if self.population is None or self.out is None or self.verbosity == 0:
            return []
        if self.verbosity == 1:
            return [
                IntMessage(
                    topic=GeneratorMessageTopics.NEW_EVALUATIONS,
                    value=self.population.shape[0],
                    source=self.__class__.__name__,
                ),
            ]
        # verbosity == 2
        return [
            PolarsDataFrameMessage(
                topic=GeneratorMessageTopics.VERBOSE_OUTPUTS,
                value=pl.concat([self.population, self.out], how="horizontal"),
                source=self.__class__.__name__,
            ),
            IntMessage(
                topic=GeneratorMessageTopics.NEW_EVALUATIONS,
                value=self.population.shape[0],
                source=self.__class__.__name__,
            ),
        ]


class RandomGenerator(BaseGenerator):
    """Class for generating random initial population for the evolutionary optimization algorithms.

    This class generates the initial population by randomly sampling the points from the variable bounds. The
    distribution of the points is uniform. If the seed is not provided, the seed is set to 0.
    """

    def __init__(
        self, problem: Problem, evaluator: EMOEvaluator, n_points: int, seed: int, verbosity: int, publisher: Publisher
    ):
        """Initialize the RandomGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int): The seed for the random number generator.
            verbosity (int): The verbosity level of the generator. A verbosity of 2 is needed if you want to maintain
                an external archive. Otherwise, a verbosity of 1 is sufficient.
            publisher (Publisher): The publisher to publish the messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.n_points = n_points
        self.evaluator = evaluator
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def do(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Generate the initial population.

        This method should be implemented by the inherited classes.

        Returns:
            tuple[pl.DataFrame, pl.DataFrame]: The initial population as the first element,
                the corresponding objectives, the constraint violations, and the targets as the second element.
        """
        if self.population is not None and self.out is not None:
            self.notify()
            return self.population, self.out
        self.population = pl.from_numpy(
            self.rng.uniform(low=self.bounds[:, 0], high=self.bounds[:, 1], size=(self.n_points, self.bounds.shape[0])),
            schema=self.variable_symbols,
        )
        self.out = self.evaluator.evaluate(self.population)
        self.notify()
        return self.population, self.out

    def update(self, message) -> None:
        """Update the generator based on the message."""


class LHSGenerator(BaseGenerator):
    """Class for generating Latin Hypercube Sampling (LHS) initial population for the MOEAs.

    This class generates the initial population by using the Latin Hypercube Sampling (LHS) method.
    If the seed is not provided, the seed is set to 0.
    """

    def __init__(
        self, problem: Problem, evaluator: EMOEvaluator, n_points: int, seed: int, verbosity: int, publisher: Publisher
    ):
        """Initialize the LHSGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int): The seed for the random number generator.
            verbosity (int): The verbosity level of the generator. A verbosity of 2 is needed if you want to maintain
                an external archive. Otherwise, a verbosity of 1 is sufficient.
            publisher (Publisher): The publisher to publish the messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.n_points = n_points
        self.evaluator = evaluator
        self.lhsrng = LatinHypercube(d=len(self.variable_symbols), seed=seed)
        self.seed = seed

    def do(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Generate the initial population.

        This method should be implemented by the inherited classes.

        Returns:
            tuple[pl.DataFrame, pl.DataFrame]: The initial population as the first element,
                the corresponding objectives, the constraint violations, and the targets as the second element.
        """
        if self.population is not None and self.out is not None:
            self.notify()
            return self.population, self.out
        self.population = pl.from_numpy(
            self.lhsrng.random(n=self.n_points) * (self.bounds[:, 1] - self.bounds[:, 0]) + self.bounds[:, 0],
            schema=self.variable_symbols,
        )
        self.out = self.evaluator.evaluate(self.population)
        self.notify()
        return self.population, self.out

    def update(self, message) -> None:
        """Update the generator based on the message."""


class RandomBinaryGenerator(BaseGenerator):
    """Class for generating random initial population for problems with binary variables.

    This class generates an initial population by randomly setting variable values to be either 0 or 1.
    """

    def __init__(
        self, problem: Problem, evaluator: EMOEvaluator, n_points: int, seed: int, verbosity: int, publisher: Publisher
    ):
        """Initialize the RandomBinaryGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int): The seed for the random number generator.
            verbosity (int): The verbosity level of the generator. A verbosity of 2 is needed if you want to maintain
                an external archive. Otherwise, a verbosity of 1 is sufficient.
            publisher (Publisher): The publisher to publish the messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.n_points = n_points
        self.evaluator = evaluator
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def do(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Generate the initial population.

        Returns:
            tuple[pl.DataFrame, pl.DataFrame]: The initial population as the first element,
                the corresponding objectives, the constraint violations, and the targets as the second element.
        """
        if self.population is not None and self.out is not None:
            self.notify()
            return self.population, self.out

        self.population = pl.from_numpy(
            self.rng.integers(low=0, high=2, size=(self.n_points, self.bounds.shape[0])).astype(dtype=np.float64),
            schema=self.variable_symbols,
        )

        self.out = self.evaluator.evaluate(self.population)
        self.notify()
        return self.population, self.out

    def update(self, message) -> None:
        """Update the generator based on the message."""


class RandomIntegerGenerator(BaseGenerator):
    """Class for generating random initial population for problems with integer variables.

    This class generates an initial population by randomly setting variable values to be integers between the bounds of
    the variables.
    """

    def __init__(
        self, problem: Problem, evaluator: EMOEvaluator, n_points: int, seed: int, verbosity: int, publisher: Publisher
    ):
        """Initialize the RandomIntegerGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int): The seed for the random number generator.
            verbosity (int): The verbosity level of the generator. A verbosity of 2 is needed if you want to maintain
                an external archive. Otherwise, a verbosity of 1 is sufficient.
            publisher (Publisher): The publisher to publish the messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.n_points = n_points
        self.evaluator = evaluator
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def do(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Generate the initial population.

        Returns:
            tuple[pl.DataFrame, pl.DataFrame]: The initial population as the first element,
                the corresponding objectives, the constraint violations, and the targets as the second element.
        """
        if self.population is not None and self.out is not None:
            self.notify()
            return self.population, self.out

        self.population = pl.from_numpy(
            self.rng.integers(
                low=self.bounds[:, 0],
                high=self.bounds[:, 1],
                size=(self.n_points, self.bounds.shape[0]),
                endpoint=True,
            ).astype(dtype=float),
            schema=self.variable_symbols,
        )

        self.out = self.evaluator.evaluate(self.population)
        self.notify()
        return self.population, self.out

    def update(self, message) -> None:
        """Update the generator based on the message."""


class RandomMixedIntegerGenerator(BaseGenerator):
    """Class for generating random initial population for problems with mixed-integer variables.

    This class generates an initial population by randomly setting variable
    values to be integers or floats between the bounds of the variables.
    """

    def __init__(
        self, problem: Problem, evaluator: EMOEvaluator, n_points: int, seed: int, verbosity: int, publisher: Publisher
    ):
        """Initialize the RandomMixedIntegerGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population.
            n_points (int): The number of points to generate for the initial population.
            seed (int): The seed for the random number generator.
            verbosity (int): The verbosity level of the generator. A verbosity of 2 is needed if you want to maintain
                an external archive. Otherwise, a verbosity of 1 is sufficient.
            publisher (Publisher): The publisher to publish the messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.var_symbol_types = {
            VariableTypeEnum.real: [
                var.symbol for var in problem.variables if var.variable_type == VariableTypeEnum.real
            ],
            VariableTypeEnum.integer: [
                var.symbol
                for var in problem.variables
                if var.variable_type in [VariableTypeEnum.integer, VariableTypeEnum.binary]
            ],
        }
        self.n_points = n_points
        self.evaluator = evaluator
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def do(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Generate the initial population.

        Returns:
            tuple[pl.DataFrame, pl.DataFrame]: The initial population as the first element,
                the corresponding objectives, the constraint violations, and the targets as the second element.
        """
        if self.population is not None and self.out is not None:
            self.notify()
            return self.population, self.out

        tmp = {
            var.symbol: self.rng.integers(
                low=var.lowerbound, high=var.upperbound, size=self.n_points, endpoint=True
            ).astype(dtype=float)
            if var.variable_type in [VariableTypeEnum.binary, VariableTypeEnum.integer]
            else self.rng.uniform(low=var.lowerbound, high=var.upperbound, size=self.n_points).astype(dtype=float)
            for var in self.problem.variables
        }

        # combine
        # self.population
        self.population = pl.DataFrame(tmp)

        self.out = self.evaluator.evaluate(self.population)
        self.notify()
        return self.population, self.out

    def update(self, message) -> None:
        """Update the generator based on the message."""


class ArchiveGenerator(BaseGenerator):
    """Class for getting initial population from an archive."""

    def __init__(
        self,
        problem: Problem,
        evaluator: EMOEvaluator,
        publisher: Publisher,
        verbosity: int,
        solutions: pl.DataFrame,
        **kwargs,  # just to dump seed
    ):
        """Initialize the ArchiveGenerator class.

        Args:
            problem (Problem): The problem to solve.
            evaluator (BaseEvaluator): The evaluator to evaluate the population. Only used to check that the outputs
                have the correct variables.
            publisher (Publisher): The publisher to publish the messages.
            verbosity (int): The verbosity level of the generator. A verbosity of 2 is needed if you want to maintain
                an external archive. Otherwise, a verbosity of 1 is sufficient.
            solutions (pl.DataFrame): The decision variable vectors to use as the initial population.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        if not isinstance(solutions, pl.DataFrame):
            raise ValueError("The solutions must be a polars DataFrame.")
        if solutions.shape[0] == 0:
            raise ValueError("The solutions DataFrame is empty.")
        self.solutions = solutions
        # self.outputs = outputs
        if not set(self.solutions.columns) == set(self.variable_symbols):
            raise ValueError("The solutions DataFrame must have the same columns as the problem variables.")
        # TODO: Check that the outputs have the correct columns
        self.evaluator = evaluator

    def do(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Get the initial population from the archive.

        Returns:
            tuple[pl.DataFrame, pl.DataFrame]: The initial population as the first element,
                the corresponding objectives, the constraint violations, and the targets as the second element.
        """
        self.outputs = self.evaluator.evaluate(self.solutions)
        self.notify()
        return self.solutions, self.outputs

    def state(self) -> Sequence[Message]:
        """Return the state of the generator.

        This method overrides the state method of the BaseGenerator class, because the solutions and outputs are
        already provided and not generated by the generator.

        Returns:
            dict: The state of the generator.
        """
        # TODO: Should we do it like this? Or just do super().state()?
        # Maybe saying that zero evaluations have been done is misleading?
        # idk
        if self.verbosity == 0:
            return []
        if self.verbosity == 1:
            return [
                IntMessage(
                    topic=GeneratorMessageTopics.NEW_EVALUATIONS,
                    value=0,
                    source=self.__class__.__name__,
                ),
            ]
        # verbosity == 2
        return [
            PolarsDataFrameMessage(
                topic=GeneratorMessageTopics.VERBOSE_OUTPUTS,
                value=pl.concat([self.solutions, self.outputs], how="horizontal"),
                source=self.__class__.__name__,
            ),
            IntMessage(
                topic=GeneratorMessageTopics.NEW_EVALUATIONS,
                value=0,
                source=self.__class__.__name__,
            ),
        ]

    def update(self, message) -> None:
        """Update the generator based on the message."""
