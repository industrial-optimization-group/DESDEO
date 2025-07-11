"""Defines the messaging protocol used by the various EMO operators."""

from enum import Enum
from typing import Any, Literal

import numpy as np
from polars import DataFrame
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class CrossoverMessageTopics(Enum):
    """Topics for messages related to crossover operators."""

    TEST = "TEST"
    """ A message topic used only for testing the crossover operators. """
    XOVER_PROBABILITY = "XOVER_PROBABILITY"
    """ The current crossover probability. """
    XOVER_DISTRIBUTION = "XOVER_DISTRIBUTION"
    """ The current crossover distribution index. Primary used in the SBX crossover. """
    PARENTS = "PARENTS"
    """ The parents selected for crossover. """
    OFFSPRINGS = "OFFSPRINGS"
    """ The offsprings generated from the crossover. """
    ALPHA = "ALPHA"
    """ Alpha parameter used in crossover. """
    LAMBDA = "LAMBDA"
    """ Lambda parameter used in crossover. Primarily used in the bounded exponential xover. """


class MutationMessageTopics(Enum):
    """Topics for messages related to mutation operators."""

    TEST = "TEST"
    """ A message topic used only for testing the mutation operators. """
    MUTATION_PROBABILITY = "MUTATION_PROBABILITY"
    """ The current mutation probability. """
    MUTATION_DISTRIBUTION = "MUTATION_DISTRIBUTION"
    """ The current mutation distribution index. Primary used in the polynomial mutation. """
    OFFSPRING_ORIGINAL = "OFFSPRING_ORIGINAL"
    """ The original offsprings before mutation. """
    OFFSPRINGS = "OFFSPRINGS"
    """ The offsprings after mutation. """
    PARENTS = "PARENTS"
    """ The parents of the offsprings. """


class EvaluatorMessageTopics(Enum):
    """Topics for messages related to evaluator operators."""

    TEST = "TEST"
    """ A message topic used only for testing the evaluator operators. """
    POPULATION = "POPULATION"
    """ The population to evaluate. """
    OUTPUTS = "OUTPUTS"
    """ The outputs of the population. Contains objectives, targets, constraints. """
    OBJECTIVES = "OBJECTIVES"
    """ The true objective values of the population. """
    TARGETS = "TARGETS"
    """ The targets, i.e., objective values seen by the evolutionary operators."""
    CONSTRAINTS = "CONSTRAINTS"
    """ The constraints of the population. """
    VERBOSE_OUTPUTS = "VERBOSE_OUTPUTS"
    """ Same as POPULATION + OUTPUTS."""
    NEW_EVALUATIONS = "NEW_EVALUATIONS"
    """ The number of new evaluations. """


class GeneratorMessageTopics(Enum):
    """Topics for messages related to population generator operators."""

    TEST = "TEST"
    """ A message topic used only for testing the evaluator operators. """
    POPULATION = "POPULATION"
    """ The population to evaluate. """
    OUTPUTS = "OUTPUTS"
    """ The outputs of the population generation. Contains objectives, targets, and constraints. """
    OBJECTIVES = "OBJECTIVES"
    """ The true objective values of the population. """
    TARGETS = "TARGETS"
    """ The targets, i.e., objective values seen by the evolutionary operators."""
    CONSTRAINTS = "CONSTRAINTS"
    """ The constraints of the population. """
    VERBOSE_OUTPUTS = "VERBOSE_OUTPUTS"
    """ Same as POPULATION + OUTPUTS. """
    NEW_EVALUATIONS = "NEW_EVALUATIONS"
    """ The number of new evaluations. """


class SelectorMessageTopics(Enum):
    """Topics for messages related to selector operators."""

    TEST = "TEST"
    """ A message topic used only for testing the selector operators. """
    STATE = "STATE"
    """ The state of the parameters of the selector. """
    INDIVIDUALS = "INDIVIDUALS"
    """ The individuals to select from. """
    OUTPUTS = "OUTPUTS"
    """ The outputs of the individuals. """
    CONSTRAINTS = "CONSTRAINTS"
    """ The constraints of the individuals. """
    SELECTED_INDIVIDUALS = "SELECTED_INDIVIDUALS"
    """ The individuals selected by the selector. """
    SELECTED_OUTPUTS = "SELECTED_OUTPUTS"
    """ The targets of the selected individuals. """
    SELECTED_FITNESS = "SELECTED_FITNESS"
    """ The fitness of the selected individuals. This is the fitness calculated by the selector, not the objectives."""
    SELECTED_VERBOSE_OUTPUTS = "SELECTED_VERBOSE_OUTPUTS"
    """ Same as SELECTED_OUTPUTS + SELECTED_INDIVIDUALS"""
    REFERENCE_VECTORS = "REFERENCE_VECTORS"
    """ The reference vectors used in the selection in decomposition-based EMO algorithms. """


