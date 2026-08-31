"""Evolutionary operators for mutation.

Various evolutionary operators for mutation in multiobjective optimization are defined here.
"""

import copy
import warnings
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
    TerminatorMessageTopics,
)
from desdeo.tools.patterns import Publisher, Subscriber


class BaseMutation(Subscriber):
    """A base class for mutation operators."""

    @abstractmethod
    def __init__(self, problem: Problem, verbosity: int, publisher: Publisher):
        """Initialize a mutation operator."""
        super().__init__(verbosity=verbosity, publisher=publisher)
        self.problem = problem
        self.variable_symbols = [var.symbol for var in problem.get_flattened_variables()]
        self.lower_bounds = [var.lowerbound for var in problem.get_flattened_variables()]
        self.upper_bounds = [var.upperbound for var in problem.get_flattened_variables()]
        self.variable_types = [var.variable_type for var in problem.get_flattened_variables()]
        self.variable_combination: VariableDomainTypeEnum = problem.variable_domain
        # Populated by `do`. Initialized here so that `state` can be called before the first
        # mutation, e.g. by a logger that reports the operator's state up front.
        self.offspring_original: pl.DataFrame | None = None
        self.parents: pl.DataFrame | None = None
        self.offspring: pl.DataFrame | None = None

    @property
    def is_discrete(self) -> list[bool]:
        """Whether each (flattened) variable is restricted to integer values.

        Returns:
            list[bool]: one flag per variable, in the order of `variable_symbols`.
        """
        return [var_type in (VariableTypeEnum.binary, VariableTypeEnum.integer) for var_type in self.variable_types]

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
                MutationMessageTopics.PARENTS,
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
        verbosity: int,
        publisher: Publisher,
        mutation_probability: float | None = None,
        distribution_index: float = 20,
    ):
        """Initialize a bounded polynomial mutation operator.

        Args:
            problem (Problem): The problem object.
            seed (int): The seed for the random number generator.
            verbosity (int): The verbosity level of the operator. See the `provided_topics` attribute to see what
                messages are provided at each verbosity level. Recommended value is 1.
            publisher (Publisher): The publisher to which the operator will send messages.
            mutation_probability (float | None, optional): The probability of mutation. Defaults to None.
            distribution_index (float, optional): The distribution index for polynomial mutation. Defaults to 20.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        if self.variable_combination != VariableDomainTypeEnum.continuous:
            raise ValueError("This mutation operator only works with continuous variables.")
        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.lower_bounds)
        else:
            self.mutation_probability = mutation_probability
        self.distribution_index = distribution_index
        self.rng = np.random.default_rng(seed)
        self.seed = seed

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
        # Note: `to_numpy` hands back an F-contiguous array. Every `pl.from_numpy` in this module
        # therefore states `orient="row"`: for a square population (as many individuals as
        # variables) polars cannot infer the orientation from the shape, and would read such an
        # array column-wise, transposing the population.
        offspring = offsprings.to_numpy(writable=True)
        min_val = np.ones_like(offspring) * self.lower_bounds
        max_val = np.ones_like(offspring) * self.upper_bounds
        k = self.rng.random(size=offspring.shape)
        miu = self.rng.random(size=offspring.shape)
        # A fixed variable has a single feasible value, and scaling by the width of an empty
        # interval would divide by zero. The resulting nan would survive the clipping below,
        # because every comparison against nan is False, so leave those genes alone instead.
        mutatable = np.logical_and(k <= self.mutation_probability, max_val > min_val)
        temp = np.logical_and(mutatable, (miu < 0.5))  # noqa: PLR2004
        # The polynomial mutation formula can still raise negative scaled values to fractional
        # powers; the offspring are clipped to the bounds afterwards, so the intermediate inf is
        # discarded. Silence the resulting benign numpy warnings.
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            offspring_scaled = (offspring - min_val) / (max_val - min_val)
            offspring[temp] = offspring[temp] + (
                (max_val[temp] - min_val[temp])
                * (
                    (
                        2 * miu[temp]
                        + (1 - 2 * miu[temp]) * (1 - offspring_scaled[temp]) ** (self.distribution_index + 1)
                    )
                    ** (1 / (self.distribution_index + 1))
                    - 1
                )
            )
            temp = np.logical_and(mutatable, (miu >= 0.5))  # noqa: PLR2004
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
        self.offspring = pl.from_numpy(offspring, schema=self.variable_symbols, orient="row")
        self.notify()
        return self.offspring

    def update(self, *_, **__):
        """Do nothing. This is just the basic polynomial mutation operator."""

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        if self.offspring_original is None or self.parents is None or self.offspring is None:
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
                MutationMessageTopics.PARENTS,
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
        verbosity: int,
        publisher: Publisher,
        mutation_probability: float | None = None,
    ):
        """Initialize a binary flip mutation operator.

        Args:
            problem (Problem): The problem object.
            seed (int): The seed for the random number generator.
            mutation_probability (float | None, optional): The probability of mutation. If None,
                the probability will be set to be 1/n, where n is the number of decision variables
                in the problem. Defaults to None.
            verbosity (int): The verbosity level of the operator. See the `provided_topics` attribute to see what
                messages are provided at each verbosity level. Recommended value is 1.
            publisher (Publisher): The publisher to which the operator will send messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)

        if self.variable_combination != VariableDomainTypeEnum.binary:
            raise ValueError("This mutation operator only works with binary variables.")
        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.variable_symbols)
        else:
            self.mutation_probability = mutation_probability

        self.rng = np.random.default_rng(seed)
        self.seed = seed

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
        offspring = offsprings.to_numpy(writable=True).astype(dtype=np.bool)

        # create a boolean mask based on the mutation probability
        flip_mask = self.rng.random(offspring.shape) < self.mutation_probability

        # using XOR (^), flip the bits in the offspring when the mask is True
        # otherwise leave the bit's value as it is
        offspring = offspring ^ flip_mask

        self.offspring = (
            pl.from_numpy(offspring, schema=self.variable_symbols, orient="row").select(pl.all()).cast(pl.Float64)
        )
        self.notify()

        return self.offspring

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        if self.offspring_original is None or self.parents is None or self.offspring is None:
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
                MutationMessageTopics.PARENTS,
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
        verbosity: int,
        publisher: Publisher,
        mutation_probability: float | None = None,
    ):
        """Initialize a random integer mutation operator.

        Args:
            problem (Problem): The problem object.
            seed (int): The seed for the random number generator.
            mutation_probability (float | None, optional): The probability of mutation. If None,
                the probability will be set to be 1/n, where n is the number of decision variables
                in the problem. Defaults to None.
            verbosity (int): The verbosity level of the operator. See the `provided_topics` attribute to see what
                messages are provided at each verbosity level. Recommended value is 1.
            publisher (Publisher): The publisher to which the operator will send messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)

        if self.variable_combination != VariableDomainTypeEnum.integer:
            raise ValueError("This mutation operator only works with integer variables.")
        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.variable_symbols)
        else:
            self.mutation_probability = mutation_probability

        self.rng = np.random.default_rng(seed)
        self.seed = seed

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

        population = offsprings.to_numpy(writable=True).astype(int)

        # create a boolean mask based on the mutation probability
        mutation_mask = self.rng.random(population.shape) < self.mutation_probability

        mutated = np.where(
            mutation_mask,
            self.rng.integers(self.lower_bounds, self.upper_bounds, size=population.shape, dtype=int, endpoint=True),
            population,
        )

        self.offspring = (
            pl.from_numpy(mutated, schema=self.variable_symbols, orient="row").select(pl.all()).cast(pl.Float64)
        )
        self.notify()

        return self.offspring

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        if self.offspring_original is None or self.parents is None or self.offspring is None:
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
                MutationMessageTopics.PARENTS,
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
        verbosity: int,
        publisher: Publisher,
        mutation_probability: float | None = None,
    ):
        """Initialize a random mixed_integer mutation operator.

        Args:
            problem (Problem): The problem object.
            seed (int): The seed for the random number generator.
            mutation_probability (float | None, optional): The probability of mutation. If None,
                the probability will be set to be 1/n, where n is the number of decision variables
                in the problem. Defaults to None.
            verbosity (int): The verbosity level of the operator. See the `provided_topics` attribute to see what
                messages are provided at each verbosity level. Recommended value is 1.
            publisher (Publisher): The publisher to which the operator will send messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)

        if mutation_probability is None:
            self.mutation_probability = 1 / len(self.variable_symbols)
        else:
            self.mutation_probability = mutation_probability

        self.rng = np.random.default_rng(seed)
        self.seed = seed

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

        population = offsprings.to_numpy(writable=True).astype(float)

        # create a boolean mask based on the mutation probability
        mutation_mask = self.rng.random(population.shape) < self.mutation_probability

        mutation_pool = np.array(
            [
                self.rng.integers(low=int(lower), high=int(upper), size=population.shape[0], endpoint=True).astype(
                    dtype=float
                )
                if discrete
                else self.rng.uniform(low=lower, high=upper, size=population.shape[0]).astype(dtype=float)
                for lower, upper, discrete in zip(self.lower_bounds, self.upper_bounds, self.is_discrete, strict=True)
            ]
        ).T

        mutated = np.where(
            mutation_mask,
            # self.rng.integers(self.lower_bounds, self.upper_bounds, size=population.shape, dtype=int, endpoint=True),
            mutation_pool,
            population,
        )

        self.offspring = (
            pl.from_numpy(mutated, schema=self.variable_symbols, orient="row").select(pl.all()).cast(pl.Float64)
        )
        self.notify()

        return self.offspring

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        if self.offspring_original is None or self.parents is None or self.offspring is None:
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


