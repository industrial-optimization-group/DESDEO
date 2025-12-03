"""Classes for evaluating the objectives and constraints of the individuals in the population."""

import warnings
from collections.abc import Sequence

import polars as pl

from desdeo.problem import Evaluator, Problem
from desdeo.tools.message import (
    EvaluatorMessageTopics,
    IntMessage,
    Message,
    PolarsDataFrameMessage,
)
from desdeo.tools.patterns import Publisher, Subscriber


class EMOEvaluator(Subscriber):
    """Base class for evaluating the objectives and constraints of the individuals in the population.

    This class should be inherited by the classes that implement the evaluation of the objectives
    and constraints of the individuals in the population.

    """

    @property
    def provided_topics(self) -> dict[int, Sequence[EvaluatorMessageTopics]]:
        """The topics provided by the Evaluator."""
        return {
            0: [],
            1: [EvaluatorMessageTopics.NEW_EVALUATIONS],
            2: [
                EvaluatorMessageTopics.NEW_EVALUATIONS,
                EvaluatorMessageTopics.VERBOSE_OUTPUTS,
            ],
        }

    @property
    def interested_topics(self):
        """The topics that the Evaluator is interested in."""
        return []

    def __init__(self, problem: Problem, verbosity: int, publisher: Publisher):
        """Initialize the EMOEvaluator class."""
        super().__init__(
            verbosity=verbosity,
            publisher=publisher,
        )
        self.problem = problem
        # TODO(@light-weaver, @gialmisi): This can be so much more efficient.
        self.evaluator = lambda x: Evaluator(problem).evaluate(
            {name.symbol: x[name.symbol].to_list() for name in problem.get_flattened_variables()}, flat=True
        )
        self.variable_symbols = [name.symbol for name in problem.variables]
        self.population: pl.DataFrame
        self.out: pl.DataFrame
        self.new_evals: int = 0

    def evaluate(self, population: pl.DataFrame) -> pl.DataFrame:
        """Evaluate and return the objectives.

        Args:
            population (pl.Dataframe): The set of decision variables to evaluate.

        Returns:
            pl.Dataframe: A dataframe of objective vectors, target vectors, and constraint vectors.
        """
        self.population = population
        out = self.evaluator(population)
        # remove variable_symbols from the output
        self.out = out.drop(self.variable_symbols, strict=False)
        self.new_evals = len(population)
        # merge the objectives and targets

        self.notify()
        return self.out

    def state(self) -> Sequence[Message]:
        """The state of the evaluator sent to the Publisher."""
        if self.population is None or self.out is None or self.population is None or self.verbosity == 0:
            return []
        if self.verbosity == 1:
            return [
                IntMessage(
                    topic=EvaluatorMessageTopics.NEW_EVALUATIONS,
                    value=self.new_evals,
                    source=self.__class__.__name__,
                )
            ]

        if isinstance(self.population, pl.DataFrame):
            message = PolarsDataFrameMessage(
                topic=EvaluatorMessageTopics.VERBOSE_OUTPUTS,
                value=pl.concat([self.population, self.out], how="horizontal"),
                source=self.__class__.__name__,
            )
        else:
            warnings.warn("Population is not a Polars DataFrame. Defaulting to providing OUTPUTS only.", stacklevel=2)
            message = PolarsDataFrameMessage(
                topic=EvaluatorMessageTopics.VERBOSE_OUTPUTS,
                value=self.out,
                source=self.__class__.__name__,
            )
        return [
            IntMessage(
                topic=EvaluatorMessageTopics.NEW_EVALUATIONS,
                value=self.new_evals,
                source=self.__class__.__name__,
            ),
            message,
        ]

    def update(self, *_, **__):
        """Update the parameters of the evaluator."""
