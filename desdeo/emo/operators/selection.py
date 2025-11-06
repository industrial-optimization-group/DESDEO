"""The base class for selection operators.

Some operators should be rewritten.
TODO:@light-weaver
"""

import warnings
from abc import abstractmethod
from collections.abc import Sequence
from enum import StrEnum
from itertools import combinations
from typing import Callable, Literal, TypedDict, TypeVar

import numpy as np
import polars as pl
from numba import njit
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.special import comb
from scipy.stats.qmc import LatinHypercube
from sqlalchemy import false

from desdeo.problem import Problem
from desdeo.tools import get_corrected_ideal_and_nadir
from desdeo.tools.indicators_binary import self_epsilon
from desdeo.tools.message import (
    Array2DMessage,
    DictMessage,
    Message,
    NumpyArrayMessage,
    PolarsDataFrameMessage,
    SelectorMessageTopics,
    TerminatorMessageTopics,
)
from desdeo.tools.non_dominated_sorting import fast_non_dominated_sort
from desdeo.tools.patterns import Publisher, Subscriber

SolutionType = TypeVar("SolutionType", list, pl.DataFrame)


class BaseSelector(Subscriber):
    """A base class for selection operators."""

    def __init__(self, problem: Problem, verbosity: int, publisher: Publisher, seed: int = 0):
        """Initialize a selection operator."""
        super().__init__(verbosity=verbosity, publisher=publisher)
        self.problem = problem
        self.variable_symbols = [x.symbol for x in problem.get_flattened_variables()]
        self.objective_symbols = [x.symbol for x in problem.objectives]
        self.maximization_mult = {x.symbol: -1 if x.maximize else 1 for x in problem.objectives}

        if problem.scalarization_funcs is None:
            self.target_symbols = [f"{x.symbol}_min" for x in problem.objectives]
            try:
                ideal, nadir = get_corrected_ideal_and_nadir(problem)  # This is for the minimized problem
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
        self.seed = seed
        self.rng = np.random.default_rng(seed)

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


