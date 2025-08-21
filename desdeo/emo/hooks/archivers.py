"""A collection of archivers for storing solutions evaluated during evolution."""

from collections.abc import Sequence

import polars as pl

from desdeo.problem import Problem
from desdeo.tools.message import (
    EvaluatorMessageTopics,
    GeneratorMessageTopics,
    Message,
    MessageTopics,
    SelectorMessageTopics,
    TerminatorMessageTopics,
)
from desdeo.tools.non_dominated_sorting import non_dominated, non_dominated_merge
from desdeo.tools.patterns import Publisher, Subscriber


class BaseArchive(Subscriber):
    """Base class for archivers."""

    @property
    def interested_topics(self) -> Sequence[MessageTopics]:
        """Return the message topics that the archiver is interested in."""
        return [
            GeneratorMessageTopics.VERBOSE_OUTPUTS,
            EvaluatorMessageTopics.VERBOSE_OUTPUTS,
            SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
            TerminatorMessageTopics.GENERATION,
        ]

    @property
    def provided_topics(self) -> dict[int, Sequence[MessageTopics]]:
        """Return the topics provided by the archiver."""
        return {0: []}

    def __init__(self, *, problem: Problem, publisher: Publisher):
        """Initialize the base archiver.

        Args:
            problem (Problem): The problem being solved.
            publisher (Publisher): The publisher object.
        """
        super().__init__(publisher, verbosity=0)
        self.solutions: pl.DataFrame = None
        self.selections: pl.DataFrame = None
        self.problem = problem
        self.generation_number = 1

    def state(self) -> Sequence[Message]:
        """Return the state of the archiver."""
        return []

    def update(self, message: Message) -> None:
        """Updae the archiver with new data.

        Takes care of common archiving jobs. Make sure to run this for every archiver.

        Args:
            message (Message): Message from the publisher.
        """
        if message.topic == TerminatorMessageTopics.GENERATION:
            self.generation_number = message.value
            return
        if message.topic == SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS:
            data: pl.DataFrame = message.value
            data = data.with_columns(generation=self.generation_number)
            if self.selections is None:
                self.selections = data
            else:
                self.selections = pl.concat([self.selections, data], how="vertical")
            return


class FeasibleArchive(BaseArchive):
    """An archiver that stores all feasible solutions evaluated during evolution."""

    def __init__(self, *, problem: Problem, publisher: Publisher):
        """Initialize the archiver.

        Args:
            problem (Problem): The problem being solved.
            publisher (Publisher): The publisher object.
        """
        super().__init__(problem=problem, publisher=publisher)

        if problem.constraints is None:
            raise ValueError("The problem has no constraints.")
        self.cons_symb = [x.symbol for x in problem.constraints]

    def update(self, message: Message) -> None:
        """Update the archiver with the new data.

        Args:
            message (Message): Message from the publisher.
        """
        if (
            message.topic == TerminatorMessageTopics.GENERATION  # NOQA: PLR1714
            or message.topic == SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS
        ):
            super().update(message)
            return
        data = message.value
        feasible_mask = (data[self.cons_symb] <= 0).to_numpy().all(axis=1)
        feasible_data = data.filter(feasible_mask)
        feasible_data = feasible_data.with_columns(generation=self.generation_number)
        if self.solutions is None:
            self.solutions = feasible_data
        else:
            self.solutions = pl.concat([self.solutions, feasible_data])


class Archive(BaseArchive):
    """An archiver that stores the solutions evaluated during evolution."""

    def update(self, message: Message) -> None:
        """Update the archiver with the new data.

        Args:
            message (Message): Message from the publisher.
        """
        if (
            message.topic == TerminatorMessageTopics.GENERATION  # NOQA: PLR1714
            or message.topic == SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS
        ):
            super().update(message)
            return
        data = message.value
        data = data.with_columns(generation=self.generation_number)
        if self.solutions is None:
            self.solutions = data
        else:
            self.solutions = pl.concat([self.solutions, data])


class NonDominatedArchive(Archive):
    """An archiver that stores only the non-dominated solutions evaluated during evolution."""

    def __init__(self, *, problem: Problem, publisher: Publisher):
        """Initialize the archiver.

        Args:
            problem (Problem): The problem being solved.
            publisher (Publisher): The publisher object.
        """
        super().__init__(problem=problem, publisher=publisher)
        self.targets = [f"{x.symbol}_min" for x in problem.objectives]

    def update(self, message: Message) -> None:
        """Update the archiver with the new data.

        Args:
            message (Message): Message from the publisher.
        """
        if (
            message.topic == TerminatorMessageTopics.GENERATION  # NOQA: PLR1714
            or message.topic == SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS
        ):
            super().update(message)
            return
        data = message.value
        data = data.with_columns(generation=self.generation_number)
        if type(data) is not pl.DataFrame:
            raise ValueError("Data should be a polars DataFrame")
        if self.solutions is None:
            non_dom_mask = non_dominated(data[self.targets].to_numpy())
            self.solutions = data.filter(non_dom_mask)
        else:
            to_add = data.filter(non_dominated(data[self.targets].to_numpy()))
            mask1, mask2 = non_dominated_merge(self.solutions[self.targets].to_numpy(), to_add[self.targets].to_numpy())
            self.solutions = pl.concat([self.solutions.filter(mask1), to_add.filter(mask2)])