class TerminatorMessageTopics(Enum):
    """Topics for messages related to terminator operators."""

    TEST = "TEST"
    """ A message topic used only for testing the terminator operators. """
    STATE = "STATE"
    """ The state of the parameters of the terminator. """
    TERMINATION = "TERMINATION"
    """ The value of the termination condition. """
    GENERATION = "GENERATION"
    """ The current generation number. """
    EVALUATION = "EVALUATION"
    """ The current number of evaluations. """
    MAX_GENERATIONS = "MAX_GENERATIONS"
    """ The maximum number of generations. """
    MAX_EVALUATIONS = "MAX_EVALUATIONS"
    """ The maximum number of evaluations. """


MessageTopics = (
    CrossoverMessageTopics
    | MutationMessageTopics
    | EvaluatorMessageTopics
    | GeneratorMessageTopics
    | SelectorMessageTopics
    | TerminatorMessageTopics
    | Literal["ALL"]  # Used to indicate that all topics are of interest to a subscriber.
)


class BaseMessage(BaseModel):
    """A message containing an integer value."""

    topic: MessageTopics = Field(..., description="The topic of the message.")
    """ The topic of the message. """
    source: str = Field(..., description="The source of the message.")
    """ The source of the message. """


class IntMessage(BaseMessage):
    """A message containing an integer value."""

    value: int = Field(..., description="The integer value of the message.")
    """ The integer value of the message. """


class FloatMessage(BaseMessage):
    """A message containing a float value."""

    value: float = Field(..., description="The float value of the message.")
    """ The float value of the message. """


class StringMessage(BaseMessage):
    """A message containing a string value."""

    value: str = Field(..., description="The string value of the message.")
    """ The string value of the message. """


class BoolMessage(BaseMessage):
    """A message containing a boolean value."""

    value: bool = Field(..., description="The boolean value of the message.")
    """ The boolean value of the message. """


class DictMessage(BaseMessage):
    """A message containing a dictionary value."""

    value: dict[str, Any] = Field(..., description="The dictionary value of the message.")
    """ The dictionary value of the message. """


class Array2DMessage(BaseMessage):
    """A message containing a 2D array value, such as a population or a set of objectives."""

    value: list[list[float]] = Field(..., description="The array value of the message.")
    """ The array value of the message. """


class PolarsDataFrameMessage(BaseMessage):
    """A message containing a 2D array value, such as a population or a set of objectives."""

    value: DataFrame = Field(..., description="The array value of the message.")
    """ The array value of the message. """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("value")
    def _serialize_value(self, value: DataFrame) -> dict[str, list[int | float]]:
        return value.to_dict(as_series=False)


class NumpyArrayMessage(BaseMessage):
    """A message containing a numpy array value."""

    value: np.ndarray = Field(..., description="The numpy array value of the message.")
    """ The numpy array value of the message. """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("value")
    def _serialize_value(self, value: np.ndarray) -> list[list[float]]:
        return value.tolist()


class GenericMessage(BaseMessage):
    """A message containing a generic value."""

    value: Any = Field(..., description="The generic value of the message.")
    """ The generic value of the message. """


Message = (
    IntMessage
    | FloatMessage
    | DictMessage
    | Array2DMessage
    | GenericMessage
    | StringMessage
    | BoolMessage
    | PolarsDataFrameMessage
    | NumpyArrayMessage
)

AllowedMessagesAtVerbosity: dict[int, tuple[type[Message], ...]] = {
    0: (),
    1: (IntMessage, FloatMessage, StringMessage, BoolMessage),
    2: (
        IntMessage,
        FloatMessage,
        StringMessage,
        BoolMessage,
        DictMessage,
        Array2DMessage,
        GenericMessage,
        PolarsDataFrameMessage,
        NumpyArrayMessage,
    ),
}