class ReferenceVectorOptions(BaseModel):
    """Pydantic model for Reference Vector arguments."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    adaptation_frequency: int = Field(default=0)
    """Number of generations between reference vector adaptation. If set to 0, no adaptation occurs. Defaults to 0.
    Only used if no preference is provided."""
    creation_type: Literal["simplex", "s_energy"] = Field(default="simplex")
    """The method for creating reference vectors. Defaults to "simplex".
    Currently only "simplex" is implemented. Future versions will include "s_energy".

    If set to "simplex", the reference vectors are created using the simplex lattice design method.
    This method is generates distributions with specific numbers of reference vectors.
    Check: https://www.itl.nist.gov/div898/handbook/pri/section5/pri542.htm for more information.
    If set to "s_energy", the reference vectors are created using the Riesz s-energy criterion. This method is used to
    distribute an arbitrary number of reference vectors in the objective space while minimizing the s-energy.
    Currently not implemented.
    """
    vector_type: Literal["spherical", "planar"] = Field(default="spherical")
    """The method for normalizing the reference vectors. Defaults to "spherical"."""
    lattice_resolution: int | None = None
    """Number of divisions along an axis when creating the simplex lattice. This is not required/used for the "s_energy"
    method. If not specified, the lattice resolution is calculated based on the `number_of_vectors`. If "spherical" is 
    selected as the `vector_type`, this value overrides the `number_of_vectors`.
    """
    number_of_vectors: int = 200
    """Number of reference vectors to be created. If "simplex" is selected as the `creation_type`, then the closest
    `lattice_resolution` is calculated based on this value. If "s_energy" is selected, then this value is used directly.
    Note that if neither `lattice_resolution` nor `number_of_vectors` is specified, the number of vectors defaults to
    200. Overridden if "spherical" is selected as the `vector_type` and `lattice_resolution` is provided.
    """
    adaptation_distance: float = Field(default=0.2)
    """Distance parameter for the interactive adaptation methods. Defaults to 0.2."""
    reference_point: dict[str, float] | None = Field(default=None)
    """The reference point for interactive adaptation."""
    preferred_solutions: dict[str, list[float]] | None = Field(default=None)
    """The preferred solutions for interactive adaptation."""
    non_preferred_solutions: dict[str, list[float]] | None = Field(default=None)
    """The non-preferred solutions for interactive adaptation."""
    preferred_ranges: dict[str, list[float]] | None = Field(default=None)
    """The preferred ranges for interactive adaptation."""


class BaseDecompositionSelector(BaseSelector):
    """Base class for decomposition based selection operators."""

    def __init__(
        self,
        problem: Problem,
        reference_vector_options: ReferenceVectorOptions,
        verbosity: int,
        publisher: Publisher,
        invert_reference_vectors: bool = False,
        seed: int = 0,
    ):
        super().__init__(problem, verbosity=verbosity, publisher=publisher, seed=seed)
        self.reference_vector_options = reference_vector_options
        self.invert_reference_vectors = invert_reference_vectors
        self.reference_vectors: np.ndarray
        self.reference_vectors_initial: np.ndarray

        if self.reference_vector_options.creation_type == "s_energy":
            raise NotImplementedError("Riesz s-energy criterion is not yet implemented.")

        self._create_simplex()

        if self.reference_vector_options.reference_point:
            corrected_rp = np.array(
                [
                    self.reference_vector_options.reference_point[x] * self.maximization_mult[x]
                    for x in self.objective_symbols
                ]
            )
            self.interactive_adapt_3(
                corrected_rp,
                translation_param=self.reference_vector_options.adaptation_distance,
            )
        elif self.reference_vector_options.preferred_solutions:
            corrected_sols = np.array(
                [
                    np.array(self.reference_vector_options.preferred_solutions[x]) * self.maximization_mult[x]
                    for x in self.objective_symbols
                ]
            ).T
            self.interactive_adapt_1(
                corrected_sols,
                translation_param=self.reference_vector_options.adaptation_distance,
            )
        elif self.reference_vector_options.non_preferred_solutions:
            corrected_sols = np.array(
                [
                    np.array(self.reference_vector_options.non_preferred_solutions[x]) * self.maximization_mult[x]
                    for x in self.objective_symbols
                ]
            ).T
            self.interactive_adapt_2(
                corrected_sols,
                predefined_distance=self.reference_vector_options.adaptation_distance,
                ord=2 if self.reference_vector_options.vector_type == "spherical" else 1,
            )
        elif self.reference_vector_options.preferred_ranges:
            corrected_ranges = np.array(
                [
                    np.array(self.reference_vector_options.preferred_ranges[x]) * self.maximization_mult[x]
                    for x in self.objective_symbols
                ]
            ).T
            self.interactive_adapt_4(
                corrected_ranges,
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

        if self.reference_vector_options.lattice_resolution:
            lattice_resolution = self.reference_vector_options.lattice_resolution
        else:
            lattice_resolution = approx_lattice_resolution(
                self.reference_vector_options.number_of_vectors, num_dims=self.num_dims
            )

        number_of_vectors: int = comb(
            lattice_resolution + self.num_dims - 1,
            self.num_dims - 1,
            exact=True,
        )

        self.reference_vector_options.number_of_vectors = number_of_vectors
        self.reference_vector_options.lattice_resolution = lattice_resolution

        temp1 = range(1, self.num_dims + lattice_resolution)
        temp1 = np.array(list(combinations(temp1, self.num_dims - 1)))
        temp2 = np.array([range(self.num_dims - 1)] * number_of_vectors)
        temp = temp1 - temp2 - 1
        weight = np.zeros((number_of_vectors, self.num_dims), dtype=int)
        weight[:, 0] = temp[:, 0]
        for i in range(1, self.num_dims - 1):
            weight[:, i] = temp[:, i] - temp[:, i - 1]
        weight[:, -1] = lattice_resolution - temp[:, -1]
        if not self.invert_reference_vectors: # todo, this currently only exists for nsga3
            self.reference_vectors = weight / lattice_resolution
        else:
            self.reference_vectors = 1 - (weight / lattice_resolution)
        self.reference_vectors_initial = np.copy(self.reference_vectors)
        self._normalize_rvs()

    def _normalize_rvs(self):
        """Normalize the reference vectors to a unit hypersphere."""
        if self.reference_vector_options.vector_type == "spherical":
            norm = np.linalg.norm(self.reference_vectors, axis=1).reshape(-1, 1)
            norm[norm == 0] = np.finfo(float).eps
            self.reference_vectors = np.divide(self.reference_vectors, norm)
            return
        if self.reference_vector_options.vector_type == "planar":
            if not self.invert_reference_vectors:
                norm = np.sum(self.reference_vectors, axis=1).reshape(-1, 1)
                self.reference_vectors = np.divide(self.reference_vectors, norm)
                return
            else:
                norm = np.sum(1 - self.reference_vectors, axis=1).reshape(-1, 1)
                self.reference_vectors = 1 - np.divide(1 - self.reference_vectors, norm)
                return
        # Not needed due to pydantic validation
        raise ValueError("Invalid vector type. Must be either 'spherical' or 'planar'.")

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

    def interactive_adapt_2(self, z: np.ndarray, predefined_distance: float, ord: int) -> None:
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
                re-positioned somewhere else. Default value: 0.2
            ord (int): Order of the norm. Default is 2, i.e., Euclidian distance.
        """
        # calculate L1 norm of non-preferred solution(s)
        z = np.atleast_2d(z)
        norm = np.linalg.norm(z, ord=ord, axis=1).reshape(np.shape(z)[0], 1)

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
        lhs = LatinHypercube(d=self.num_dims, seed=self.rng)
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