class MPTMutation(BaseMutation):
    """Makinen, Periaux and Toivanen (MTP) mutation.

    Applies small mutations to mixed-integer variables using a mutation exponent strategy.
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
                MutationMessageTopics.PARENTS,
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
        verbosity: int,
        publisher: Publisher,
        mutation_probability: float | None = None,
        mutation_exponent: float = 2.0,
    ):
        """Initialize a small mutation operator.

        Args:
            problem (Problem): Optimization problem.
            seed (int): RNG seed.
            mutation_probability (float | None): Probability of mutation per gene.
            mutation_exponent (float): Controls strength of small mutation (larger means smaller mutations).
            verbosity (int): The verbosity level of the operator. See the `provided_topics` attribute to see what
                messages are provided at each verbosity level. Recommended value is 1.
            publisher (Publisher): The publisher to which the operator will send messages.
                publisher must be passed. See the Subscriber class for more information.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.mutation_exponent = mutation_exponent
        self.mutation_probability = (
            1 / len(self.variable_symbols) if mutation_probability is None else mutation_probability
        )

    def _mutate_value(self, x, lower_bound, upper_bound):
        """Apply small mutation to a single float value using mutation exponent."""
        if upper_bound == lower_bound:
            # A fixed variable has a single feasible value; scaling by the width would divide by zero.
            return lower_bound
        t = (x - lower_bound) / (upper_bound - lower_bound)
        rnd = self.rng.uniform(0, 1)

        if rnd < t:
            tm = t - t * ((t - rnd) / t) ** self.mutation_exponent
        elif rnd > t:
            tm = t + (1 - t) * ((rnd - t) / (1 - t)) ** self.mutation_exponent
        else:
            tm = t

        return (1 - tm) * lower_bound + tm * upper_bound

    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Perform the MPT mutation operation.

        Args:
            offsprings (pl.DataFrame): the offspring population to mutate.
            parents (pl.DataFrame): the parent population from which the offspring
                was generated (via crossover). Not used in the mutation operator.

        Returns:
            pl.DataFrame: the offspring resulting from the mutation.
        """
        self.offspring_original = copy.copy(offsprings)
        self.parents = parents

        population = offsprings.to_numpy(writable=True).astype(float)

        bounds = list(zip(self.lower_bounds, self.upper_bounds, self.is_discrete, strict=True))
        for i in range(population.shape[0]):
            for j, (lower_bound, upper_bound, discrete) in enumerate(bounds):
                if self.rng.random() < self.mutation_probability:
                    mutated = self._mutate_value(population[i, j], lower_bound, upper_bound)
                    # Round after float mutation to keep integer domain. `np.round` rather than
                    # `round`, which raises on the NaN some crossover operators produce.
                    population[i, j] = np.round(mutated) if discrete else mutated

        self.offspring = (
            pl.from_numpy(population, schema=self.variable_symbols, orient="row").select(pl.all()).cast(pl.Float64)
        )
        self.notify()
        return self.offspring

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        if self.offspring_original is None or self.parents is None or self.offspring is None:
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
    """Non-uniform mutation operator.

    The mutation strength decays over generations.

    The decay is driven by how far the run has progressed towards its budget. The budget is
    taken from the terminator's messages, so the operator stays in step with the terminator
    even when the number of generations is not known in advance (for example when the run is
    terminated by a maximum number of function evaluations). A budget passed explicitly via
    `max_generations` takes precedence over the messages.
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
                MutationMessageTopics.PARENTS,
                MutationMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics that the mutation operator is interested in."""
        return [
            TerminatorMessageTopics.GENERATION,
            TerminatorMessageTopics.MAX_GENERATIONS,
            TerminatorMessageTopics.EVALUATION,
            TerminatorMessageTopics.MAX_EVALUATIONS,
        ]

    def __init__(
        self,
        *,
        problem: Problem,
        seed: int,
        verbosity: int,
        publisher: Publisher,
        max_generations: int | None = None,
        mutation_probability: float | None = None,
        b: float = 5.0,  # decay parameter
    ):
        """Initialize a Non-uniform mutation operator.

        Args:
            problem (Problem): The optimization problem definition.
            seed (int): Random number generator seed for reproducibility.
            verbosity (int): The verbosity level of the operator. See the `provided_topics` attribute to see what
                messages are provided at each verbosity level. Recommended value is 1.
            publisher (Publisher): The publisher to which the operator will send messages.
            max_generations (int | None): Maximum number of generations in the evolutionary run, used to scale
                mutation decay. Defaults to None, in which case the budget reported by the terminator is used,
                falling back to the number of function evaluations if the terminator does not bound the number
                of generations. Prefer leaving this as None: a value that disagrees with the terminator makes the
                decay schedule finish too early or not at all.
            mutation_probability (float | None): Probability of mutating each
                gene. If None, defaults to 1 / number of variables.
            b (float): Non-uniform mutation decay parameter. Higher values cause
                faster reduction in mutation strength over generations.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        if max_generations is not None and max_generations <= 0:
            raise ValueError(f"max_generations must be a positive integer, got {max_generations}.")
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.b = b
        self.current_generation = 0
        self.max_generations = max_generations
        self.current_evaluations = 0
        self.max_evaluations: int | None = None
        # Budget reported by the terminator, used when max_generations was not given explicitly.
        self.reported_max_generations: int | None = None
        self._warned_past_budget = False
        self.mutation_probability = (
            1 / len(self.variable_symbols) if mutation_probability is None else mutation_probability
        )

    @property
    def decay_progress(self) -> float:
        """The fraction of the run that has elapsed, in [0, 1].

        A value of 0 means full mutation strength and a value of 1 means no mutation at all. The
        ratio must never leave [0, 1]: a negative `1 - progress` would be raised to the power `b`
        below, which yields a complex number for a fractional `b` and overflows the float range
        for an integral one.

        Returns:
            float: the elapsed fraction of the run, clamped to [0, 1]. Zero if no budget is known.
        """
        max_generations = self.max_generations if self.max_generations is not None else self.reported_max_generations

        if max_generations is not None and max_generations > 0:
            progress = self.current_generation / max_generations
            if progress > 1.0 and self.max_generations is not None and not self._warned_past_budget:
                self._warned_past_budget = True
                warnings.warn(
                    f"{self.__class__.__name__} was given max_generations={self.max_generations}, but the run has "
                    f"reached generation {self.current_generation}. The mutation strength has already decayed to "
                    "zero and stays there for the rest of the run. Leave max_generations as None to let the "
                    "operator follow the terminator's budget instead.",
                    stacklevel=2,
                )
            return min(progress, 1.0)

        if self.max_evaluations is not None and self.max_evaluations > 0:
            return min(self.current_evaluations / self.max_evaluations, 1.0)

        # Nothing bounds the run (e.g. a time based terminator), so keep the mutation at full strength.
        return 0.0

    def _mutate_value(self, x: float, lower_bound: float, upper_bound: float, mutation_threshold: float = 0.5) -> float:
        """Apply non-uniform mutation to a single float value.

        Args:
            x (float): The current value of the gene to be mutated.
            lower_bound (float): The lower bound of the gene.
            upper_bound (float): The upper bound of the gene.
            mutation_threshold (float): The mutation threshold. Defaults to 0.5.

        Returns:
            float: The mutated gene value, clipped within the bounds [l, u].
        """
        r = self.rng.uniform(0, 1)  # Random number to choose direction
        b = self.b

        u_rand = self.rng.uniform(0, 1)  # Random number for mutation strength
        tau = (1 - self.decay_progress) ** b

        if r <= mutation_threshold:
            y = upper_bound - x
            delta = y * (1 - u_rand**tau)
            xm = x + delta
        else:
            y = x - lower_bound
            delta = y * (1 - u_rand**tau)
            xm = x - delta

        return np.clip(xm, lower_bound, upper_bound)

    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Perform non-uniform mutation.

        Args:
            offsprings (pl.DataFrame): The current offspring population to
                mutate. Each row corresponds to one individual.
            parents (pl.DataFrame): The parent population (not used in mutation but passed for interface consistency).

        Returns:
            pl.DataFrame: A new offspring population with mutated values applied. Returned as a Polars DataFrame.
        """
        self.offspring_original = copy.copy(offsprings)
        self.parents = parents

        population = offsprings.to_numpy(writable=True).astype(float)

        bounds = list(zip(self.lower_bounds, self.upper_bounds, self.is_discrete, strict=True))
        for i in range(population.shape[0]):
            for j, (lower_bound, upper_bound, discrete) in enumerate(bounds):
                if self.rng.random() < self.mutation_probability:
                    mutated = self._mutate_value(population[i, j], lower_bound, upper_bound)
                    # Round to keep the integer domain. `np.round` rather than `round`, which
                    # raises on the NaN some crossover operators produce.
                    population[i, j] = np.round(mutated) if discrete else mutated

        self.offspring = pl.from_numpy(population, schema=self.variable_symbols, orient="row").cast(pl.Float64)
        self.notify()

        return self.offspring

    def update(self, message: Message):
        """Track the progress of the run (used to reduce mutation strength over time)."""
        if not isinstance(message.topic, TerminatorMessageTopics):
            return
        if not isinstance(message.value, int):
            return
        match message.topic:
            case TerminatorMessageTopics.GENERATION:
                self.current_generation = message.value
            case TerminatorMessageTopics.MAX_GENERATIONS:
                self.reported_max_generations = message.value
            case TerminatorMessageTopics.EVALUATION:
                self.current_evaluations = message.value
            case TerminatorMessageTopics.MAX_EVALUATIONS:
                self.max_evaluations = message.value
            case _:
                return

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        if self.offspring_original is None or self.parents is None or self.offspring is None:
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


class SelfAdaptiveGaussianMutation(BaseMutation):
    """Self-adaptive Gaussian mutation for real-coded evolutionary algorithms.

    Evolves both solution vector and mutation step sizes (strategy parameters).
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
                MutationMessageTopics.PARENTS,
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
        verbosity: int,
        publisher: Publisher,
        mutation_probability: float | None = None,
    ):
        """Initialize the self-adaptive Gaussian mutation operator.

        Args:
            problem (Problem): The optimization problem definition, including variable bounds and types.
            seed (int): Seed for the random number generator to ensure reproducibility.
            mutation_probability (float | None): Probability of mutating each gene.
                If None, it defaults to 1 divided by the number of variables.
            verbosity (int): The verbosity level of the operator. See the `provided_topics` attribute to see what
                messages are provided at each verbosity level. Recommended value is 1.
            publisher (Publisher): The publisher to which the operator will send messages.

        Attributes:
            rng (Generator): NumPy random number generator initialized with the given seed.
            seed (int): The seed used for reproducibility.
            num_vars (int): Number of variables in the problem.
            mutation_probability (float): Probability of mutating each gene.
            tau_prime (float): Global learning rate, used in step size adaptation.
            tau (float): Local learning rate, used in step size adaptation.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher)

        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.num_vars = len(self.variable_symbols)

        self.mutation_probability = 1 / self.num_vars if mutation_probability is None else mutation_probability

        self.tau_prime = 1 / np.sqrt(2 * self.num_vars)
        self.tau = 1 / np.sqrt(2 * np.sqrt(self.num_vars))

        # Per-gene step sizes, adapted on each call and carried over across generations.
        self.step_sizes: np.ndarray | None = None

    def do(
        self,
        offsprings: pl.DataFrame,
        parents: pl.DataFrame,
    ) -> pl.DataFrame:
        """Apply self-adaptive Gaussian mutation.

        The per-gene step sizes are adapted on every call and stored in `self.step_sizes`,
        so that the adaptation carries over across generations.

        Args:
            offsprings (pl.DataFrame): Current offspring population.
            parents (pl.DataFrame): Parent population.

        Returns:
            pl.DataFrame: The mutated offspring population.
        """
        self.offspring_original = offsprings
        self.parents = parents

        offspring_array = offsprings.to_numpy(writable=True).astype(float)

        if self.step_sizes is None or self.step_sizes.shape != offspring_array.shape:
            self.step_sizes = np.full_like(offspring_array, fill_value=0.1)

        new_offspring, self.step_sizes = self._mutation(offspring_array, self.step_sizes)

        mutated_df = pl.from_numpy(new_offspring, schema=self.variable_symbols, orient="row").cast(pl.Float64)
        self.offspring = mutated_df
        self.notify()

        return mutated_df

    def _mutation(self, variables: np.ndarray, eta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Perform the self-adaptive mutation.

        Args:
            variables (np.ndarray): Current offspring population as a NumPy array.
            eta (np.ndarray): Current step sizes for mutation.

        Returns:
            tuple[np.ndarray, np.ndarray]: Mutated population and updated step sizes.
        """
        new_variables = variables.copy()
        new_eta = eta.copy()

        for i in range(variables.shape[0]):
            common_noise = self.rng.normal()
            for j in range(variables.shape[1]):
                if self.rng.random() < self.mutation_probability:
                    rnd_number = self.rng.normal()  # random number in the interval [0, 1]
                    new_eta[i, j] *= np.exp(self.tau_prime * common_noise + self.tau * rnd_number)
                    new_variables[i, j] += new_eta[i, j] * rnd_number

        # Gaussian noise is unbounded, so keep the offspring inside the feasible box. Without this
        # the operator relies on a repair function that the templates only apply afterwards.
        new_variables = np.clip(new_variables, self.lower_bounds, self.upper_bounds)

        return new_variables, new_eta

    def update(self, *_, **__):
        """Do nothing."""

    def state(self) -> Sequence[Message]:
        """Return the state of the mutation operator."""
        if self.offspring_original is None or self.parents is None or self.offspring is None:
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


