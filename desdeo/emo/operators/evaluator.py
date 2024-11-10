"""Classes for evaluating the objectives and constraints of the individuals in the population."""

from collections.abc import Sequence

import polars as pl

from desdeo.problem import PolarsEvaluator, Problem
from desdeo.tools.message import (
    EvaluatorMessageTopics,
    GenericMessage,
    IntMessage,
    Message,
    PolarsDataFrameMessage,
)
from desdeo.tools.patterns import Subscriber


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
                EvaluatorMessageTopics.POPULATION,
                EvaluatorMessageTopics.OUTPUTS,
            ],
        }

    @property
    def interested_topics(self):
        """The topics that the Evaluator is interested in."""
        return []

    def __init__(
        self,
        problem: Problem,
        verbosity: int = 1,
        **kwargs,
    ):
        """Initialize the EMOEvaluator class."""
        super().__init__(**kwargs)
        self.problem = problem
        # TODO(@light-weaver, @gialmisi): This can be so much more efficient.
        self.evaluator = lambda x: PolarsEvaluator(problem)._polars_evaluate_flat(
            {name.symbol: x[name.symbol].to_list() for name in problem.get_flattened_variables()}
        )
        self.variable_symbols = [name.symbol for name in problem.variables]
        self.population: pl.DataFrame
        self.outs: pl.DataFrame
        self.verbosity: int = verbosity
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
        self.out = out.drop(self.variable_symbols)
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
                    source="EMOEvaluator",
                )
            ]

        if isinstance(self.population, pl.DataFrame):
            population_message = PolarsDataFrameMessage(
                topic=EvaluatorMessageTopics.POPULATION,
                value=self.population,
                source="EMOEvaluator",
            )
        else:
            population_message = GenericMessage(
                topic=EvaluatorMessageTopics.POPULATION,
                value="Population is not a polars DataFrame",
                source="EMOEvaluator",
            )
        return [
            IntMessage(
                topic=EvaluatorMessageTopics.NEW_EVALUATIONS,
                value=self.new_evals,
                source="EMOEvaluator",
            ),
            population_message,
            PolarsDataFrameMessage(
                topic=EvaluatorMessageTopics.OUTPUTS,
                value=self.out,
                source="EMOEvaluator",
            ),
        ]

    def update(self, *_, **__):
        """Update the parameters of the evaluator."""