class ParameterAdaptationStrategy(StrEnum):
    """The parameter adaptation strategies for the RVEA selector."""

    GENERATION_BASED = "GENERATION_BASED"  # Based on the current generation and the maximum generation.
    FUNCTION_EVALUATION_BASED = (
        "FUNCTION_EVALUATION_BASED"  # Based on the current function evaluation and the maximum function evaluation.
    )
    OTHER = "OTHER"  # As of yet undefined strategies.


@njit
def _rvea_selection(
    fitness: np.ndarray, reference_vectors: np.ndarray, ideal: np.ndarray, partial_penalty: float, gamma: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Select individuals based on their fitness and their distance to the reference vectors.

    Args:
        fitness (np.ndarray): The fitness values of the individuals.
        reference_vectors (np.ndarray): The reference vectors.
        ideal (np.ndarray): The ideal point.
        partial_penalty (float): The partial penalty in APD.
        gamma (np.ndarray): The angle between current and closest reference vector.

    Returns:
        tuple[np.ndarray, np.ndarray]: The selected individuals and their APD fitness values.
    """
    tranlated_fitness = fitness - ideal
    num_vectors = reference_vectors.shape[0]
    num_solutions = fitness.shape[0]

    cos_matrix = np.zeros((num_solutions, num_vectors))

    for i in range(num_solutions):
        solution = tranlated_fitness[i]
        norm = np.linalg.norm(solution)
        for j in range(num_vectors):
            cos_matrix[i, j] = np.dot(solution, reference_vectors[j]) / max(1e-10, norm)  # Avoid division by zero

    assignment_matrix = np.zeros((num_solutions, num_vectors), dtype=np.bool_)

    for i in range(num_solutions):
        assignment_matrix[i, np.argmax(cos_matrix[i])] = True

    selection = np.zeros(num_solutions, dtype=np.bool_)
    apd_fitness = np.zeros(num_solutions, dtype=np.float64)

    for j in range(num_vectors):
        min_apd = np.inf
        select = -1
        for i in np.where(assignment_matrix[:, j])[0]:
            solution = tranlated_fitness[i]
            apd = (1 + (partial_penalty * np.arccos(cos_matrix[i, j]) / gamma[j])) * np.linalg.norm(solution)
            apd_fitness[i] = apd
            if apd < min_apd:
                min_apd = apd
                select = i
        selection[select] = True

    return selection, apd_fitness


@njit
def _rvea_selection_constrained(
    fitness: np.ndarray,
    constraints: np.ndarray,
    reference_vectors: np.ndarray,
    ideal: np.ndarray,
    partial_penalty: float,
    gamma: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Select individuals based on their fitness and their distance to the reference vectors.

    Args:
        fitness (np.ndarray): The fitness values of the individuals.
        constraints (np.ndarray): The constraint violations of the individuals.
        reference_vectors (np.ndarray): The reference vectors.
        ideal (np.ndarray): The ideal point.
        partial_penalty (float): The partial penalty in APD.
        gamma (np.ndarray): The angle between current and closest reference vector.

    Returns:
        tuple[np.ndarray, np.ndarray]: The selected individuals and their APD fitness values.
    """
    tranlated_fitness = fitness - ideal
    num_vectors = reference_vectors.shape[0]
    num_solutions = fitness.shape[0]

    violations = np.maximum(0, constraints)

    cos_matrix = np.zeros((num_solutions, num_vectors))

    for i in range(num_solutions):
        solution = tranlated_fitness[i]
        norm = np.linalg.norm(solution)
        for j in range(num_vectors):
            cos_matrix[i, j] = np.dot(solution, reference_vectors[j]) / max(1e-10, norm)  # Avoid division by zero

    assignment_matrix = np.zeros((num_solutions, num_vectors), dtype=np.bool_)

    for i in range(num_solutions):
        assignment_matrix[i, np.argmax(cos_matrix[i])] = True

    selection = np.zeros(num_solutions, dtype=np.bool_)
    apd_fitness = np.zeros(num_solutions, dtype=np.float64)

    for j in range(num_vectors):
        min_apd = np.inf
        min_violation = np.inf
        select = -1
        select_violation = -1
        for i in np.where(assignment_matrix[:, j])[0]:
            solution = tranlated_fitness[i]
            apd = (1 + (partial_penalty * np.arccos(cos_matrix[i, j]) / gamma[j])) * np.linalg.norm(solution)
            apd_fitness[i] = apd
            feasible = np.all(violations[i] == 0)
            current_violation = np.sum(violations[i])
            if feasible:
                if apd < min_apd:
                    min_apd = apd
                    select = i
            elif current_violation < min_violation:
                min_violation = current_violation
                select_violation = i
        if select != -1:
            selection[select] = True
        else:
            selection[select_violation] = True

    return selection, apd_fitness


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
        reference_vector_options: ReferenceVectorOptions | dict | None = None,
        seed: int = 0,
    ):
        if parameter_adaptation_strategy not in ParameterAdaptationStrategy:
            raise TypeError(f"Parameter adaptation strategy must be of Type {type(ParameterAdaptationStrategy)}")
        if parameter_adaptation_strategy == ParameterAdaptationStrategy.OTHER:
            raise ValueError("Other parameter adaptation strategies are not yet implemented.")

        if reference_vector_options is None:
            reference_vector_options = ReferenceVectorOptions()

        if isinstance(reference_vector_options, dict):
            reference_vector_options = ReferenceVectorOptions.model_validate(reference_vector_options)

        # Just asserting correct options for RVEA
        reference_vector_options.vector_type = "spherical"
        if reference_vector_options.adaptation_frequency == 0:
            warnings.warn(
                "Adaptation frequency was set to 0. Setting it to 100 for RVEA selector. "
                "Set it to 0 only if you provide preference information.",
                UserWarning,
                stacklevel=2,
            )
            reference_vector_options.adaptation_frequency = 100

        super().__init__(
            problem=problem,
            reference_vector_options=reference_vector_options,
            verbosity=verbosity,
            publisher=publisher,
            seed=seed,
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
        self.adapted_reference_vectors = None

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
            # No constraints :)
            if self.ideal is None:
                self.ideal = np.min(targets, axis=0)
            else:
                self.ideal = np.min(np.vstack((self.ideal, np.min(targets, axis=0))), axis=0)
            self.nadir = np.max(targets, axis=0) if self.nadir is None else self.nadir
            if self.adapted_reference_vectors is None:
                self._adapt()
            selection, _ = _rvea_selection(
                fitness=targets,
                reference_vectors=self.adapted_reference_vectors,
                ideal=self.ideal,
                partial_penalty=self._partial_penalty_factor(),
                gamma=self.reference_vectors_gamma,
            )
        else:
            # Yes constraints :(
            constraints = (
                parents[1][self.constraints_symbols].vstack(offsprings[1][self.constraints_symbols]).to_numpy()
            )
            feasible = (constraints <= 0).all(axis=1)
            # Note that
            if self.ideal is None:
                # TODO: This breaks if there are no feasible solutions in the initial population
                self.ideal = np.min(targets[feasible], axis=0)
            else:
                self.ideal = np.min(np.vstack((self.ideal, np.min(targets[feasible], axis=0))), axis=0)
            try:
                nadir = np.max(targets[feasible], axis=0)
                self.nadir = nadir
            except ValueError:  # No feasible solution in current population
                pass  # Use previous nadir
            if self.adapted_reference_vectors is None:
                self._adapt()
            selection, _ = _rvea_selection_constrained(
                fitness=targets,
                constraints=constraints,
                reference_vectors=self.adapted_reference_vectors,
                ideal=self.ideal,
                partial_penalty=self._partial_penalty_factor(),
                gamma=self.reference_vectors_gamma,
            )

        self.selection = np.where(selection)[0].tolist()
        self.selected_individuals = solutions[self.selection]
        self.selected_targets = alltargets[self.selection]
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
                if (
                    self.reference_vector_options.adaptation_frequency > 0
                    and self.numerator % self.reference_vector_options.adaptation_frequency == 0
                ):
                    self._adapt()
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

        self.reference_vectors_gamma = np.zeros(self.adapted_reference_vectors.shape[0])
        for i in range(self.adapted_reference_vectors.shape[0]):
            closest_angle = np.inf
            for j in range(self.adapted_reference_vectors.shape[0]):
                if i != j:
                    angle = np.arccos(
                        np.clip(np.dot(self.adapted_reference_vectors[i], self.adapted_reference_vectors[j]), -1.0, 1.0)
                    )
                    if angle < closest_angle and angle > 0:
                        # In cases with extreme differences in obj func ranges
                        # sometimes, the closest reference vectors are so close that
                        # the angle between them is 0 according to arccos (literally 0)
                        closest_angle = angle
            self.reference_vectors_gamma[i] = closest_angle

@njit
def jitted_calc_perpendicular_distance(
    solutions: np.ndarray, ref_dirs: np.ndarray, invert_reference_vectors: bool
) -> np.ndarray:
    """Calculate the perpendicular distance between solutions and reference directions.

    Args:
        solutions (np.ndarray): The normalized solutions.
        ref_dirs (np.ndarray): The reference directions.
        invert_reference_vectors (bool): Whether to invert the reference vectors.

    Returns:
        np.ndarray: The perpendicular distance matrix.
    """
    matrix = np.zeros((solutions.shape[0], ref_dirs.shape[0]))
    for i in range(ref_dirs.shape[0]):
        for j in range(solutions.shape[0]):
            if invert_reference_vectors:
                unit_vector = 1 - ref_dirs[i]
                unit_vector = -unit_vector / np.linalg.norm(unit_vector)
            else:
                unit_vector = ref_dirs[i] / np.linalg.norm(ref_dirs[i])
            component = ref_dirs[i] - solutions[j] - np.dot(ref_dirs[i] - solutions[j], unit_vector) * unit_vector
            matrix[j, i] = np.linalg.norm(component)
    return matrix

class NSGA3Selector(BaseDecompositionSelector):
    """The NSGA-III selection operator, heavily based on the version of nsga3 in the pymoo package by msu-coinlab."""

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
        invert_reference_vectors: bool = False,
        seed: int = 0,
    ):
        """Initialize the NSGA-III selection operator.

        Args:
            problem (Problem): The optimization problem to be solved.
            verbosity (int): The verbosity level of the operator.
            publisher (Publisher): The publisher to use for communication.
            reference_vector_options (ReferenceVectorOptions | None, optional): Options for the reference vectors. Defaults to None.
            invert_reference_vectors (bool, optional): Whether to invert the reference vectors. Defaults to False.
            seed (int, optional): The random seed to use. Defaults to 0.
        """
        if reference_vector_options is None:
            reference_vector_options = ReferenceVectorOptions()
        elif isinstance(reference_vector_options, dict):
            reference_vector_options = ReferenceVectorOptions.model_validate(reference_vector_options)

        # Just asserting correct options for NSGA-III
        reference_vector_options.vector_type = "planar"
        super().__init__(
            problem,
            reference_vector_options=reference_vector_options,
            verbosity=verbosity,
            publisher=publisher,
            seed=seed,
            invert_reference_vectors=invert_reference_vectors,
        )
        if self.constraints_symbols is not None:
            raise NotImplementedError("NSGA3 selector does not support constraints. Please use a different selector.")

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
            next_niche = next_niche[self.rng.integers(0, len(next_niche))]

            # indices of individuals that are considered and assign to next_niche
            next_ind = np.where(np.logical_and(niche_of_individuals == next_niche, mask))[0]

            # shuffle to break random tie (equal perp. dist) or select randomly
            self.rng.shuffle(next_ind)

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
        # dist_matrix = self.calc_perpendicular_distance(N, ref_dirs)
        dist_matrix = jitted_calc_perpendicular_distance(N, ref_dirs, self.invert_reference_vectors)

        niche_of_individuals = np.argmin(dist_matrix, axis=1)
        dist_to_niche = dist_matrix[np.arange(F.shape[0]), niche_of_individuals]

        return niche_of_individuals, dist_to_niche

    def calc_niche_count(self, n_niches, niche_of_individuals):
        niche_count = np.zeros(n_niches, dtype=int)
        index, count = np.unique(niche_of_individuals, return_counts=True)
        niche_count[index] = count
        return niche_count

    def calc_perpendicular_distance(self, N, ref_dirs):
        if self.invert_reference_vectors:
            u = np.tile(-ref_dirs, (len(N), 1))
            v = np.repeat(1 - N, len(ref_dirs), axis=0)
        else:
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


