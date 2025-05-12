"""Evolutionary operators for mutation.

Various evolutionary operators for mutation in multiobjective optimization are defined here.
"""

import copy
from abc import abstractmethod
from collections.abc import Sequence

import numpy as np
import polars as pl

from desdeo.problem import Problem, VariableDomainTypeEnum
from desdeo.tools.message import (
    FloatMessage,
    Message,
    MutationMessageTopics,
    PolarsDataFrameMessage,
)
from desdeo.tools.patterns import Subscriber


class BaseMutation(Subscriber):
    """A base class for mutation operators."""

    @abstractmethod
    def __init__(self, problem: Problem, **kwargs):
        """Initialize a mu operator."""
        super().__init__(**kwargs)
        self.problem = problem
        self.variable_symbols = [
            var.symbol for var in problem.get_flattened_variables()
        ]
        self.lower_bounds = [
            var.lowerbound for var in problem.get_flattened_variables()
        ]
        self.upper_bounds = [
            var.upperbound for var in problem.get_flattened_variables()
        ]
        self.variable_types = [
            var.variable_type for var in problem.get_flattened_variables()
        ]
        self.variable_combination: VariableDomainTypeEnum = problem.variable_domain

    @abstractmethod
    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Perform the mutation operation.

        Args:
            offsprings (pl.DataFrame): the offspring population to mutate.
            parents (pl.DataFrame): the parent population from which the offspring
                was generated (via crossover).

        Returns:
            pl.DataFrame: the offspring resulting from the mutation.
        """


class BoundedPolynomialMutation(BaseMutation):
    """Implements the bounded polynomial mutation operator.

    Reference:
        Deb, K., & Goyal, M. (1996). A combined genetic adaptive search (GeneAS) for
        engineering design. Computer Science and informatics, 26(4), 30-45, 1996.
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[MutationMessageTopics]]:
        """The message topics provided by the mutation operator."""
        return {
            0: [],
            1: [
                MutationMessageTopics.MUTATION_PROBABILITY,
                MutationMessageTopics.MUTATION_DISTRIBUTION,
            ],
            2: [
                MutationMessageTopics.MUTATION_PROBABILITY,
                MutationMessageTopics.MUTATION_DISTRIBUTION,
                MutationMessageTopics.OFFSPRING_ORIGINAL,
                MutationMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics that the mutation operator is interested in."""
        return []

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
        super().__init__(problem, **kwargs)
        if self.variable_combination != VariableDomainTypeEnum.continuous:
            raise ValueError(
                "This mutation operator only works with continuous variables."
            )
        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.lower_bounds)
        else:
            self.mutation_probability = mutation_probability
        self.distribution_index = distribution_index
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.offspring_original: pl.DataFrame
        self.parents: pl.DataFrame
        self.offspring: pl.DataFrame

    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Perform the mutation operation.

        Args:
            offsprings (pl.DataFrame): the offspring population to mutate.
            parents (pl.DataFrame): the parent population from which the offspring
                was generated (via crossover).

        Returns:
            pl.DataFrame: the offspring resulting from the mutation.
        """
        # TODO(@light-weaver): Extract to a numba jitted function
        self.offspring_original = offsprings
        self.parents = parents  # Not used, but kept for consistency
        offspring = offsprings.to_numpy()
        min_val = np.ones_like(offspring) * self.lower_bounds
        max_val = np.ones_like(offspring) * self.upper_bounds
        k = self.rng.random(size=offspring.shape)
        miu = self.rng.random(size=offspring.shape)
        temp = np.logical_and((k <= self.mutation_probability), (miu < 0.5))
        offspring_scaled = (offspring - min_val) / (max_val - min_val)
        offspring[temp] = offspring[temp] + (
            (max_val[temp] - min_val[temp])
            * (
                (
                    2 * miu[temp]
                    + (1 - 2 * miu[temp])
                    * (1 - offspring_scaled[temp]) ** (self.distribution_index + 1)
                )
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
                    + 2
                    * (miu[temp] - 0.5)
                    * offspring_scaled[temp] ** (self.distribution_index + 1)
                )
                ** (1 / (self.distribution_index + 1))
            )
        )
        offspring[offspring > max_val] = max_val[offspring > max_val]
        offspring[offspring < min_val] = min_val[offspring < min_val]
        self.offspring = pl.from_numpy(offspring, schema=self.variable_symbols)
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
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.OFFSPRING_ORIGINAL,
                source=self.__class__.__name__,
                value=self.offspring_original,
            ),
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.PARENTS,
                source=self.__class__.__name__,
                value=self.parents,
            ),
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.OFFSPRINGS,
                source=self.__class__.__name__,
                value=self.offspring,
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


