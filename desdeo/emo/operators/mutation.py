"""Evolutionary operators for mutation.

Various evolutionary operators for mutation in multiobjective optimization are defined here.
"""

from abc import abstractmethod
from collections.abc import Sequence

import numpy as np

from desdeo.problem import Problem, TensorVariable
from desdeo.tools.message import Array2DMessage, FloatMessage, Message, MutationMessageTopics, StringMessage
from desdeo.tools.patterns import Subscriber


class BaseMutation(Subscriber):
    """A base class for mutation operators."""

    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize a mu operator."""
        super().__init__(**kwargs)

    @abstractmethod
    def do(self, offsprings: np.ndarray, parents: np.ndarray) -> np.ndarray:
        """Perform the mutation operation.

        Args:
            offsprings (np.ndarray): the offspring population to mutate.
            parents (np.ndarray): the parent population from which the offspring
                was generated (via crossover).

        Returns:
            np.ndarray: the offspring resulting from the mutation.
        """


class TestMutation(BaseMutation):
    """Just a test mutation operator."""

    def __init__(self, problem: Problem, **kwargs):
        """Initialize a test mutation operator."""
        super().__init__(**kwargs)

    def do(self, offsprings: np.ndarray, parents: np.ndarray) -> np.ndarray:
        """Perform the test mutation operation.

        Args:
            offsprings (np.ndarray): the offspring population to mutate.
            parents (np.ndarray): the parent population from which the offspring
                was generated (via crossover).

        Returns:
            np.ndarray: the offspring resulting from the mutation.
        """
        return offsprings

    def update(self, *_, **__):
        """Do nothing. This is just the test mutation operator."""

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        return [StringMessage(topic=MutationMessageTopics.TEST, value="Called", source=self.__class__.__name__)]


class BoundedPolynomialMutation(BaseMutation):
    """A bounded polynomial mutation operator.

    This operator is based on the polynomial mutation operator described in
    Deb, K., & Goyal, M. (1996). A combined genetic adaptive search (GeneAS) for
    engineering design. Computer Science and informatics, 26(4), 30-45, 1996.
    """

    def __init__(
        self,
        *,
        problem: Problem,
        seed: int,
        mutation_probability: float | None = None,
        distribution_index: float = 20,
        **kwargs,
    ):
        """Initialize a bounded polynomial mutation operator.

        Args:
            problem (Problem): The problem object.
            seed (int): The seed for the random number generator.
            mutation_probability (float | None, optional): The probability of mutation. Defaults to None.
            distribution_index (float, optional): The distributaion index for polynomial mutation. Defaults to 20.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(**kwargs)
        if any(isinstance(var, TensorVariable) for var in problem.variables):
            raise TypeError("Crossover does not support tensor variables yet.")
        self.bounds = np.array([[var.lowerbound, var.upperbound] for var in problem.variables])
        self.lower_limits = self.bounds[:, 0]
        self.upper_limits = self.bounds[:, 1]
        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.lower_limits)
        else:
            self.mutation_probability = mutation_probability
        self.distribution_index = distribution_index
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.offspring_original: np.ndarray | None = None
        self.offspring: np.ndarray | None = None
        match self.verbosity:
            case 0:
                self.provided_topics = []
            case 1:
                self.provided_topics = [
                    MutationMessageTopics.MUTATION_PROBABILITY,
                    MutationMessageTopics.MUTATION_DISTRIBUTION,
                ]
            case 2:
                self.provided_topics = [
                    MutationMessageTopics.MUTATION_PROBABILITY,
                    MutationMessageTopics.MUTATION_DISTRIBUTION,
                    MutationMessageTopics.OFFSPRING_ORIGINAL,
                    MutationMessageTopics.OFFSPRINGS,
                ]

    def do(self, offspring: np.ndarray, *_, **__) -> np.ndarray:
        """Conduct bounded polynomial mutation. Return the mutated individuals.

        Parameters:
        ----------
        offspring : np.ndarray
            The array of offsprings to be mutated.

        Returns:
        -------
        np.ndarray
            The mutated offsprings
        """
        # TODO(@light-weaver): Extract to a numba jitted function
        min_val = np.ones_like(offspring) * self.lower_limits
        max_val = np.ones_like(offspring) * self.upper_limits
        k = self.rng.random(size=offspring.shape)
        miu = self.rng.random(size=offspring.shape)
        temp = np.logical_and((k <= self.mutation_probability), (miu < 0.5))
        self.offspring_original = offspring.copy()
        offspring_scaled = (offspring - min_val) / (max_val - min_val)
        offspring[temp] = offspring[temp] + (
            (max_val[temp] - min_val[temp])
            * (
                (2 * miu[temp] + (1 - 2 * miu[temp]) * (1 - offspring_scaled[temp]) ** (self.distribution_index + 1))
                ** (1 / (self.distribution_index + 1))
                - 1
            )
        )
        temp = np.logical_and((k <= self.mutation_probability), (miu >= 0.5))
        offspring[temp] = offspring[temp] + (
            (max_val[temp] - min_val[temp])
            * (
                1
                - (
                    2 * (1 - miu[temp])
                    + 2 * (miu[temp] - 0.5) * offspring_scaled[temp] ** (self.distribution_index + 1)
                )
                ** (1 / (self.distribution_index + 1))
            )
        )
        offspring[offspring > max_val] = max_val[offspring > max_val]
        offspring[offspring < min_val] = min_val[offspring < min_val]
        self.offspring = offspring
        self.notify()
        return self.offspring

    def update(self, *_, **__):
        """Do nothing. This is just the basic polynomial mutation operator."""

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        if self.offspring_original is None or self.offspring is None:
            return []
        if self.verbosity == 0:
            return []
        if self.verbosity == 1:
            return [
                FloatMessage(
                    topic=MutationMessageTopics.MUTATION_PROBABILITY,
                    source=self.__class__.__name__,
                    value=self.mutation_probability,
                ),
                FloatMessage(
                    topic=MutationMessageTopics.MUTATION_DISTRIBUTION,
                    source=self.__class__.__name__,
                    value=self.distribution_index,
                ),
            ]
        # verbosity == 2
        return [
            Array2DMessage(
                topic=MutationMessageTopics.OFFSPRING_ORIGINAL,
                source=self.__class__.__name__,
                value=self.offspring_original.tolist(),
            ),
            Array2DMessage(
                topic=MutationMessageTopics.OFFSPRINGS,
                source=self.__class__.__name__,
                value=self.offspring.tolist(),
            ),
            FloatMessage(
                topic=MutationMessageTopics.MUTATION_PROBABILITY,
                source=self.__class__.__name__,
                value=self.mutation_probability,
            ),
            FloatMessage(
                topic=MutationMessageTopics.MUTATION_DISTRIBUTION,
                source=self.__class__.__name__,
                value=self.distribution_index,
            ),
        ]