@njit
def _ibea_fitness(fitness_components: np.ndarray, kappa: float) -> np.ndarray:
    """Calculates the IBEA fitness for each individual based on pairwise fitness components.

    Args:
        fitness_components (np.ndarray): The pairwise fitness components of the individuals.
        kappa (float): The kappa value for the IBEA selection.

    Returns:
        np.ndarray: The IBEA fitness values for each individual.
    """
    num_individuals = fitness_components.shape[0]
    fitness = np.zeros(num_individuals)
    for i in range(num_individuals):
        for j in range(num_individuals):
            if i != j:
                fitness[i] -= np.exp(-fitness_components[j, i] / kappa)
    return fitness


@njit
def _ibea_select(fitness_components: np.ndarray, bad_sols: np.ndarray, kappa: float) -> int:
    """Selects the worst individual based on the IBEA indicator.

    Args:
        fitness_components (np.ndarray): The pairwise fitness components of the individuals.
        bad_sols (np.ndarray): A boolean array indicating which individuals are considered "bad".
        kappa (float): The kappa value for the IBEA selection.

    Returns:
        int: The index of the selected individual.
    """
    fitness = np.zeros(len(fitness_components))
    for i in range(len(fitness_components)):
        if bad_sols[i]:
            continue
        for j in range(len(fitness_components)):
            if bad_sols[j] or i == j:
                continue
            fitness[i] -= np.exp(-fitness_components[j, i] / kappa)
    choice = np.argmin(fitness)
    if fitness[choice] >= 0:
        if sum(bad_sols) == len(fitness_components) - 1:
            # If all but one individual is chosen, select the last one
            return np.where(~bad_sols)[0][0]
        raise RuntimeError("All individuals have non-negative fitness. Cannot select a new individual.")
    return choice