class BinaryFlipMutation(BaseMutation):
    """Implements the bit flip mutation operator for binary variables.

    The binary flip mutation will mutate each binary decision variable,
    by flipping it (0 to 1, 1 to 0) with a provided probability.
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[MutationMessageTopics]]:
        """The message topics provided by the mutation operator."""
        return {
            0: [],
            1: [
                MutationMessageTopics.MUTATION_PROBABILITY,
            ],
            2: [
                MutationMessageTopics.MUTATION_PROBABILITY,
                MutationMessageTopics.OFFSPRING_ORIGINAL,
                MutationMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics that the mutation operator is interested in."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        seed: int,
        mutation_probability: float | None = None,
        **kwargs,
    ):
        """Initialize a binary flip mutation operator.

        Args:
            problem (Problem): The problem object.
            seed (int): The seed for the random number generator.
            mutation_probability (float | None, optional): The probability of mutation. If None,
                the probability will be set to be 1/n, where n is the number of decision variables
                in the problem. Defaults to None.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(problem, **kwargs)

        if self.variable_combination != VariableDomainTypeEnum.binary:
            raise ValueError("This mutation operator only works with binary variables.")
        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.variable_symbols)
        else:
            self.mutation_probability = mutation_probability

        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.offspring_original: pl.DataFrame
        self.parents: pl.DataFrame
        self.offspring: pl.DataFrame

    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Perform the binary flip mutation operation.

        Args:
            offsprings (pl.DataFrame): the offspring population to mutate.
            parents (pl.DataFrame): the parent population from which the offspring
                was generated (via crossover). Not used in the mutation operator.

        Returns:
            pl.DataFrame: the offspring resulting from the mutation.
        """
        self.offspring_original = copy.copy(offsprings)
        self.parents = parents  # Not used, but kept for consistency
        offspring = offsprings.to_numpy().astype(dtype=np.bool)

        # create a boolean mask based on the mutation probability
        flip_mask = self.rng.random(offspring.shape) < self.mutation_probability

        # using XOR (^), flip the bits in the offspring when the mask is True
        # otherwise leave the bit's value as it is
        offspring = offspring ^ flip_mask

        self.offspring = (
            pl.from_numpy(offspring, schema=self.variable_symbols)
            .select(pl.all())
            .cast(pl.Float64)
        )
        self.notify()

        return self.offspring

    def update(self, *_, **__):
        """Do nothing."""

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
            ]
        # verbosity == 2
        return [
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.OFFSPRING_ORIGINAL,
                source=self.__class__.__name__,
                value=self.offspring_original,
            ),
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.PARENTS,
                source=self.__class__.__name__,
                value=self.parents,
            ),
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.OFFSPRINGS,
                source=self.__class__.__name__,
                value=self.offspring,
            ),
            FloatMessage(
                topic=MutationMessageTopics.MUTATION_PROBABILITY,
                source=self.__class__.__name__,
                value=self.mutation_probability,
            ),
        ]


class IntegerRandomMutation(BaseMutation):
    """Implements a random mutation operator for integer variables.

    The mutation will mutate each binary integer variable,
    by changing its value to a random value bounded by the
    variable's bounds with a provided probability.
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[MutationMessageTopics]]:
        """The message topics provided by the mutation operator."""
        return {
            0: [],
            1: [
                MutationMessageTopics.MUTATION_PROBABILITY,
            ],
            2: [
                MutationMessageTopics.MUTATION_PROBABILITY,
                MutationMessageTopics.OFFSPRING_ORIGINAL,
                MutationMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics that the mutation operator is interested in."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        seed: int,
        mutation_probability: float | None = None,
        **kwargs,
    ):
        """Initialize a random integer mutation operator.

        Args:
            problem (Problem): The problem object.
            seed (int): The seed for the random number generator.
            mutation_probability (float | None, optional): The probability of mutation. If None,
                the probability will be set to be 1/n, where n is the number of decision variables
                in the problem. Defaults to None.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(problem, **kwargs)

        if self.variable_combination != VariableDomainTypeEnum.integer:
            raise ValueError(
                "This mutation operator only works with integer variables."
            )
        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.variable_symbols)
        else:
            self.mutation_probability = mutation_probability

        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.offspring_original: pl.DataFrame
        self.parents: pl.DataFrame
        self.offspring: pl.DataFrame

    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Perform the random integer mutation operation.

        Args:
            offsprings (pl.DataFrame): the offspring population to mutate.
            parents (pl.DataFrame): the parent population from which the offspring
                was generated (via crossover). Not used in the mutation operator.

        Returns:
            pl.DataFrame: the offspring resulting from the mutation.
        """
        self.offspring_original = copy.copy(offsprings)
        self.parents = parents  # Not used, but kept for consistency

        population = offsprings.to_numpy().astype(int)

        # create a boolean mask based on the mutation probability
        mutation_mask = self.rng.random(population.shape) < self.mutation_probability

        mutated = np.where(
            mutation_mask,
            self.rng.integers(
                self.lower_bounds,
                self.upper_bounds,
                size=population.shape,
                dtype=int,
                endpoint=True,
            ),
            population,
        )

        self.offspring = (
            pl.from_numpy(mutated, schema=self.variable_symbols)
            .select(pl.all())
            .cast(pl.Float64)
        )
        self.notify()

        return self.offspring

    def update(self, *_, **__):
        """Do nothing."""

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
            ]
        # verbosity == 2
        return [
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.OFFSPRING_ORIGINAL,
                source=self.__class__.__name__,
                value=self.offspring_original,
            ),
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.PARENTS,
                source=self.__class__.__name__,
                value=self.parents,
            ),
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.OFFSPRINGS,
                source=self.__class__.__name__,
                value=self.offspring,
            ),
            FloatMessage(
                topic=MutationMessageTopics.MUTATION_PROBABILITY,
                source=self.__class__.__name__,
                value=self.mutation_probability,
            ),
        ]


