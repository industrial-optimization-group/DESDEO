"""Evolutionary operators for mutation.

Various evolutionary operators for mutation in multiobjective optimization are defined here.
"""

import copy
from abc import abstractmethod
from collections.abc import Sequence

import numpy as np
import polars as pl

from desdeo.problem import Problem, VariableDomainTypeEnum, VariableTypeEnum
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
        self.variable_symbols = [var.symbol for var in problem.get_flattened_variables()]
        self.lower_bounds = [var.lowerbound for var in problem.get_flattened_variables()]
        self.upper_bounds = [var.upperbound for var in problem.get_flattened_variables()]
        self.variable_types = [var.variable_type for var in problem.get_flattened_variables()]
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
            raise ValueError("This mutation operator only works with continuous variables.")
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

        self.offspring = pl.from_numpy(offspring, schema=self.variable_symbols).select(pl.all()).cast(pl.Float64)
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
            raise ValueError("This mutation operator only works with integer variables.")
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
            self.rng.integers(self.lower_bounds, self.upper_bounds, size=population.shape, dtype=int, endpoint=True),
            population,
        )

        self.offspring = pl.from_numpy(mutated, schema=self.variable_symbols).select(pl.all()).cast(pl.Float64)
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


class MixedIntegerRandomMutation(BaseMutation):
    """Implements a random mutation operator for mixed-integer variables.

    The mutation will mutate each mixed-integer variable,
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
        """Initialize a random mixed_integer mutation operator.

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

        population = offsprings.to_numpy().astype(float)

        # create a boolean mask based on the mutation probability
        mutation_mask = self.rng.random(population.shape) < self.mutation_probability

        mutation_pool = np.array(
            [
                self.rng.integers(
                    low=var.lowerbound, high=var.upperbound, size=population.shape[0], endpoint=True
                ).astype(dtype=float)
                if var.variable_type in [VariableTypeEnum.binary, VariableTypeEnum.integer]
                else self.rng.uniform(low=var.lowerbound, high=var.upperbound, size=population.shape[0]).astype(
                    dtype=float
                )
                for var in self.problem.variables
            ]
        ).T

        mutated = np.where(
            mutation_mask,
            # self.rng.integers(self.lower_bounds, self.upper_bounds, size=population.shape, dtype=int, endpoint=True),
            mutation_pool,
            population,
        )

        self.offspring = pl.from_numpy(mutated, schema=self.variable_symbols).select(pl.all()).cast(pl.Float64)
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


class NonUniformMutation(BaseMutation):
    """
    Non-uniform mutation operator.
    The mutation strength decays over generations.
    """

    @property
    def provided_topics(self) -> dict[int, Sequence[MutationMessageTopics]]:
        """The message topics provided by the mutation operator."""
        return {
            0: [],
            1: [MutationMessageTopics.MUTATION_PROBABILITY],
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
        b: float = 5.0,  # decay parameter
        max_generations: int,
        **kwargs,
    ):
        """
        Initialize a Non-uniform mutation operator.

        Args:
            problem (Problem): The optimization problem definition.
            seed (int): Random number generator seed for reproducibility.
            mutation_probability (float | None): Probability of mutating each gene. If None, defaults to 1 / number of variables.
            b (float): Non-uniform mutation decay parameter. Higher values cause faster reduction in mutation strength over generations.
            max_generations (int): Maximum number of generations in the evolutionary run. Used to scale mutation decay.
            **kwargs: Additional keyword arguments passed to the base mutation class.
        """
        super().__init__(problem, **kwargs)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.b = b
        self.current_generation = 0
        self.max_generations = max_generations
        self.mutation_probability = (
            1 / len(self.variable_symbols) if mutation_probability is None else mutation_probability
        )

    def _mutate_value(self, x, l, u):
        """
        Apply non-uniform mutation to a single float value.

        Args:
            x (float): The current value of the gene to be mutated.
            l (float): The lower bound of the gene.
            u (float): The upper bound of the gene.

        Returns:
            float: The mutated gene value, clipped within the bounds [l, u].
        """
        r = self.rng.uniform(0, 1)  # Random number to choose direction
        t = self.current_generation
        T = self.max_generations
        b = self.b

        u_rand = self.rng.uniform(0, 1)  # Random number for mutation strength
        tau = (1 - t / T) ** b

        if r <= 0.5:
            y = u - x
            delta = y * (1 - u_rand ** tau)
            xm = x + delta
        else:
            y = x - l
            delta = y * (1 - u_rand ** tau)
            xm = x - delta

        return np.clip(xm, l, u)

    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Perform non-uniform mutation.

        Args:
        offsprings (pl.DataFrame): The current offspring population to mutate. Each row corresponds to one individual.
        parents (pl.DataFrame): The parent population (not used in mutation but passed for interface consistency).

        Returns:
            pl.DataFrame: A new offspring population with mutated values applied. Returned as a Polars DataFrame.
        """
        self.offspring_original = copy.copy(offsprings)
        self.parents = parents

        population = offsprings.to_numpy().astype(float)

        for i in range(population.shape[0]):
            for j, var in enumerate(self.problem.variables):
                if self.rng.random() < self.mutation_probability:
                    x = population[i, j]
                    l, u = var.lowerbound, var.upperbound
                    if var.variable_type in [VariableTypeEnum.binary, VariableTypeEnum.integer]:
                        population[i, j] = round(self._mutate_value(x, l, u))
                    else:
                        population[i, j] = self._mutate_value(x, l, u)

        self.offspring = pl.from_numpy(population, schema=self.variable_symbols).cast(pl.Float64)
        self.notify()
        return self.offspring

    def update(self, generation: int, **kwargs):
        """Update current generation (used to reduce mutation strength over time)."""
        self.current_generation = generation

    def state(self) -> Sequence[Message]:
        """Return state messages."""
        if self.verbosity == 0:
            return []
        return [
            FloatMessage(
                topic=MutationMessageTopics.MUTATION_PROBABILITY,
                source=self.__class__.__name__,
                value=self.mutation_probability,
            ),
        ]