@njit
def _ibea_select_all(fitness_components: np.ndarray, population_size: int, kappa: float) -> np.ndarray:
    """Selects all individuals based on the IBEA indicator.

    Args:
        fitness_components (np.ndarray): The pairwise fitness components of the individuals.
        population_size (int): The desired size of the population after selection.
        kappa (float): The kappa value for the IBEA selection.

    Returns:
        list[int]: The list of indices of the selected individuals.
    """
    current_pop_size = len(fitness_components)
    bad_sols = np.zeros(current_pop_size, dtype=np.bool_)
    fitness = np.zeros(len(fitness_components))
    mod_fit_components = np.exp(-fitness_components / kappa)
    for i in range(len(fitness_components)):
        for j in range(len(fitness_components)):
            if i == j:
                continue
            fitness[i] -= mod_fit_components[j, i]
    while current_pop_size - sum(bad_sols) > population_size:
        selected = np.argmin(fitness)
        if fitness[selected] >= 0:
            if sum(bad_sols) == len(fitness_components) - 1:
                # If all but one individual is chosen, select the last one
                selected = np.where(~bad_sols)[0][0]
            raise RuntimeError("All individuals have non-negative fitness. Cannot select a new individual.")
        fitness[selected] = np.inf  # Make sure that this individual is not selected again
        bad_sols[selected] = True
        for i in range(len(mod_fit_components)):
            if bad_sols[i]:
                continue
            # Update fitness of the remaining individuals
            fitness[i] += mod_fit_components[selected, i]
    return ~bad_sols


