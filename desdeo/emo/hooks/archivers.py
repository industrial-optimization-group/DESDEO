"""A collection of archivers for storing solutions evaluated during evolution."""

from collections.abc import Sequence

import polars as pl

from desdeo.problem import Problem
from desdeo.tools.message import EvaluatorMessageTopics, GeneratorMessageTopics, Message, MessageTopics
from desdeo.tools.non_dominated_sorting import non_dominated, non_dominated_merge
from desdeo.tools.patterns import Publisher, Subscriber


class FeasibleArchive(Subscriber):
    """An archiver that stores all feasible solutions evaluated during evolution."""

    @property
    def interested_topics(self) -> Sequence[MessageTopics]:
        """Return the message topics that the archiver is interested in."""
        return [GeneratorMessageTopics.OUTPUTS, EvaluatorMessageTopics.OUTPUTS]

    @property
    def provided_topics(self) -> dict[int, Sequence[MessageTopics]]:
        """Return the topics provided by the archiver."""
        return {0: []}

    def __init__(self, *, problem: Problem, publisher: Publisher):
        """Initialize the archiver.

        Args:
            problem (Problem): The problem being solved.
            publisher (Publisher): The publisher object.
        """
        super().__init__(publisher, verbosity=0)
        self.feasible_archive: pl.DataFrame = None
        self.problem = problem
        if problem.constraints is None:
            raise ValueError("The problem has no constraints.")
        self.cons_symb = [x.symbol for x in problem.constraints]

    def update(self, message: Message) -> None:
        """Update the archiver with the new data.

        Args:
            message (Message): Message from the publisher.
        """
        data = message.value
        feasible_mask = (data[self.cons_symb] <= 0).to_numpy().all(axis=1)
        feasible_data = data.filter(feasible_mask)
        if self.feasible_archive is None:
            self.feasible_archive = feasible_data
        else:
            self.feasible_archive = pl.concat([self.feasible_archive, feasible_data])

    def state(self) -> dict:
        """Return the state of the archiver."""
        return {}


class Archive(Subscriber):
    """An archiver that stores the solutions evaluated during evolution."""

    @property
    def interested_topics(self) -> Sequence[MessageTopics]:
        """Return the message topics that the archiver is interested in."""
        return [GeneratorMessageTopics.OUTPUTS, EvaluatorMessageTopics.OUTPUTS]

    @property
    def provided_topics(self) -> dict[int, Sequence[MessageTopics]]:
        """Return the topics provided by the archiver."""
        return {0: []}

    def __init__(self, *, problem: Problem, publisher: Publisher):
        """Initialize the archiver.

        Args:
            problem (Problem): The problem being solved.
            publisher (Publisher): The publisher object.
        """
        super().__init__(publisher, verbosity=0)
        self.archive: pl.DataFrame = None
        self.problem = problem

    def update(self, message: Message) -> None:
        """Update the archiver with the new data.

        Args:
            message (Message): Message from the publisher.
        """
        data = message.value
        if self.archive is None:
            self.archive = data
        else:
            self.archive = pl.concat([self.archive, data])

    def state(self) -> dict:
        """Return the state of the archiver."""
        return {}


class NonDominatedArchive(Subscriber):
    """An archiver that stores only the non-dominated solutions evaluated during evolution."""

    @property
    def interested_topics(self) -> Sequence[MessageTopics]:
        """Return the message topics that the archiver is interested in."""
        return [GeneratorMessageTopics.OUTPUTS, EvaluatorMessageTopics.OUTPUTS]

    @property
    def provided_topics(self) -> dict[int, Sequence[MessageTopics]]:
        """Return the topics provided by the archiver."""
        return {0: []}

    def __init__(self, *, problem: Problem, publisher: Publisher):
        """Initialize the archiver.

        Args:
            problem (Problem): The problem being solved.
            publisher (Publisher): The publisher object.
        """
        super().__init__(publisher, verbosity=0)
        self.archive: pl.DataFrame = None
        self.problem = problem
        self.targets = [f"{x.symbol}_min" for x in problem.objectives]

    def update(self, message: Message) -> None:
        """Update the archiver with the new data.

        Args:
            message (Message): Message from the publisher.
        """
        data = message.value
        if type(data) is not pl.DataFrame:
            raise ValueError("Data should be a polars DataFrame")
        if self.archive is None:
            non_dom_mask = non_dominated(data[self.targets].to_numpy())
            self.archive = data.filter(non_dom_mask)
        else:
            to_add = data.filter(non_dominated(data[self.targets].to_numpy()))
            mask1, mask2 = non_dominated_merge(self.archive[self.targets].to_numpy(), to_add[self.targets].to_numpy())
            self.archive = pl.concat([self.archive.filter(mask1), to_add.filter(mask2)])

    def state(self) -> dict:
        """Return the state of the archiver."""
        return {}