class UniformMutation(BaseMutation):
    """Implements uniform mutation operator.
    Reference:
    Back, Thomas. Evolutionary Algorithms in Theory and Practice, 1996
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[MutationMessageTopics]]:
        """The message topics provided by the mutation operator."""
        return {
            0: [],
            1: [
                MutationMessageTopics.MUTATION_PROBABILITY,
                MutationMessageTopics.MUTATION_DISTRIBUTION,
            ],
            2: [
                MutationMessageTopics.MUTATION_PROBABILITY,
                MutationMessageTopics.MUTATION_DISTRIBUTION,
                MutationMessageTopics.OFFSPRING_ORIGINAL,
                MutationMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics that the mutation operator is interested in."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        seed: int,
        mutation_probability: float | None = None,
        distribution_index: float = 20,
        **kwargs,
    ):
        """Initialize an uniform mutation operator.

        Args:
            problem (Problem): The problem object.
            seed (int): The seed for the random number generator.
            mutation_probability (float | None, optional): The probability of mutation. Defaults to None.
            distribution_index (float, optional): The distributaion index for polynomial mutation. Defaults to 20.
            kwargs: Additional keyword arguments. These are passed to the Subscriber class. At the very least, the
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(problem, **kwargs)
        if self.variable_combination != VariableDomainTypeEnum.continuous:
            raise ValueError(
                "This mutation operator only works with continuous variables."
            )
        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.lower_bounds)
        else:
            self.mutation_probability = mutation_probability
        self.distribution_index = distribution_index
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.offspring_original: pl.DataFrame
        self.parents: pl.DataFrame
        self.offspring: pl.DataFrame

    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Perform the mutation operation.

        Args:
            offsprings (pl.DataFrame): the offspring population to mutate.
            parents (pl.DataFrame): the parent population from which the offspring
                was generated (via crossover).

        Returns:
            pl.DataFrame: the offspring resulting from the mutation.
        """
        # TODO(@light-weaver): Extract to a numba jitted function
        self.offspring_original = offsprings
        self.parents = parents  # Not used, but kept for consistency
        offspring = offsprings.to_numpy()
        min_val = np.ones_like(offspring) * self.lower_bounds
        max_val = np.ones_like(offspring) * self.upper_bounds

        k = self.rng.random(size=offspring.shape)
        miu = self.rng.random(size=offspring.shape)

        for i in range(len(offspring)):
            for j in range(len(offspring[i])):
                y = offspring[i][j]
                if np.random.rand() < self.mutation_probability:
                    rand = np.random.rand()
                    tmp = (rand - 0.5) * self.mutation_probability
                    tmp += y
                    offspring[i][j] = tmp

        offspring[offspring > max_val] = max_val[offspring > max_val]
        offspring[offspring < min_val] = min_val[offspring < min_val]

        self.offspring = pl.from_numpy(offspring, schema=self.variable_symbols)
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
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.OFFSPRING_ORIGINAL,
                source=self.__class__.__name__,
                value=self.offspring_original,
            ),
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.PARENTS,
                source=self.__class__.__name__,
                value=self.parents,
            ),
            PolarsDataFrameMessage(
                topic=MutationMessageTopics.OFFSPRINGS,
                source=self.__class__.__name__,
                value=self.offspring,
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
