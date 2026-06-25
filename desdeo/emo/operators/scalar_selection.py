"""Classs for scalar selection operators."""

import warnings
from abc import abstractmethod
from collections.abc import Sequence

import numpy as np
import polars as pl

from desdeo.emo.operators.selection import SolutionType
from desdeo.tools.message import (
    DictMessage,
    Message,
    NumpyArrayMessage,
    PolarsDataFrameMessage,
    SelectorMessageTopics,
)
from desdeo.tools.patterns import Publisher, Subscriber


class BaseScalarSelector(Subscriber):
    """A base class for selection operators."""

    @property
    def provided_topics(self):
        return {
            0: [],
            1: [],
            2: [],
        }

    @property
    def interested_topics(self):
        return [
            SelectorMessageTopics.SELECTED_FITNESS,
        ]

    def __init__(self, verbosity: int, publisher: Publisher):
        """Initialize a selection operator."""
        super().__init__(verbosity=verbosity, publisher=publisher)
        self.fitness: np.ndarray | None = None

    @abstractmethod
    def _do(
        self,
        solutions: tuple[SolutionType, pl.DataFrame],
        fitness: np.ndarray | None = None,
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Perform the selection operation.

        Args:
            solutions (tuple[SolutionType, pl.DataFrame]): the decision variables as the first element.
                The second element is the objective values, targets, and constraint violations.
            fitness (np.ndarray | None, optional): The fitness values of the solutions. If None, the fitness is
                calculated from the messages sent by the publisher.

        Returns:
            SolutionType: The selected decision variables.
        """

    def do(
        self,
        solutions: tuple[SolutionType, pl.DataFrame],
        fitness: np.ndarray | None = None,
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Perform the selection operation.

        Args:
            solutions (tuple[SolutionType, pl.DataFrame]): the decision variables as the first element.
                The second element is the objective values, targets, and constraint violations.
            fitness (np.ndarray | None, optional): The fitness values of the solutions. If None, the fitness is
                calculated from the messages sent by the publisher.

        Returns:
            SolutionType: The selected decision variables.
        """
        if fitness is not None and self.fitness is not None:
            raise RuntimeError("The fitness is being set twice.")
        if fitness is None and self.fitness is None:
            raise RuntimeError(
                "The fitness is not set. Either pass it as an argument or make sure the publisher sends it."
            )
        if fitness is None:
            fitness = self.fitness
        if len(fitness) != len(solutions[0]):
            raise ValueError(
                f"The length of the fitness array ({len(fitness)}) does not match"
                f" the number of solutions ({len(solutions[0])})."
            )
        returnval = self._do(solutions, fitness)
        self.fitness = None  # Reset fitness after selection
        return returnval

    def update(self, message: Message) -> None:
        """Update the operator with a message.

        Args:
            message (Message): The message to update the operator with.
        """
        if message.topic == SelectorMessageTopics.SELECTED_FITNESS and isinstance(message.value, np.ndarray):
            self.fitness = message.value
        else:
            raise ValueError(f"Unknown message topic: {message.topic}")

    def state(self) -> Sequence[Message]:
        return []


class TournamentSelection(BaseScalarSelector):
    """A tournament selection operator."""

    def __init__(
        self,
        *,
        winner_size: int,
        verbosity: int,
        publisher: Publisher,
        tournament_size: int = 2,
        seed: int | None = None,
        selection_probability: float | None = None,
    ) -> None:
        """Initialize the tournament selection operator.

        Args:
            winner_size (int): The number of winners to select.
            verbosity (int): The verbosity level of the operator.
            publisher (Publisher): The publisher to send messages to.
            tournament_size (int, optional): The size of the tournament. Defaults to 2, which corresponds to binary
                tournament.
            seed (int | None, optional): The seed for the random number generator. If None, the deterministic tournament
                selection is used, i.e., the solution with the highest fitness in the tournament is always selected.
                Otherwise the selection is stochastic, and the solution is selected with a probability proportional to
                its fitness. Defaults to None.
            selection_probability (float | None, optional): The probability of selecting a solution in the tournament.
                If None, but a seed is provided, then the probabilities are proportional to the fitness values of the
                solutions in the tournament. If None and no seed is provided, then the selection is deterministic.
                If a value is provided, and the seed is not None, then the selection is stochastic, and the
                probabilities of choosing the k-best solution in the tournament is given by p * (1 - p) ** (k - 1),
                where p is the selection probability. Note that doing selection with a probability proportional to
                fitness is equivalent to roulette wheel selection.
        """
        super().__init__(verbosity=verbosity, publisher=publisher)
        self.winner_size = winner_size
        self.tournament_size = tournament_size
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.selection_probability = selection_probability
        if self.seed is None and self.selection_probability is not None:
            raise ValueError(
                "If selection_probability is provided, seed must also be provided to ensure stochastic selection."
            )

    @staticmethod
    def deterministic_select(indices: np.ndarray, fitness: np.ndarray) -> int:
        """Select the index of the solution with the highest fitness from the given indices.

        Args:
            indices (np.ndarray): The indices of the solutions to select from.
            fitness (np.ndarray): The fitness values of the solutions.

        Returns:
            int: The index of the solution with the highest fitness.
        """
        return indices[np.argmax(fitness)]

    def stochastic_select(self, indices: np.ndarray, fitness: np.ndarray) -> int:
        """Select the index of the solution with a probability proportional to its fitness from the given indices.

        Args:
            indices (np.ndarray): The indices of the solutions to select from.
            fitness (np.ndarray): The fitness values of the solutions.

        Returns:
            int: The index of the selected solution.
        """
        if self.selection_probability is None:
            probabilities = fitness / np.sum(fitness)
            probabilities = np.cumsum(probabilities)
        else:
            indices = indices[np.argsort(fitness)[::-1]]  # Sort indices by fitness in descending order
            probabilities = np.array(
                [self.selection_probability * (1 - self.selection_probability) ** i for i in range(len(indices))]
            )
        random_value = self.rng.random()
        selected_index = np.searchsorted(probabilities, random_value)
        return indices[selected_index]

    def _do(
        self, solutions: tuple[SolutionType, pl.DataFrame], fitness: np.ndarray | None = None
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Perform the tournament selection operation.

        Args:
            solutions (tuple[SolutionType, pl.DataFrame]): The decision variables and their outputs.
            fitness (np.ndarray | None, optional): The fitness values of the solutions.

        Returns:
            tuple[SolutionType, pl.DataFrame]: The selected decision variables and their outputs.
        """
        selected_indices = np.zeros(self.winner_size, dtype=int)
        for i in range(self.winner_size):
            tournament_indices = self.rng.choice(range(len(solutions[0])), size=self.tournament_size, replace=True)
            if self.seed is None:
                selected_indices[i] = self.deterministic_select(tournament_indices, fitness[tournament_indices])
            else:
                selected_indices[i] = self.stochastic_select(tournament_indices, fitness[tournament_indices])
        selected_solutions = solutions[0][selected_indices]
        selected_outputs = solutions[1][selected_indices]
        return selected_solutions, selected_outputs


class ElitistSelection(BaseScalarSelector):
    """Deterministic elitist selection: keep the top ``winner_size`` rows by a single output column.

    The selector ranks the combined ``(decision_variables, outputs)`` tuple by
    the values of ``outputs[target_column]`` (lower is better) and returns the
    best ``winner_size`` rows. No randomness, so the operation is reproducible.
    Useful as an elitist scheme for any single fitness column already present
    in the outputs DataFrame, e.g. an achievement scalarizing function value
    added via [desdeo.tools.scalarization.add_asf_nondiff][].
    """

    @property
    def provided_topics(self):
        """Topics published by this selector for each verbosity level."""
        return {
            0: [],
            1: [SelectorMessageTopics.STATE],
            2: [SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS, SelectorMessageTopics.SELECTED_FITNESS],
        }

    @property
    def interested_topics(self):
        """ElitistSelection reads its fitness column from the outputs DataFrame; no subscriptions needed."""
        return []

    def __init__(
        self,
        *,
        winner_size: int,
        target_column: str,
        verbosity: int,
        publisher: Publisher,
    ):
        """Initialize the elitist scalar selector.

        Args:
            winner_size (int): The number of individuals to keep after selection.
            target_column (str): Name of the output column to sort by (ascending,
                lower is better).
            verbosity (int): Verbosity level for emitted messages.
            publisher (Publisher): Publisher used to emit selection state.
        """
        super().__init__(verbosity=verbosity, publisher=publisher)
        self.winner_size = winner_size
        self.target_column = target_column
        self.selection: list[int] | None = None
        self.selected_individuals: SolutionType | None = None
        self.selected_targets: pl.DataFrame | None = None

    def do(
        self,
        solutions: tuple[SolutionType, pl.DataFrame],
        fitness: np.ndarray | None = None,
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Keep the top ``winner_size`` rows by ``target_column`` (ascending).

        Args:
            solutions (tuple[SolutionType, pl.DataFrame]): Combined parents and
                offspring as a single ``(decision_variables, outputs)`` tuple.
            fitness (np.ndarray | None, optional): Optional fitness override.
                If ``None`` (the usual case), the values in
                ``outputs[target_column]`` are used.

        Returns:
            tuple[SolutionType, pl.DataFrame]: The selected decision variables
                and their outputs.
        """
        decvars, outputs = solutions
        values = fitness if fitness is not None else outputs[self.target_column].to_numpy()
        order = np.argsort(values, kind="stable")
        chosen = order[: self.winner_size].tolist()

        if isinstance(decvars, pl.DataFrame):
            self.selected_individuals = decvars[chosen]
        else:
            self.selected_individuals = [decvars[i] for i in chosen]
        self.selected_targets = outputs[chosen]
        self.selection = chosen
        self.fitness = np.asarray(values)[chosen]

        self.notify()
        return self.selected_individuals, self.selected_targets

    def _do(
        self,
        solutions: tuple[SolutionType, pl.DataFrame],
        fitness: np.ndarray | None = None,
    ) -> tuple[SolutionType, pl.DataFrame]:
        """ABC requirement: delegate to the public `do()`."""
        return self.do(solutions, fitness)

    def state(self) -> Sequence[Message]:
        """Emit the selection state for archivers and other listeners."""
        if self.verbosity == 0 or self.selection is None or self.selected_targets is None:
            return []
        if self.verbosity == 1:
            return [
                DictMessage(
                    topic=SelectorMessageTopics.STATE,
                    value={
                        "winner_size": self.winner_size,
                        "selected_individuals": self.selection,
                    },
                    source=self.__class__.__name__,
                )
            ]
        # verbosity == 2
        if isinstance(self.selected_individuals, pl.DataFrame):
            message = PolarsDataFrameMessage(
                topic=SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
                value=pl.concat([self.selected_individuals, self.selected_targets], how="horizontal"),
                source=self.__class__.__name__,
            )
        else:
            warnings.warn("Population is not a Polars DataFrame. Defaulting to providing OUTPUTS only.", stacklevel=2)
            message = PolarsDataFrameMessage(
                topic=SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
                value=self.selected_targets,
                source=self.__class__.__name__,
            )
        return [
            DictMessage(
                topic=SelectorMessageTopics.STATE,
                value={
                    "winner_size": self.winner_size,
                    "selected_individuals": self.selection,
                },
                source=self.__class__.__name__,
            ),
            message,
            NumpyArrayMessage(
                topic=SelectorMessageTopics.SELECTED_FITNESS,
                value=self.fitness,
                source=self.__class__.__name__,
            ),
        ]

    def update(self, message: Message) -> None:
        """ElitistSelection has no subscriptions; ignore any messages."""