class PowerMutation(BaseMutation):
    """Implements the Power Mutation (PM) operator for real and integer variables."""

    @property
    def provided_topics(self) -> dict[int, Sequence[MutationMessageTopics]]:
        """The message topics provided by the mutation operator."""
        return {
            0: [],
            1: [MutationMessageTopics.MUTATION_PROBABILITY],
            2: [
                MutationMessageTopics.MUTATION_PROBABILITY,
                MutationMessageTopics.OFFSPRING_ORIGINAL,
                MutationMessageTopics.PARENTS,
                MutationMessageTopics.OFFSPRINGS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics that the mutation operator listens to (none in this case)."""
        return []

    def __init__(
        self,
        *,
        problem: Problem,
        seed: int,
        verbosity: int,
        publisher: Publisher,
        p: float = 1.5,
        mutation_probability: float | None = None,
    ):
        """Initialize the PowerMutation operator.

        Args:
            problem (Problem): The problem definition containing variable bounds and types.
            seed (int): Random seed for reproducibility.
            p (float): Power distribution parameter. Controls the perturbation magnitude. Default is 1.5.
            mutation_probability (float | None): Per-variable mutation probability. Defaults to 1/n.
            verbosity (int): The verbosity level of the operator. See the `provided_topics` attribute to see what
                messages are provided at each verbosity level. Recommended value is 1.
            publisher (Publisher): The publisher to which the operator will send messages.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.p = p
        self.mutation_probability = (
            mutation_probability if mutation_probability is not None else 1 / len(self.variable_symbols)
        )
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Apply Power Mutation to the given offspring population.

        Args:
            offsprings (pl.DataFrame): The offspring population to mutate.
            parents (pl.DataFrame): The parent population

        Returns:
            pl.DataFrame: Mutated offspring population.
        """
        self.offspring_original = copy.copy(offsprings)
        self.parents = parents

        if self.mutation_probability == 0.0:
            self.offspring = offsprings.clone()
            self.notify()
            return self.offspring

        population = offsprings.to_numpy(writable=True).astype(float)
        mutation_mask = self.rng.random(population.shape) < self.mutation_probability
        mutated = population.copy()

        bounds = zip(self.lower_bounds, self.upper_bounds, self.is_discrete, strict=True)
        for i, (lower_bound, upper_bound, discrete) in enumerate(bounds):
            if upper_bound == lower_bound:
                # A fixed variable has a single feasible value, and scaling by the width of an
                # empty interval would divide by zero. Leave the column as it is.
                continue
            x_i = population[:, i]

            u_i = self.rng.random(len(x_i))  # uniform random number
            s_i = u_i ** (1 / self.p)  # random number that follows the power distribution

            r_i = self.rng.random(len(x_i))  # another uniform random number
            direction = ((x_i - lower_bound) / (upper_bound - lower_bound)) < r_i  # used as condition

            xi_mutated = np.where(direction, x_i - s_i * (x_i - lower_bound), x_i + s_i * (upper_bound - x_i))
            if discrete:
                # Round after float mutation to keep the integer domain.
                xi_mutated = np.round(xi_mutated)

            # Apply mutation based on mask
            mutated[:, i] = np.where(mutation_mask[:, i], xi_mutated, x_i)

        # Convert back to DataFrame
        self.offspring = (
            pl.from_numpy(mutated, schema=self.variable_symbols, orient="row").select(pl.all()).cast(pl.Float64)
        )
        self.notify()

        return self.offspring

    def update(self, *_, **__):
        """No update logic needed."""

    def state(self) -> Sequence[Message]:
        """Return mutation-related state messages based on verbosity level.

        Returns:
            List of messages reporting mutation probability, input, and output (at higher verbosity).
        """
        if self.offspring_original is None or self.parents is None or self.offspring is None:
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

        # Verbosity == 2
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
