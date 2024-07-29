"""Classes for evaluating the objectives and constraints of the individuals in the population."""

from collections.abc import Callable, Sequence

import numpy as np

from desdeo.problem import Problem
from desdeo.tools.message import Array2DMessage, EvaluatorMessageTopics, IntMessage, Message
from desdeo.tools.patterns import Subscriber

ObjEvaluator = Callable[[Sequence], np.ndarray]
ConsEvaluator = Callable[[Sequence], np.ndarray | None]
TargetsEvaluator = Callable[[np.ndarray], np.ndarray]


class BaseEvaluator(Subscriber):
    """Base class for evaluating the objectives and constraints of the individuals in the population.

    This class should be inherited by the classes that implement the evaluation of the objectives
    and constraints of the individuals in the population.

    """

    def __init__(
        self,
        problem: Problem,
        obj_evaluator: ObjEvaluator,
        cons_evaluator: ConsEvaluator,
        targets_evaluator: TargetsEvaluator,
        verbosity: int = 1,
        **kwargs,
    ):
        """Initialize the BaseEvaluator class."""
        super().__init__(**kwargs)
        self.problem = problem
        self.obj_evaluator = obj_evaluator
        self.cons_evaluator = cons_evaluator
        self.targets_evaluator = targets_evaluator
        self.population: Sequence | None = None
        self.objs: np.ndarray | None = None
        self.targets: np.ndarray | None = None
        self.cons: np.ndarray | None = None
        self.verbosity: int = verbosity
        self.new_evals: int = 0
        match self.verbosity:
            case 0:
                self.provided_topics = []
            case 1:
                self.provided_topics = [EvaluatorMessageTopics.NEW_EVALUATIONS]
            case 2:
                self.provided_topics = [
                    EvaluatorMessageTopics.NEW_EVALUATIONS,
                    EvaluatorMessageTopics.POPULATION,
                    EvaluatorMessageTopics.OBJECTIVES,
                    EvaluatorMessageTopics.CONSTRAINTS,
                    EvaluatorMessageTopics.TARGETS,
                ]

    def evaluate(self, population: Sequence) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        """Evaluate and return the objectives.

        Args:
            population (Iterable): The set of decision variables to evaluate.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray | None]: Tuple of objective vectors, target vectors, and
                constraint vectors.
        """
        self.population = population
        # TODO(@light-weaver): Replace the code below with calls to the Problem object.
        # For now, this is a hack.
        self.objs = self.obj_evaluator(population)
        self.cons = self.cons_evaluator(population)
        self.targets = self.targets_evaluator(self.objs)
        self.new_evals = len(population)
        self.notify()
        return self.objs, self.targets, self.cons

    def state(self) -> Sequence[Message] | None:
        """The state of the evaluator sent to the Publisher."""
        if self.population is None or self.objs is None or self.cons is None or self.targets is None:
            return None
        if self.verbosity == 0:
            return None
        if self.verbosity == 1:
            return [
                IntMessage(
                    topic=EvaluatorMessageTopics.NEW_EVALUATIONS,
                    value=self.new_evals,
                    source="BaseEvaluator",
                )
            ]
        return [
            IntMessage(
                topic=EvaluatorMessageTopics.NEW_EVALUATIONS,
                value=self.new_evals,
                source="BaseEvaluator",
            ),
            Array2DMessage(
                topic=EvaluatorMessageTopics.POPULATION,
                value=self.population.tolist(),
                source="BaseEvaluator",
            ),
            Array2DMessage(
                topic=EvaluatorMessageTopics.OBJECTIVES,
                value=self.objs.tolist(),
                source="BaseEvaluator",
            ),
            Array2DMessage(
                topic=EvaluatorMessageTopics.CONSTRAINTS,
                value=self.cons.tolist(),
                source="BaseEvaluator",
            ),
            Array2DMessage(
                topic=EvaluatorMessageTopics.TARGETS,
                value=self.targets.tolist(),
                source="BaseEvaluator",
            ),
        ]

    def update(self, *_, **__):
        """Update the parameters of the evaluator."""
