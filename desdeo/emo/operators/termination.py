"""The base class for termination criteria.

The termination criterion is used to determine when the optimization process should stop. In this implementation, it
also includes a simple counter for the number of elapsed generations. This counter is increased by one each time the
termination criterion is called. The simplest termination criterion is reaching the maximum number of generations.
The implementation also contains a counter for the number of evaluations. This counter is updated by the Evaluator
and Generator classes. The termination criterion can be based on the number of evaluations as well.

Warning:
    Each subclass of BaseTerminator must implement the do method. The do method should always call the
    super().do method to increment the generation counter _before_ conducting the termination check.
"""

from abc import abstractmethod
from collections.abc import Sequence

from desdeo.tools.message import (
    EvaluatorMessageTopics,
    GeneratorMessageTopics,
    IntMessage,
    Message,
    TerminatorMessageTopics,
)
from desdeo.tools.patterns import Publisher, Subscriber


class BaseTerminator(Subscriber):
    """The base class for the termination criteria.

    Also includes a simple counter for number of elapsed generations. This counter is increased by one each time the
    termination criterion is called.
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[TerminatorMessageTopics]]:
        """Return the topics provided by the terminator.

        Returns:
            dict[int, Sequence[TerminatorMessageTopics]]: The topics provided by the terminator.
        """
        return {
            0: [],
            1: [
                TerminatorMessageTopics.GENERATION,
                TerminatorMessageTopics.EVALUATION,
                TerminatorMessageTopics.MAX_GENERATIONS,
                TerminatorMessageTopics.MAX_EVALUATIONS,
            ],
        }

    @property
    def interested_topics(self):
        """Return the message topics that the terminator is interested in."""
        return [EvaluatorMessageTopics.NEW_EVALUATIONS, GeneratorMessageTopics.NEW_EVALUATIONS]

    def __init__(self, publisher: Publisher):
        """Initialize a termination criterion."""
        super().__init__(publisher=publisher, verbosity=1)
        self.current_generation: int = 1
        self.current_evaluations: int = 0
        self.max_generations: int = 0
        self.max_evaluations: int = 0

    def check(self) -> bool:
        """Check if the termination criterion is reached.

        Returns:
            bool: True if the termination criterion is reached, False otherwise.
        """
        self.current_generation += 1
        self.notify()

    def state(self) -> Sequence[Message]:
        """Return the state of the termination criterion."""
        state = [
            IntMessage(
                topic=TerminatorMessageTopics.GENERATION,
                value=self.current_generation,
                source=self.__class__.__name__,
            ),
            IntMessage(
                topic=TerminatorMessageTopics.EVALUATION, value=self.current_evaluations, source=self.__class__.__name__
            ),
        ]
        if self.max_evaluations != 0:
            state.append(
                IntMessage(
                    topic=TerminatorMessageTopics.MAX_EVALUATIONS,
                    value=self.max_evaluations,
                    source=self.__class__.__name__,
                )
            )
        if self.max_generations != 0:
            state.append(
                IntMessage(
                    topic=TerminatorMessageTopics.MAX_GENERATIONS,
                    value=self.max_generations,
                    source=self.__class__.__name__,
                )
            )
        return state

    def update(self, message: Message) -> None:
        """Update the number of evaluations.

        Note that for this method to work, this class must be registered as an observer of a subject that sends
        messages with the key "num_evaluations". The Evaluator class does this.

        Args:
            message (dict): the message from the subject, must contain the key "num_evaluations".
        """
        if not isinstance(message, IntMessage):
            return
        if not (isinstance(message.topic, EvaluatorMessageTopics) or isinstance(message.topic, GeneratorMessageTopics)):
            return
        if (
            message.topic == EvaluatorMessageTopics.NEW_EVALUATIONS  # NOQA: PLR1714
            or message.topic == GeneratorMessageTopics.NEW_EVALUATIONS
        ):
            self.current_evaluations += message.value


class MaxGenerationsTerminator(BaseTerminator):
    """A class for a termination criterion based on the number of generations."""

    def __init__(self, max_generations: int, publisher: Publisher):
        """Initialize a termination criterion based on the number of generations.

        Args:
            max_generations (int): the maximum number of generations.
            publisher (Publisher): The publisher to which the terminator will publish its state.
        """
        super().__init__(publisher=publisher)
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
        return self.current_generation > self.max_generations


# TODO (@light-weaver): This check is done _after_ the evaluations have taken place.
# This means that the algorithm will run for one more generation than it should.
class MaxEvaluationsTerminator(BaseTerminator):
    """A class for a termination criterion based on the number of evaluations."""

    def __init__(self, max_evaluations: int, publisher: Publisher):
        """Initialize a termination criterion based on the number of evaluations.

        Looks for messages with key "num_evaluations" to update the number of evaluations.

        Args:
            max_evaluations (int): the maximum number of evaluations.
            publisher (Publisher): The publisher to which the terminator will publish its state.
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(publisher=publisher)
        if not isinstance(max_evaluations, int) or max_evaluations < 0:
            raise ValueError("max_evaluations must be a non-negative integer")
        self.max_evaluations = max_evaluations
        self.current_evaluations = 0

    def check(self) -> bool:
        """Check if the termination criterion based on the number of generations is reached.

        Args:
            new_generation (bool, optional): Increment the generation counter. Defaults to True.

        Returns:
            bool: True if the termination criterion is reached, False otherwise.
        """
        super().check()
        self.notify()
        return self.current_evaluations >= self.max_evaluations


class CompositeTerminator(BaseTerminator):
    """Combines multiple terminators using logical AND or OR."""

    def __init__(self, terminators: list[BaseTerminator], publisher: Publisher, mode: str = "any"):
        """Initialize a composite termination criterion.

        Args:
            terminators (list[BaseTerminator]): List of BaseTerminator instances.
            publisher (Publisher): Publisher for passing messages.
            mode (str): "any" (terminate if any) or "all" (terminate if all). By default, "any".
        """
        super().__init__(publisher=publisher)
        self.terminators = terminators
        for t in self.terminators:
            t.notify = lambda: None
        self.mode = mode

    def check(self) -> bool:
        """Check if the termination criterion is reached.

        Returns:
            bool: True if the termination criterion is reached, False otherwise.
        """
        super().check()
        results = [t.check() for t in self.terminators]
        if self.mode == "all":
            return all(results)
        return any(results)
