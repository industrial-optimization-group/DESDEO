"""The base class for selection operators.

This whole file should be rewritten. Everything is a mess. Moreover, the selectors do not yet take seeds as input for reproducibility.
TODO:@light-weaver
"""

import warnings
from abc import abstractmethod
from collections.abc import Sequence
from enum import Enum
from itertools import combinations
from typing import Literal, TypedDict, TypeVar

import numpy as np
import polars as pl
from scipy.special import comb
from scipy.stats.qmc import LatinHypercube

from desdeo.problem import Problem
from desdeo.tools import get_corrected_ideal_and_nadir
from desdeo.tools.message import (
    Array2DMessage,
    DictMessage,
    Message,
    PolarsDataFrameMessage,
    SelectorMessageTopics,
    TerminatorMessageTopics,
)
from desdeo.tools.non_dominated_sorting import fast_non_dominated_sort
from desdeo.tools.patterns import Subscriber, Publisher

SolutionType = TypeVar("SolutionType", list, pl.DataFrame)


class BaseSelector(Subscriber):
    """A base class for selection operators."""

    def __init__(self, problem: Problem, verbosity: int, publisher: Publisher):
        """Initialize a selection operator."""
        super().__init__(verbosity=verbosity, publisher=publisher)
        self.problem = problem
        self.variable_symbols = [x.symbol for x in problem.get_flattened_variables()]
        self.objective_symbols = [x.symbol for x in problem.objectives]

        if problem.scalarization_funcs is None:
            self.target_symbols = [f"{x.symbol}_min" for x in problem.objectives]
            try:
                ideal, nadir = get_corrected_ideal_and_nadir(problem)
                self.ideal = np.array([ideal[x.symbol] for x in problem.objectives])
                self.nadir = np.array([nadir[x.symbol] for x in problem.objectives]) if nadir is not None else None
            except ValueError:  # in case the ideal and nadir are not provided
                self.ideal = None
                self.nadir = None
        else:
            self.target_symbols = [x.symbol for x in problem.scalarization_funcs if x.symbol is not None]
            self.ideal: np.ndarray | None = None
            self.nadir: np.ndarray | None = None
        if problem.constraints is None:
            self.constraints_symbols = None
        else:
            self.constraints_symbols = [x.symbol for x in problem.constraints]
        self.num_dims = len(self.target_symbols)

    @abstractmethod
    def do(
        self,
        parents: tuple[SolutionType, pl.DataFrame],
        offsprings: tuple[SolutionType, pl.DataFrame],
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Perform the selection operation.

        Args:
            parents (tuple[SolutionType, pl.DataFrame]): the decision variables as the first element.
                The second element is the objective values, targets, and constraint violations.
            offsprings (tuple[SolutionType, pl.DataFrame]): the decision variables as the first element.
                The second element is the objective values, targets, and constraint violations.

        Returns:
            tuple[SolutionType, pl.DataFrame]: The selected decision variables and their objective values,
                targets, and constraint violations.
        """


class ReferenceVectorOptions(TypedDict, total=False):
    """The options for the reference vector based selection operators."""

    adaptation_frequency: int
    """Number of generations between reference vector adaptation. If set to 0, no adaptation occurs. Defaults to 100.
    Only used if `interactive_adaptation` is set to "none"."""
    creation_type: Literal["simplex", "s_energy"]
    """The method for creating reference vectors. Defaults to "simplex".
    Currently only "simplex" is implemented. Future versions will include "s_energy".

    If set to "simplex", the reference vectors are created using the simplex lattice design method.
    This method is generates distributions with specific numbers of reference vectors.
    Check: https://www.itl.nist.gov/div898/handbook/pri/section5/pri542.htm for more information.

    If set to "s_energy", the reference vectors are created using the Riesz s-energy criterion. This method is used to
    distribute an arbitrary number of reference vectors in the objective space while minimizing the s-energy.
    Currently not implemented.
    """
    vector_type: Literal["spherical", "planar"]
    """The method for normalizing the reference vectors. Defaults to "spherical"."""
    lattice_resolution: int
    """Number of divisions along an axis when creating the simplex lattice. This is not required/used for the "s_energy"
    method. If not specified, the lattice resolution is calculated based on the `number_of_vectors`.
    """
    number_of_vectors: int
    """Number of reference vectors to be created. If "simplex" is selected as the `creation_type`, then the closest
    `lattice_resolution` is calculated based on this value. If "s_energy" is selected, then this value is used directly.
    Note that if neither `lattice_resolution` nor `number_of_vectors` is specified, the number of vectors defaults to
    500.
    """
    interactive_adaptation: Literal[
        "preferred_solutions", "non_preferred_solutions", "preferred_ranges", "reference_point", "none"
    ]
    """The method for adapting reference vectors based on the Decision maker's preference information.
    Defaults to "none".
    """
    adaptation_distance: float
    """Distance parameter for the interactive adaptation methods. Defaults to 0.2."""
    reference_point: dict[str, float]
    """The reference point for interactive adaptation."""
    preferred_solutions: dict[str, list[float]]
    """The preferred solutions for interactive adaptation."""
    non_preferred_solutions: dict[str, list[float]]
    """The non-preferred solutions for interactive adaptation."""
    preferred_ranges: dict[str, list[float]]
    """The preferred ranges for interactive adaptation."""


class BaseDecompositionSelector(BaseSelector):
    """Base class for decomposition based selection operators."""

    def __init__(
        self, problem: Problem, reference_vector_options: ReferenceVectorOptions, verbosity: int, publisher: Publisher
    ):
        super().__init__(problem, verbosity=verbosity, publisher=publisher)
        self.reference_vector_options = reference_vector_options
        self.reference_vectors: np.ndarray
        self.reference_vectors_initial: np.ndarray

        # Set default values
        if "creation_type" not in self.reference_vector_options:
            self.reference_vector_options["creation_type"] = "simplex"
        if "vector_type" not in self.reference_vector_options:
            self.reference_vector_options["vector_type"] = "spherical"
        if "adaptation_frequency" not in self.reference_vector_options:
            self.reference_vector_options["adaptation_frequency"] = 100
        if self.reference_vector_options["creation_type"] == "simplex":
            self._create_simplex()
        elif self.reference_vector_options["creation_type"] == "s_energy":
            raise NotImplementedError("Riesz s-energy criterion is not yet implemented.")

        if "interactive_adaptation" not in self.reference_vector_options:
            self.reference_vector_options["interactive_adaptation"] = "none"
        elif self.reference_vector_options["interactive_adaptation"] != "none":
            self.reference_vector_options["adaptation_frequency"] = 0
        if "adaptation_distance" not in self.reference_vector_options:
            self.reference_vector_options["adaptation_distance"] = 0.2
        self._create_simplex()

        if self.reference_vector_options["interactive_adaptation"] == "reference_point":
            if "reference_point" not in self.reference_vector_options:
                raise ValueError("Reference point must be specified for interactive adaptation.")
            self.interactive_adapt_3(
                np.array([self.reference_vector_options["reference_point"][x] for x in self.target_symbols]),
                translation_param=self.reference_vector_options["adaptation_distance"],
            )
        elif self.reference_vector_options["interactive_adaptation"] == "preferred_solutions":
            if "preferred_solutions" not in self.reference_vector_options:
                raise ValueError("Preferred solutions must be specified for interactive adaptation.")
            self.interactive_adapt_1(
                np.array([self.reference_vector_options["preferred_solutions"][x] for x in self.target_symbols]).T,
                translation_param=self.reference_vector_options["adaptation_distance"],
            )
        elif self.reference_vector_options["interactive_adaptation"] == "non_preferred_solutions":
            if "non_preferred_solutions" not in self.reference_vector_options:
                raise ValueError("Non-preferred solutions must be specified for interactive adaptation.")
            self.interactive_adapt_2(
                np.array([self.reference_vector_options["non_preferred_solutions"][x] for x in self.target_symbols]).T,
                predefined_distance=self.reference_vector_options["adaptation_distance"],
            )
        elif self.reference_vector_options["interactive_adaptation"] == "preferred_ranges":
            if "preferred_ranges" not in self.reference_vector_options:
                raise ValueError("Preferred ranges must be specified for interactive adaptation.")
            self.interactive_adapt_4(
                np.array([self.reference_vector_options["preferred_ranges"][x] for x in self.target_symbols]).T,
            )

    def _create_simplex(self):
        """Create the reference vectors using simplex lattice design."""

        def approx_lattice_resolution(number_of_vectors: int, num_dims: int) -> int:
            """Approximate the lattice resolution based on the number of vectors."""
            temp_lattice_resolution = 0
            while True:
                temp_lattice_resolution += 1
                temp_number_of_vectors = comb(
                    temp_lattice_resolution + num_dims - 1,
                    num_dims - 1,
                    exact=True,
                )
                if temp_number_of_vectors > number_of_vectors:
                    break
            return temp_lattice_resolution - 1

        if "lattice_resolution" in self.reference_vector_options:
            lattice_resolution = self.reference_vector_options["lattice_resolution"]
        elif "number_of_vectors" in self.reference_vector_options:
            lattice_resolution = approx_lattice_resolution(
                self.reference_vector_options["number_of_vectors"], num_dims=self.num_dims
            )
        else:
            lattice_resolution = approx_lattice_resolution(500, num_dims=self.num_dims)

        number_of_vectors: int = comb(
            lattice_resolution + self.num_dims - 1,
            self.num_dims - 1,
            exact=True,
        )

        self.reference_vector_options["number_of_vectors"] = number_of_vectors
        self.reference_vector_options["lattice_resolution"] = lattice_resolution

        temp1 = range(1, self.num_dims + lattice_resolution)
        temp1 = np.array(list(combinations(temp1, self.num_dims - 1)))
        temp2 = np.array([range(self.num_dims - 1)] * number_of_vectors)
        temp = temp1 - temp2 - 1
        weight = np.zeros((number_of_vectors, self.num_dims), dtype=int)
        weight[:, 0] = temp[:, 0]
        for i in range(1, self.num_dims - 1):
            weight[:, i] = temp[:, i] - temp[:, i - 1]
        weight[:, -1] = lattice_resolution - temp[:, -1]
        self.reference_vectors = weight / lattice_resolution
        self.reference_vectors_initial = np.copy(self.reference_vectors)
        self._normalize_rvs()

    def _normalize_rvs(self):
        """Normalize the reference vectors to a unit hypersphere."""
        if self.reference_vector_options["vector_type"] == "spherical":
            norm = np.linalg.norm(self.reference_vectors, axis=1).reshape(-1, 1)
            norm[norm == 0] = np.finfo(float).eps
        elif self.reference_vector_options["vector_type"] == "planar":
            norm = np.sum(self.reference_vectors, axis=1).reshape(-1, 1)
        else:
            raise ValueError("Invalid vector type. Must be either 'spherical' or 'planar'.")
        self.reference_vectors = np.divide(self.reference_vectors, norm)

    def interactive_adapt_1(self, z: np.ndarray, translation_param: float) -> None:
        """Adapt reference vectors using the information about prefererred solution(s) selected by the Decision maker.

        Args:
            z (np.ndarray): Preferred solution(s).
            translation_param (float): Parameter determining how close the reference vectors are to the central vector
            **v** defined by using the selected solution(s) z.
        """
        if z.shape[0] == 1:
            # single preferred solution
            # calculate new reference vectors
            self.reference_vectors = translation_param * self.reference_vectors_initial + ((1 - translation_param) * z)

        else:
            # multiple preferred solutions
            # calculate new reference vectors for each preferred solution
            values = [translation_param * self.reference_vectors_initial + ((1 - translation_param) * z_i) for z_i in z]

            # combine arrays of reference vectors into a single array and update reference vectors
            self.reference_vectors = np.concatenate(values)

        self._normalize_rvs()
        self.add_edge_vectors()

    def interactive_adapt_2(self, z: np.ndarray, predefined_distance: float) -> None:
        """Adapt reference vectors by using the information about non-preferred solution(s) selected by the Decision maker.

        After the Decision maker has specified non-preferred solution(s), Euclidian distance between normalized solution
        vector(s) and each of the reference vectors are calculated. Those reference vectors that are **closer** than a
        predefined distance are either **removed** or **re-positioned** somewhere else.

        Note:
            At the moment, only the **removal** of reference vectors is supported. Repositioning of the reference
            vectors is **not** supported.

        Note:
            In case the Decision maker specifies multiple non-preferred solutions, the reference vector(s) for which the
            distance to **any** of the non-preferred solutions is less than predefined distance are removed.

        Note:
            Future developer should implement a way for a user to say: "Remove some percentage of
            objecive space/reference vectors" rather than giving a predefined distance value.

        Args:
            z (np.ndarray): Non-preferred solution(s).
            predefined_distance (float): The reference vectors that are closer than this distance are either removed or
            re-positioned somewhere else.
            Default value: 0.2
        """
        # calculate L1 norm of non-preferred solution(s)
        z = np.atleast_2d(z)
        norm = np.linalg.norm(z, ord=2, axis=1).reshape(np.shape(z)[0], 1)

        # non-preferred solutions normalized
        v_c = np.divide(z, norm)

        # distances from non-preferred solution(s) to each reference vector
        distances = np.array(
            [
                list(
                    map(
                        lambda solution: np.linalg.norm(solution - value, ord=2),
                        v_c,
                    )
                )
                for value in self.reference_vectors
            ]
        )

        # find out reference vectors that are not closer than threshold value to any non-preferred solution
        mask = [all(d >= predefined_distance) for d in distances]

        # set those reference vectors that met previous condition as new reference vectors, drop others
        self.reference_vectors = self.reference_vectors[mask]

        self._normalize_rvs()
        self.add_edge_vectors()

    def interactive_adapt_3(self, ref_point, translation_param):
        """Adapt reference vectors linearly towards a reference point. Then normalize.

        The details can be found in the following paper: Hakanen, Jussi &
        Chugh, Tinkle & Sindhya, Karthik & Jin, Yaochu & Miettinen, Kaisa.
        (2016). Connections of Reference Vectors and Different Types of
        Preference Information in Interactive Multiobjective Evolutionary
        Algorithms.

        Parameters
        ----------
        ref_point :

        translation_param :
            (Default value = 0.2)

        """
        self.reference_vectors = self.reference_vectors_initial * translation_param + (
            (1 - translation_param) * ref_point
        )
        self._normalize_rvs()
        self.add_edge_vectors()

    def interactive_adapt_4(self, preferred_ranges: np.ndarray) -> None:
        """Adapt reference vectors by using the information about the Decision maker's preferred range for each of the objective.

        Using these ranges, Latin hypercube sampling is applied to generate m number of samples between
        within these ranges, where m is the number of reference vectors. Normalized vectors constructed of these samples
        are then set as new reference vectors.

        Args:
            preferred_ranges (np.ndarray): Preferred lower and upper bound for each of the objective function values.
        """
        # bounds
        lower_limits = np.min(preferred_ranges, axis=0)
        upper_limits = np.max(preferred_ranges, axis=0)

        # generate samples using Latin hypercube sampling
        lhs = LatinHypercube(d=self.num_dims)
        w = lhs.random(n=self.reference_vectors_initial.shape[0])

        # scale between bounds
        w = w * (upper_limits - lower_limits) + lower_limits

        # set new reference vectors and normalize them
        self.reference_vectors = w
        self._normalize_rvs()
        self.add_edge_vectors()

    def add_edge_vectors(self):
        """Add edge vectors to the list of reference vectors.

        Used to cover the entire orthant when preference information is
        provided.

        """
        edge_vectors = np.eye(self.reference_vectors.shape[1])
        self.reference_vectors = np.vstack([self.reference_vectors, edge_vectors])
        self._normalize_rvs()


class ParameterAdaptationStrategy(Enum):
    """The parameter adaptation strategies for the RVEA selector."""

    GENERATION_BASED = 1  # Based on the current generation and the maximum generation.
    FUNCTION_EVALUATION_BASED = 2  # Based on the current function evaluation and the maximum function evaluation.
    OTHER = 3  # As of yet undefined strategies.


class RVEASelector(BaseDecompositionSelector):
    @property
    def provided_topics(self):
        return {
            0: [],
            1: [
                SelectorMessageTopics.STATE,
            ],
            2: [
                SelectorMessageTopics.REFERENCE_VECTORS,
                SelectorMessageTopics.STATE,
                SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
            ],
        }

    @property
    def interested_topics(self):
        return [
            TerminatorMessageTopics.GENERATION,
            TerminatorMessageTopics.MAX_GENERATIONS,
            TerminatorMessageTopics.EVALUATION,
            TerminatorMessageTopics.MAX_EVALUATIONS,
        ]

    def __init__(
        self,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        alpha: float = 2.0,
        parameter_adaptation_strategy: ParameterAdaptationStrategy = ParameterAdaptationStrategy.GENERATION_BASED,
        reference_vector_options: ReferenceVectorOptions | None = None,
    ):
        if not isinstance(parameter_adaptation_strategy, ParameterAdaptationStrategy):
            raise TypeError(f"Parameter adaptation strategy must be of Type {type(ParameterAdaptationStrategy)}")
        if parameter_adaptation_strategy == ParameterAdaptationStrategy.OTHER:
            raise ValueError("Other parameter adaptation strategies are not yet implemented.")

        if reference_vector_options is None:
            reference_vector_options = ReferenceVectorOptions(
                adaptation_frequency=100,
                creation_type="simplex",
                vector_type="spherical",
                number_of_vectors=500,
            )

        super().__init__(
            problem=problem, reference_vector_options=reference_vector_options, verbosity=verbosity, publisher=publisher
        )

        self.reference_vectors_gamma: np.ndarray
        self.numerator: float | None = None
        self.denominator: float | None = None
        self.alpha = alpha
        self.selected_individuals: list | pl.DataFrame
        self.selected_targets: pl.DataFrame
        self.selection: list[int]
        self.penalty = None
        self.parameter_adaptation_strategy = parameter_adaptation_strategy

    def do(
        self,
        parents: tuple[SolutionType, pl.DataFrame],
        offsprings: tuple[SolutionType, pl.DataFrame],
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Perform the selection operation.

        Args:
            parents (tuple[SolutionType, pl.DataFrame]): the decision variables as the first element.
                The second element is the objective values, targets, and constraint violations.
            offsprings (tuple[SolutionType, pl.DataFrame]): the decision variables as the first element.
                The second element is the objective values, targets, and constraint violations.

        Returns:
            tuple[SolutionType, pl.DataFrame]: The selected decision variables and their objective values,
                targets, and constraint violations.
        """
        if isinstance(parents[0], pl.DataFrame) and isinstance(offsprings[0], pl.DataFrame):
            solutions = parents[0].vstack(offsprings[0])
        elif isinstance(parents[0], list) and isinstance(offsprings[0], list):
            solutions = parents[0] + offsprings[0]
        else:
            raise TypeError("The decision variables must be either a list or a polars DataFrame, not both")
        if len(parents[0]) == 0:
            raise RuntimeError(
                "The parents population is empty. Cannot perform selection. This is a known unresolved issue."
            )
        alltargets = parents[1].vstack(offsprings[1])
        targets = alltargets[self.target_symbols].to_numpy()
        if self.constraints_symbols is None or len(self.constraints_symbols) == 0:
            constraints = None
        else:
            constraints = (
                parents[1][self.constraints_symbols].vstack(offsprings[1][self.constraints_symbols]).to_numpy()
            )

        if self.ideal is None:
            self.ideal = np.min(targets, axis=0)
        else:
            self.ideal = np.min(np.vstack((self.ideal, np.min(targets, axis=0))), axis=0)
        partial_penalty_factor = self._partial_penalty_factor()
        self._adapt()

        ref_vectors = self.adapted_reference_vectors
        # Normalization - There may be problems here
        translated_targets = targets - self.ideal
        targets_norm = np.linalg.norm(translated_targets, axis=1)
        # TODO check if you need the next line
        # TODO changing the order of the following few operations might be efficient
        targets_norm = np.repeat(targets_norm, len(translated_targets[0, :])).reshape(translated_targets.shape)
        # Convert zeros to eps to avoid divide by zero.
        # Has to be checked!
        targets_norm[targets_norm == 0] = np.finfo(float).eps
        normalized_targets = np.divide(translated_targets, targets_norm)  # Checked, works.
        cosine = np.dot(normalized_targets, np.transpose(ref_vectors))
        if cosine[np.where(cosine > 1)].size:
            cosine[np.where(cosine > 1)] = 1
        if cosine[np.where(cosine < 0)].size:
            cosine[np.where(cosine < 0)] = 0
        # Calculation of angles between reference vectors and solutions
        theta = np.arccos(cosine)
        # Reference vector assignment
        assigned_vectors = np.argmax(cosine, axis=1)
        selection = np.array([], dtype=int)
        # Selection
        # Convert zeros to eps to avoid divide by zero.
        # Has to be checked!
        ref_vectors[ref_vectors == 0] = np.finfo(float).eps
        for i in range(len(ref_vectors)):
            sub_population_index = np.atleast_1d(np.squeeze(np.where(assigned_vectors == i)))

            # Constraint check
            if len(sub_population_index) > 1 and constraints is not None:
                violation_values = constraints[sub_population_index]
                # violation_values = -violation_values
                violation_values = np.maximum(0, violation_values)
                # True if feasible
                feasible_bool = (violation_values == 0).all(axis=1)

                # Case when entire subpopulation is infeasible
                if not feasible_bool.any():
                    violation_values = violation_values.sum(axis=1)
                    sub_population_index = sub_population_index[np.where(violation_values == violation_values.min())]
                # Case when only some are infeasible
                else:
                    sub_population_index = sub_population_index[feasible_bool]

            sub_population_fitness = translated_targets[sub_population_index]
            # fast tracking singly selected individuals
            if len(sub_population_index) == 1:
                selx = sub_population_index
                if selection.shape[0] == 0:
                    selection = np.hstack((selection, np.transpose(selx[0])))
                else:
                    selection = np.vstack((selection, np.transpose(selx[0])))
            elif len(sub_population_index) > 1:
                # APD Calculation
                angles = theta[sub_population_index, i]
                angles = np.divide(angles, self.reference_vectors_gamma[i])  # This is correct.
                # You have done this calculation before. Check with fitness_norm
                # Remove this horrible line
                sub_pop_fitness_magnitude = np.sqrt(np.sum(np.power(sub_population_fitness, 2), axis=1))
                apd = np.multiply(
                    np.transpose(sub_pop_fitness_magnitude),
                    (1 + np.dot(partial_penalty_factor, angles)),
                )
                minidx = np.where(apd == np.nanmin(apd))
                if np.isnan(apd).all():
                    continue
                selx = sub_population_index[minidx]
                if selection.shape[0] == 0:
                    selection = np.hstack((selection, np.transpose(selx[0])))
                else:
                    selection = np.vstack((selection, np.transpose(selx[0])))

        self.selection = selection.tolist()
        self.selected_individuals = solutions[selection.flatten()]
        self.selected_targets = alltargets[selection.flatten()]
        self.notify()
        return self.selected_individuals, self.selected_targets

    def _partial_penalty_factor(self) -> float:
        """Calculate and return the partial penalty factor for APD calculation.

            This calculation does not include the angle related terms, hence the name.
            If the calculated penalty is outside [0, 1], it will round it up/down to 0/1

        Returns:
            float: The partial penalty factor
        """
        if self.numerator is None or self.denominator is None or self.denominator == 0:
            raise RuntimeError("Numerator and denominator must be set before calculating the partial penalty factor.")
        penalty = self.numerator / self.denominator
        penalty = float(np.clip(penalty, 0, 1))
        self.penalty = (penalty**self.alpha) * self.reference_vectors.shape[1]
        return self.penalty

    def update(self, message: Message) -> None:
        """Update the parameters of the RVEA APD calculation.

        Args:
            message (Message): The message to update the parameters. The message should be coming from the
                Terminator operator (via the Publisher).
        """
        if not isinstance(message.topic, TerminatorMessageTopics):
            return
        if not isinstance(message.value, int):
            return
        if self.parameter_adaptation_strategy == ParameterAdaptationStrategy.GENERATION_BASED:
            if message.topic == TerminatorMessageTopics.GENERATION:
                self.numerator = message.value
            if message.topic == TerminatorMessageTopics.MAX_GENERATIONS:
                self.denominator = message.value
        elif self.parameter_adaptation_strategy == ParameterAdaptationStrategy.FUNCTION_EVALUATION_BASED:
            if message.topic == TerminatorMessageTopics.EVALUATION:
                self.numerator = message.value
            if message.topic == TerminatorMessageTopics.MAX_EVALUATIONS:
                self.denominator = message.value
        return

    def state(self) -> Sequence[Message]:
        if self.verbosity == 0 or self.selection is None:
            return []
        if self.verbosity == 1:
            return [
                Array2DMessage(
                    topic=SelectorMessageTopics.REFERENCE_VECTORS,
                    value=self.reference_vectors.tolist(),
                    source=self.__class__.__name__,
                ),
                DictMessage(
                    topic=SelectorMessageTopics.STATE,
                    value={
                        "ideal": self.ideal,
                        "nadir": self.nadir,
                        "partial_penalty_factor": self._partial_penalty_factor(),
                    },
                    source=self.__class__.__name__,
                ),
            ]  # verbosity == 2
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
        state_verbose = [
            Array2DMessage(
                topic=SelectorMessageTopics.REFERENCE_VECTORS,
                value=self.reference_vectors.tolist(),
                source=self.__class__.__name__,
            ),
            DictMessage(
                topic=SelectorMessageTopics.STATE,
                value={
                    "ideal": self.ideal,
                    "nadir": self.nadir,
                    "partial_penalty_factor": self._partial_penalty_factor(),
                },
                source=self.__class__.__name__,
            ),
            # DictMessage(
            #     topic=SelectorMessageTopics.SELECTED_INDIVIDUALS,
            #     value=self.selection[0].tolist(),
            #     source=self.__class__.__name__,
            # ),
            message,
        ]
        return state_verbose

    def _adapt(self):
        self.adapted_reference_vectors = self.reference_vectors
        if self.ideal is not None and self.nadir is not None:
            for i in range(self.reference_vectors.shape[0]):
                self.adapted_reference_vectors[i] = self.reference_vectors[i] * (self.nadir - self.ideal)
        self.adapted_reference_vectors = (
            self.adapted_reference_vectors / np.linalg.norm(self.adapted_reference_vectors, axis=1)[:, None]
        )

        # More efficient way to calculate the gamma values
        self.reference_vectors_gamma = np.arccos(
            np.dot(self.adapted_reference_vectors, np.transpose(self.adapted_reference_vectors))
        )
        self.reference_vectors_gamma[np.where(self.reference_vectors_gamma == 0)] = np.inf
        self.reference_vectors_gamma = np.min(self.reference_vectors_gamma, axis=1)


class NSGAIII_select(BaseDecompositionSelector):
    """The NSGA-III selection operator. Code is heavily based on the version of nsga3 in the pymoo package by msu-coinlab.

    Parameters
    ----------
    pop : Population
        [description]
    n_survive : int, optional
        [description], by default None

    """

    @property
    def provided_topics(self):
        return {
            0: [],
            1: [
                SelectorMessageTopics.STATE,
            ],
            2: [
                SelectorMessageTopics.REFERENCE_VECTORS,
                SelectorMessageTopics.STATE,
                SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
            ],
        }

    @property
    def interested_topics(self):
        return []

    def __init__(
        self,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        reference_vector_options: ReferenceVectorOptions | None = None,
    ):
        if reference_vector_options is None:
            reference_vector_options = ReferenceVectorOptions(
                adaptation_frequency=0,
                creation_type="simplex",
                vector_type="planar",
                number_of_vectors=500,
            )
        super().__init__(
            problem, reference_vector_options=reference_vector_options, verbosity=verbosity, publisher=publisher
        )
        self.adapted_reference_vectors = None
        self.worst_fitness: np.ndarray | None = None
        self.extreme_points: np.ndarray | None = None
        self.n_survive = self.reference_vectors.shape[0]
        self.selection: list[int] | None = None
        self.selected_individuals: SolutionType | None = None
        self.selected_targets: pl.DataFrame | None = None

    def do(
        self,
        parents: tuple[SolutionType, pl.DataFrame],
        offsprings: tuple[SolutionType, pl.DataFrame],
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Perform the selection operation.

        Args:
            parents (tuple[SolutionType, pl.DataFrame]): the decision variables as the first element.
                The second element is the objective values, targets, and constraint violations.
            offsprings (tuple[SolutionType, pl.DataFrame]): the decision variables as the first element.
                The second element is the objective values, targets, and constraint violations.

        Returns:
            tuple[SolutionType, pl.DataFrame]: The selected decision variables and their objective values,
                targets, and constraint violations.
        """
        if isinstance(parents[0], pl.DataFrame) and isinstance(offsprings[0], pl.DataFrame):
            solutions = parents[0].vstack(offsprings[0])
        elif isinstance(parents[0], list) and isinstance(offsprings[0], list):
            solutions = parents[0] + offsprings[0]
        else:
            raise TypeError("The decision variables must be either a list or a polars DataFrame, not both")
        alltargets = parents[1].vstack(offsprings[1])
        targets = alltargets[self.target_symbols].to_numpy()
        if self.constraints_symbols is None:
            constraints = None
        else:
            constraints = (
                parents[1][self.constraints_symbols].vstack(offsprings[1][self.constraints_symbols]).to_numpy()
            )
        ref_dirs = self.reference_vectors

        if self.ideal is None:
            self.ideal = np.min(targets, axis=0)
        else:
            self.ideal = np.min(np.vstack((self.ideal, np.min(targets, axis=0))), axis=0)
        fitness = targets
        # Calculating fronts and ranks
        # fronts, dl, dc, rank = nds(fitness)
        fronts = fast_non_dominated_sort(fitness)
        fronts = [np.where(fronts[i])[0] for i in range(len(fronts))]
        non_dominated = fronts[0]

        if self.worst_fitness is None:
            self.worst_fitness = np.max(fitness, axis=0)
        else:
            self.worst_fitness = np.amax(np.vstack((self.worst_fitness, fitness)), axis=0)

        # Calculating worst points
        worst_of_population = np.amax(fitness, axis=0)
        worst_of_front = np.max(fitness[non_dominated, :], axis=0)
        self.extreme_points = self.get_extreme_points_c(
            fitness[non_dominated, :], self.ideal, extreme_points=self.extreme_points
        )
        self.nadir_point = nadir_point = self.get_nadir_point(
            self.extreme_points,
            self.ideal,
            self.worst_fitness,
            worst_of_population,
            worst_of_front,
        )

        # Finding individuals in first 'n' fronts
        selection = np.asarray([], dtype=int)
        for front_id in range(len(fronts)):
            if len(np.concatenate(fronts[: front_id + 1])) < self.n_survive:
                continue
            else:
                fronts = fronts[: front_id + 1]
                selection = np.concatenate(fronts)
                break
        F = fitness[selection]

        last_front = fronts[-1]

        # Selecting individuals from the last acceptable front.
        if len(selection) > self.n_survive:
            niche_of_individuals, dist_to_niche = self.associate_to_niches(F, ref_dirs, self.ideal, nadir_point)
            # if there is only one front
            if len(fronts) == 1:
                n_remaining = self.n_survive
                until_last_front = np.array([], dtype=int)
                niche_count = np.zeros(len(ref_dirs), dtype=int)

            # if some individuals already survived
            else:
                until_last_front = np.concatenate(fronts[:-1])
                id_until_last_front = list(range(len(until_last_front)))
                niche_count = self.calc_niche_count(len(ref_dirs), niche_of_individuals[id_until_last_front])
                n_remaining = self.n_survive - len(until_last_front)

            last_front_selection_id = list(range(len(until_last_front), len(selection)))
            if np.any(selection[last_front_selection_id] != last_front):
                print("error!!!")
            selected_from_last_front = self.niching(
                fitness[last_front, :],
                n_remaining,
                niche_count,
                niche_of_individuals[last_front_selection_id],
                dist_to_niche[last_front_selection_id],
            )
            final_selection = np.concatenate((until_last_front, last_front[selected_from_last_front]))
            if self.extreme_points is None:
                print("Error")
            if final_selection is None:
                print("Error")
        else:
            final_selection = selection

        self.selection = final_selection.tolist()
        if isinstance(solutions, pl.DataFrame) and self.selection is not None:
            self.selected_individuals = solutions[self.selection]
        elif isinstance(solutions, list) and self.selection is not None:
            self.selected_individuals = [solutions[i] for i in self.selection]
        else:
            raise RuntimeError("Something went wrong with the selection")
        self.selected_targets = alltargets[self.selection]

        self.notify()
        return self.selected_individuals, self.selected_targets

    def get_extreme_points_c(self, F, ideal_point, extreme_points=None):
        """Taken from pymoo"""
        # calculate the asf which is used for the extreme point decomposition
        asf = np.eye(F.shape[1])
        asf[asf == 0] = 1e6

        # add the old extreme points to never loose them for normalization
        _F = F
        if extreme_points is not None:
            _F = np.concatenate([extreme_points, _F], axis=0)

        # use __F because we substitute small values to be 0
        __F = _F - ideal_point
        __F[__F < 1e-3] = 0

        # update the extreme points for the normalization having the highest asf value
        # each
        F_asf = np.max(__F * asf[:, None, :], axis=2)
        I = np.argmin(F_asf, axis=1)
        extreme_points = _F[I, :]
        return extreme_points

    def get_nadir_point(
        self,
        extreme_points,
        ideal_point,
        worst_point,
        worst_of_front,
        worst_of_population,
    ):
        LinAlgError = np.linalg.LinAlgError
        try:
            # find the intercepts using gaussian elimination
            M = extreme_points - ideal_point
            b = np.ones(extreme_points.shape[1])
            plane = np.linalg.solve(M, b)
            intercepts = 1 / plane

            nadir_point = ideal_point + intercepts

            if not np.allclose(np.dot(M, plane), b) or np.any(intercepts <= 1e-6) or np.any(nadir_point > worst_point):
                raise LinAlgError()

        except LinAlgError:
            nadir_point = worst_of_front

        b = nadir_point - ideal_point <= 1e-6
        nadir_point[b] = worst_of_population[b]
        return nadir_point

    def niching(self, F, n_remaining, niche_count, niche_of_individuals, dist_to_niche):
        survivors = []

        # boolean array of elements that are considered for each iteration
        mask = np.full(F.shape[0], True)

        while len(survivors) < n_remaining:
            # all niches where new individuals can be assigned to
            next_niches_list = np.unique(niche_of_individuals[mask])

            # pick a niche with minimum assigned individuals - break tie if necessary
            next_niche_count = niche_count[next_niches_list]
            next_niche = np.where(next_niche_count == next_niche_count.min())[0]
            next_niche = next_niches_list[next_niche]
            next_niche = next_niche[np.random.randint(0, len(next_niche))]

            # indices of individuals that are considered and assign to next_niche
            next_ind = np.where(np.logical_and(niche_of_individuals == next_niche, mask))[0]

            # shuffle to break random tie (equal perp. dist) or select randomly
            np.random.shuffle(next_ind)

            if niche_count[next_niche] == 0:
                next_ind = next_ind[np.argmin(dist_to_niche[next_ind])]
            else:
                # already randomized through shuffling
                next_ind = next_ind[0]

            mask[next_ind] = False
            survivors.append(int(next_ind))

            niche_count[next_niche] += 1

        return survivors

    def associate_to_niches(self, F, ref_dirs, ideal_point, nadir_point, utopian_epsilon=0.0):
        utopian_point = ideal_point - utopian_epsilon

        denom = nadir_point - utopian_point
        denom[denom == 0] = 1e-12

        # normalize by ideal point and intercepts
        N = (F - utopian_point) / denom
        dist_matrix = self.calc_perpendicular_distance(N, ref_dirs)

        niche_of_individuals = np.argmin(dist_matrix, axis=1)
        dist_to_niche = dist_matrix[np.arange(F.shape[0]), niche_of_individuals]

        return niche_of_individuals, dist_to_niche

    def calc_niche_count(self, n_niches, niche_of_individuals):
        niche_count = np.zeros(n_niches, dtype=int)
        index, count = np.unique(niche_of_individuals, return_counts=True)
        niche_count[index] = count
        return niche_count

    def calc_perpendicular_distance(self, N, ref_dirs):
        u = np.tile(ref_dirs, (len(N), 1))
        v = np.repeat(N, len(ref_dirs), axis=0)

        norm_u = np.linalg.norm(u, axis=1)

        scalar_proj = np.sum(v * u, axis=1) / norm_u
        proj = scalar_proj[:, None] * u / norm_u[:, None]
        val = np.linalg.norm(proj - v, axis=1)
        matrix = np.reshape(val, (len(N), len(ref_dirs)))

        return matrix

    def state(self) -> Sequence[Message]:
        if self.verbosity == 0 or self.selection is None or self.selected_targets is None:
            return []
        if self.verbosity == 1:
            return [
                Array2DMessage(
                    topic=SelectorMessageTopics.REFERENCE_VECTORS,
                    value=self.reference_vectors.tolist(),
                    source=self.__class__.__name__,
                ),
                DictMessage(
                    topic=SelectorMessageTopics.STATE,
                    value={
                        "ideal": self.ideal,
                        "nadir": self.worst_fitness,
                        "extreme_points": self.extreme_points,
                        "n_survive": self.n_survive,
                    },
                    source=self.__class__.__name__,
                ),
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
        state_verbose = [
            Array2DMessage(
                topic=SelectorMessageTopics.REFERENCE_VECTORS,
                value=self.reference_vectors.tolist(),
                source=self.__class__.__name__,
            ),
            DictMessage(
                topic=SelectorMessageTopics.STATE,
                value={
                    "ideal": self.ideal,
                    "nadir": self.worst_fitness,
                    "extreme_points": self.extreme_points,
                    "n_survive": self.n_survive,
                },
                source=self.__class__.__name__,
            ),
            # Array2DMessage(
            #     topic=SelectorMessageTopics.SELECTED_INDIVIDUALS,
            #     value=self.selected_individuals,
            #     source=self.__class__.__name__,
            # ),
            message,
        ]
        return state_verbose

    def update(self, message: Message) -> None:
        pass