class IBEASelector(BaseSelector):
    """The adaptive IBEA selection operator.

    Reference: Zitzler, E., Künzli, S. (2004). Indicator-Based Selection in Multiobjective Search. In: Yao, X., et al.
    Parallel Problem Solving from Nature - PPSN VIII. PPSN 2004. Lecture Notes in Computer Science, vol 3242.
    Springer, Berlin, Heidelberg. https://doi.org/10.1007/978-3-540-30217-9_84
    """

    @property
    def provided_topics(self):
        return {
            0: [],
            1: [SelectorMessageTopics.STATE],
            2: [SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS, SelectorMessageTopics.SELECTED_FITNESS],
        }

    @property
    def interested_topics(self):
        return []

    def __init__(
        self,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        population_size: int,
        kappa: float = 0.05,
        binary_indicator: Callable[[np.ndarray], np.ndarray] = self_epsilon,
        seed: int = 0,
    ):
        """Initialize the IBEA selector.

        Args:
            problem (Problem): The problem to solve.
            verbosity (int): The verbosity level of the selector.
            publisher (Publisher): The publisher to send messages to.
            population_size (int): The size of the population to select.
            kappa (float, optional): The kappa value for the IBEA selection. Defaults to 0.05.
            binary_indicator (Callable[[np.ndarray], np.ndarray], optional): The binary indicator function to use.
                Defaults to self_epsilon with uses binary addaptive epsilon indicator.
        """
        # TODO(@light-weaver): IBEA doesn't perform as good as expected
        # The distribution of solutions found isn't very uniform
        # Update 21st August, tested against jmetalpy IBEA. Our version is both faster and better
        # What is happening???
        # Results are similar to this https://github.com/Xavier-MaYiMing/IBEA/
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)
        self.selection: list[int] | None = None
        self.selected_individuals: SolutionType | None = None
        self.selected_targets: pl.DataFrame | None = None
        self.binary_indicator = binary_indicator
        self.kappa = kappa
        self.population_size = population_size
        if self.constraints_symbols is not None:
            raise NotImplementedError("IBEA selector does not support constraints. Please use a different selector.")

    def do(
        self, parents: tuple[SolutionType, pl.DataFrame], offsprings: tuple[SolutionType, pl.DataFrame]
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
        if self.constraints_symbols is not None:
            raise NotImplementedError("IBEA selector does not support constraints. Please use a different selector.")
        if isinstance(parents[0], pl.DataFrame) and isinstance(offsprings[0], pl.DataFrame):
            solutions = parents[0].vstack(offsprings[0])
        elif isinstance(parents[0], list) and isinstance(offsprings[0], list):
            solutions = parents[0] + offsprings[0]
        else:
            raise TypeError("The decision variables must be either a list or a polars DataFrame, not both")
        if len(parents[0]) < self.population_size:
            return parents[0], parents[1]
        alltargets = parents[1].vstack(offsprings[1])

        # Adaptation
        target_vals = alltargets[self.target_symbols].to_numpy()
        target_min = np.min(target_vals, axis=0)
        target_max = np.max(target_vals, axis=0)
        # Scale the targets to the range [0, 1]
        target_vals = (target_vals - target_min) / (target_max - target_min)
        fitness_components = self.binary_indicator(target_vals)
        kappa_mult = np.max(np.abs(fitness_components))

        chosen = _ibea_select_all(
            fitness_components, population_size=self.population_size, kappa=kappa_mult * self.kappa
        )
        self.selected_individuals = solutions.filter(chosen)
        self.selected_targets = alltargets.filter(chosen)
        self.selection = chosen

        fitness_components = fitness_components[chosen][:, chosen]
        self.fitness = _ibea_fitness(fitness_components, kappa=self.kappa * np.abs(fitness_components).max())

        self.notify()
        return self.selected_individuals, self.selected_targets

    def state(self) -> Sequence[Message]:
        """Return the state of the selector."""
        if self.verbosity == 0 or self.selection is None or self.selected_targets is None:
            return []
        if self.verbosity == 1:
            return [
                DictMessage(
                    topic=SelectorMessageTopics.STATE,
                    value={
                        "population_size": self.population_size,
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
                    "population_size": self.population_size,
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
        pass
