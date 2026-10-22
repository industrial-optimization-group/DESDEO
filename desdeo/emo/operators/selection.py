"""The base class for selection operators.

Some operators should be rewritten.
TODO:@light-weaver
"""

import warnings
from abc import abstractmethod
from collections.abc import Callable, Sequence
from enum import StrEnum
from itertools import combinations
from typing import Literal, TypeVar

import numpy as np
import polars as pl
from moocore import hv_contributions
from numba import njit
from pydantic import BaseModel, ConfigDict, Field
from scipy.linalg import LinAlgWarning, lu_factor, lu_solve
from scipy.spatial.distance import cdist
from scipy.special import comb
from scipy.stats.qmc import LatinHypercube

from desdeo.problem import Problem
from desdeo.tools import get_corrected_ideal_and_nadir
from desdeo.tools.indicators_binary import self_epsilon
from desdeo.tools.indicators_unary import hv
from desdeo.tools.message import (
    Array2DMessage,
    DictMessage,
    Message,
    NumpyArrayMessage,
    PolarsDataFrameMessage,
    SelectorMessageTopics,
    TerminatorMessageTopics,
)
from desdeo.tools.non_dominated_sorting import (
    constrained_fronts,
    dominance_matrix,
    fast_non_dominated_sort,
    fast_non_dominated_sort_indices,
)
from desdeo.tools.patterns import Publisher, Subscriber
from desdeo.tools.reference_vectors import create_s_energy

SolutionType = TypeVar("SolutionType", list, pl.DataFrame)


def total_constraint_violation(outputs: pl.DataFrame, constraint_symbols: Sequence[str] | None) -> np.ndarray | None:
    """Sum each solution's constraint violations, following DESDEO's positive-means-violated convention.

    Args:
        outputs (pl.DataFrame): The objective values, targets, and constraint values of a population.
        constraint_symbols (Sequence[str] | None): The constraint columns to read, or None for an
            unconstrained problem.

    Returns:
        np.ndarray | None: A 1-D array of total violations, one per row, zero where feasible. None if
            the problem has no constraints, which lets callers keep the unconstrained code path.
    """
    if not constraint_symbols:
        return None
    values = outputs[list(constraint_symbols)].to_numpy()
    return np.maximum(values, 0.0).sum(axis=1)


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

    If set to "simplex", the reference vectors are created using the simplex lattice design method.
    This method is generates distributions with specific numbers of reference vectors.
    Check: https://www.itl.nist.gov/div898/handbook/pri/section5/pri542.htm for more information.
    If set to "s_energy", the reference vectors are created using the Riesz s-energy criterion. This method is used to
    distribute an arbitrary number of reference vectors in the objective space while minimizing the s-energy.
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
        """Initialize the base decomposition based selector.

        Args:
            problem (Problem): the problem being solved.
            reference_vector_options (ReferenceVectorOptions): options for creating and adapting the reference vectors.
            verbosity (int): the verbosity level of the operator.
            publisher (Publisher): the publisher used to communicate with other operators.
            invert_reference_vectors (bool, optional): whether to invert the reference vectors. Defaults to False.
            seed (int, optional): the random seed. Defaults to 0.
        """
        super().__init__(problem, verbosity=verbosity, publisher=publisher, seed=seed)
        self.reference_vector_options = reference_vector_options
        self.invert_reference_vectors = invert_reference_vectors
        self.reference_vectors: np.ndarray
        self.reference_vectors_initial: np.ndarray

        if self.reference_vector_options.creation_type == "s_energy":
            self._create_s_energy()
        else:
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
                norm_order=2 if self.reference_vector_options.vector_type == "spherical" else 1,
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

    def _create_s_energy(self):
        """Create the reference vectors by minimizing the Riesz s-energy.

        Unlike the simplex lattice, this honours `number_of_vectors` exactly, so the population size
        of a decomposition-based algorithm can be chosen freely rather than being rounded down to the
        nearest binomial count. `lattice_resolution` is not meaningful here and is left untouched.
        """
        vectors = create_s_energy(
            number_of_objectives=self.num_dims,
            number_of_vectors=self.reference_vector_options.number_of_vectors,
            seed=self.seed,
        )
        # `invert_reference_vectors` mirrors the simplex branch, where it exists for NSGA-III.
        self.reference_vectors = vectors if not self.invert_reference_vectors else 1 - vectors
        self.reference_vectors_initial = np.copy(self.reference_vectors)
        self._normalize_rvs()

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
        if not self.invert_reference_vectors:  # todo, this currently only exists for nsga3
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

    def interactive_adapt_2(self, z: np.ndarray, predefined_distance: float, norm_order: int) -> None:
        """Adapt reference vectors using information about non-preferred solution(s) from the Decision maker.

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
            norm_order (int): Order of the norm. Default is 2, i.e., Euclidian distance.
        """
        # calculate L1 norm of non-preferred solution(s)
        z = np.atleast_2d(z)
        norm = np.linalg.norm(z, ord=norm_order, axis=1).reshape(np.shape(z)[0], 1)

        # non-preferred solutions normalized
        v_c = np.divide(z, norm)

        # distances from non-preferred solution(s) to each reference vector
        distances = np.array(
            [[np.linalg.norm(solution - value, ord=2) for solution in v_c] for value in self.reference_vectors]
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
        """Adapt reference vectors using the Decision maker's preferred range for each objective.

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
        # A reference vector with no associated solution leaves select at -1. Guarding here is
        # essential: selection[-1] = True would silently promote the *last* individual in the array,
        # once per empty vector. Empty vectors are common, and become commoner as the number of
        # objectives grows, so the unguarded write biases selection exactly where RVEA is used most.
        if select != -1:
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
        elif select_violation != -1:
            # Guarding this branch matters as much as the one above: a reference vector with no
            # associated solution at all leaves both indices at -1, and selection[-1] = True would
            # silently promote the last individual in the array, once per empty vector.
            selection[select_violation] = True

    return selection, apd_fitness


class RVEASelector(BaseDecompositionSelector):
    """Reference Vector Guided Evolutionary Algorithm (RVEA) selection operator."""

    @property
    def provided_topics(self):
        """The message topics this operator publishes, keyed by verbosity level."""
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
        """The message topics this operator subscribes to."""
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
        """Initialize the RVEA selection operator. See the class and base class for argument details."""
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
                stacklevel=3,
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
        # Which adaptation epoch was last acted on under an evaluation budget.
        self._adaptation_epoch = 0
        # Whether the ideal so far was taken over infeasible members only, for
        # want of any feasible one. Such an ideal can be better than any
        # feasible design can reach, so it is replaced, not minimised into,
        # the moment a feasible member appears.
        self._ideal_is_provisional = False
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
            # The ideal is tracked over feasible members only. A generation may have
            # none, at the start on a tightly constrained problem or later once the
            # population has contracted, and a minimum over nothing raises. Keep the
            # previous ideal in that case, as the nadir below already does. With no
            # ideal yet, take a provisional one over every member. The ideal of
            # infeasible members can be far better than any feasible design, and
            # minimising into it would carry that error through every later
            # generation, so the provisional ideal is replaced outright by the
            # first feasible one, and only then minimised into as usual.
            if feasible.any():
                feasible_ideal = np.min(targets[feasible], axis=0)
                if self.ideal is None or self._ideal_is_provisional:
                    self.ideal = feasible_ideal
                    self._ideal_is_provisional = False
                else:
                    self.ideal = np.min(np.vstack((self.ideal, feasible_ideal)), axis=0)
            elif self.ideal is None or self._ideal_is_provisional:
                self.ideal = np.min(targets, axis=0)
                self._ideal_is_provisional = True
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
                # The adaptation frequency is stated in generations. Under an
                # evaluation budget one generation is about one population of
                # evaluations, so adapt each time the count crosses that many
                # evaluations times the frequency, as the generation-based
                # branch adapts every frequency generations.
                frequency = self.reference_vector_options.adaptation_frequency
                if frequency > 0:
                    every = frequency * max(int(self.reference_vector_options.number_of_vectors or 1), 1)
                    epoch = self.numerator // every
                    if epoch > self._adaptation_epoch:
                        self._adaptation_epoch = epoch
                        self._adapt()
            if message.topic == TerminatorMessageTopics.MAX_EVALUATIONS:
                self.denominator = message.value
        return

    def state(self) -> Sequence[Message]:
        """Return the operator's state as messages for the current verbosity level."""
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
                value=self.selected_individuals.hstack(self.selected_targets),
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
        """The message topics this operator publishes, keyed by verbosity level."""
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
        """The message topics this operator subscribes to."""
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
            reference_vector_options (ReferenceVectorOptions | None, optional): Reference vector options.
                Defaults to None.
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

        self.adapted_reference_vectors = None
        self.worst_fitness: np.ndarray | None = None
        self.extreme_points: np.ndarray | None = None
        self.n_survive = self.reference_vectors.shape[0]
        self.selection: list[int] | None = None
        self.selected_individuals: SolutionType | None = None
        self.selected_targets: pl.DataFrame | None = None

    def do(  # NOQA: C901
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

        # Check if there are constraints and filter feasible solutions
        if self.constraints_symbols is not None and len(self.constraints_symbols) > 0:
            constraints = alltargets[self.constraints_symbols].to_numpy()
            constraints = np.where(constraints > 0, constraints, 0)
            constraints_sum = np.sum(constraints, axis=1)
            feasible = np.where(constraints_sum == 0)[0].tolist()
            sorted_infeasible = constraints_sum.argsort().tolist()[len(feasible) :]
            if len(feasible) <= self.n_survive:
                # Put all feasible solutions in the selection, then fill the rest with the least constraint violation
                select = feasible.copy()
                remaining = self.n_survive - len(select)
                select += sorted_infeasible[:remaining]
                self.selection = select
                if isinstance(solutions, pl.DataFrame) and self.selection is not None:
                    self.selected_individuals = solutions[self.selection]
                elif isinstance(solutions, list) and self.selection is not None:
                    self.selected_individuals = [solutions[i] for i in self.selection]
                else:
                    raise RuntimeError("Something went wrong with the selection")
                self.selected_targets = alltargets[self.selection]

                self.notify()
                return self.selected_individuals, self.selected_targets
            # else:
            # Only consider feasible solutions for selection
            if isinstance(solutions, pl.DataFrame):
                solutions = solutions[feasible]
            elif isinstance(solutions, list):
                solutions = [solutions[i] for i in feasible]
            alltargets = alltargets[feasible]

        targets = alltargets[self.target_symbols].to_numpy()
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
            fronts = fronts[: front_id + 1]
            selection = np.concatenate(fronts)
            break
        else:
            # The combined population is smaller than the desired number of survivors
            # (this happens, e.g., when preferred solutions inflate the number of
            # reference vectors beyond the population size). Keep all available solutions.
            if fronts:
                selection = np.concatenate(fronts)
        front_fitness = fitness[selection]

        last_front = fronts[-1]

        # Selecting individuals from the last acceptable front.
        if len(selection) > self.n_survive:
            niche_of_individuals, dist_to_niche = self.associate_to_niches(
                front_fitness, ref_dirs, self.ideal, nadir_point
            )
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
            selected_from_last_front = self.niching(
                fitness[last_front, :],
                n_remaining,
                niche_count,
                niche_of_individuals[last_front_selection_id],
                dist_to_niche[last_front_selection_id],
            )
            final_selection = np.concatenate((until_last_front, last_front[selected_from_last_front]))
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

    def get_extreme_points_c(self, f, ideal_point, extreme_points=None):
        """Find the extreme points used for normalization (adapted from pymoo)."""
        # calculate the asf which is used for the extreme point decomposition
        asf = np.eye(f.shape[1])
        asf[asf == 0] = 1e6

        # add the old extreme points to never loose them for normalization
        all_f = f
        if extreme_points is not None:
            all_f = np.concatenate([extreme_points, all_f], axis=0)

        # translate so that small values are substituted to 0
        near_zero_tolerance = 1e-3
        translated_f = all_f - ideal_point
        translated_f[translated_f < near_zero_tolerance] = 0

        # update the extreme points for the normalization having the highest asf value each
        f_asf = np.max(translated_f * asf[:, None, :], axis=2)
        min_idx = np.argmin(f_asf, axis=1)
        return all_f[min_idx, :]

    def get_nadir_point(
        self,
        extreme_points,
        ideal_point,
        worst_point,
        worst_of_front,
        worst_of_population,
    ):
        """Estimate the nadir point from the extreme points (adapted from pymoo)."""
        degenerate_tolerance = 1e-6
        try:
            # find the intercepts using gaussian elimination
            coeff_matrix = extreme_points - ideal_point
            b = np.ones(extreme_points.shape[1])
            plane = np.linalg.solve(coeff_matrix, b)
            intercepts = 1 / plane

            nadir_point = ideal_point + intercepts

            if (
                not np.allclose(np.dot(coeff_matrix, plane), b)
                or np.any(intercepts <= degenerate_tolerance)
                or np.any(nadir_point > worst_point)
            ):
                raise np.linalg.LinAlgError  # noqa: TRY301

        except np.linalg.LinAlgError:
            nadir_point = worst_of_front

        b = nadir_point - ideal_point <= degenerate_tolerance
        nadir_point[b] = worst_of_population[b]
        return nadir_point

    def niching(self, f, n_remaining, niche_count, niche_of_individuals, dist_to_niche):
        """Select survivors from the last front by reference-vector niching (adapted from pymoo)."""
        survivors = []

        # boolean array of elements that are considered for each iteration
        mask = np.full(f.shape[0], fill_value=True)

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

            # if the niche is empty, take the closest individual; otherwise take a random one (already shuffled)
            next_ind = next_ind[np.argmin(dist_to_niche[next_ind])] if niche_count[next_niche] == 0 else next_ind[0]

            mask[next_ind] = False
            survivors.append(int(next_ind))

            niche_count[next_niche] += 1

        return survivors

    def associate_to_niches(self, f, ref_dirs, ideal_point, nadir_point, utopian_epsilon=0.0):
        """Associate each solution with its closest reference vector (adapted from pymoo)."""
        utopian_point = ideal_point - utopian_epsilon

        denom = nadir_point - utopian_point
        denom[denom == 0] = 1e-12

        # normalize by ideal point and intercepts
        normalized = (f - utopian_point) / denom
        dist_matrix = jitted_calc_perpendicular_distance(normalized, ref_dirs, self.invert_reference_vectors)

        niche_of_individuals = np.argmin(dist_matrix, axis=1)
        dist_to_niche = dist_matrix[np.arange(f.shape[0]), niche_of_individuals]

        return niche_of_individuals, dist_to_niche

    def calc_niche_count(self, n_niches, niche_of_individuals):
        """Count how many of the given individuals are assigned to each niche."""
        niche_count = np.zeros(n_niches, dtype=int)
        index, count = np.unique(niche_of_individuals, return_counts=True)
        niche_count[index] = count
        return niche_count

    def calc_perpendicular_distance(self, normalized, ref_dirs):
        """Compute the perpendicular distance from each normalized solution to each reference direction."""
        if self.invert_reference_vectors:
            u = np.tile(-ref_dirs, (len(normalized), 1))
            v = np.repeat(1 - normalized, len(ref_dirs), axis=0)
        else:
            u = np.tile(ref_dirs, (len(normalized), 1))
            v = np.repeat(normalized, len(ref_dirs), axis=0)

        norm_u = np.linalg.norm(u, axis=1)

        scalar_proj = np.sum(v * u, axis=1) / norm_u
        proj = scalar_proj[:, None] * u / norm_u[:, None]
        val = np.linalg.norm(proj - v, axis=1)
        return np.reshape(val, (len(normalized), len(ref_dirs)))

    def state(self) -> Sequence[Message]:
        """Return the operator's state as messages for the current verbosity level."""
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
                value=self.selected_individuals.hstack(self.selected_targets),
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

    def update(self, message: Message) -> None:
        """Handle an incoming message. This operator does not react to messages."""


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


class _FitnessPublishingSelector(BaseSelector):
    """Shared state publishing for selectors that feed a mating tournament through SELECTED_FITNESS."""

    @property
    def provided_topics(self):
        """The message topics this operator publishes, keyed by verbosity level."""
        return {
            0: [],
            1: [SelectorMessageTopics.STATE],
            2: [SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS, SelectorMessageTopics.SELECTED_FITNESS],
        }

    @property
    def interested_topics(self):
        """The message topics this operator subscribes to."""
        return []

    def __init__(self, problem: Problem, verbosity: int, publisher: Publisher, population_size: int, seed: int = 0):
        """Initialize the selector.

        Args:
            problem (Problem): The optimization problem to be solved.
            verbosity (int): The verbosity level of the operator.
            publisher (Publisher): The publisher to use for communication.
            population_size (int): The number of solutions selected each generation.
            seed (int, optional): The random seed to use. Defaults to 0.
        """
        super().__init__(problem=problem, verbosity=verbosity, publisher=publisher, seed=seed)
        if population_size < 1:
            raise ValueError("population_size must be positive.")
        self.population_size = population_size
        self.selection: list[int] | None = None
        self.selected_individuals: SolutionType | None = None
        self.selected_targets: pl.DataFrame | None = None
        self.fitness: np.ndarray | None = None

    def _merge(
        self, parents: tuple[SolutionType, pl.DataFrame], offsprings: tuple[SolutionType, pl.DataFrame]
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        if not isinstance(parents[0], pl.DataFrame):
            raise TypeError(f"{self.__class__.__name__} works on polars DataFrames only.")
        if offsprings[1].is_empty():
            return parents[0], parents[1]
        return parents[0].vstack(offsprings[0]), parents[1].vstack(offsprings[1])

    def _finish(self, solutions: pl.DataFrame, outputs: pl.DataFrame, chosen: list[int], fitness: np.ndarray):
        self.selection = chosen
        self.selected_individuals = solutions[chosen]
        self.selected_targets = outputs[chosen]
        self.fitness = fitness
        self.notify()
        return self.selected_individuals, self.selected_targets

    def state(self) -> Sequence[Message]:
        """Return the operator's state as messages for the current verbosity level."""
        if self.verbosity == 0 or self.selection is None or self.selected_targets is None:
            return []
        state = DictMessage(
            topic=SelectorMessageTopics.STATE,
            value={"population_size": self.population_size, "selected_individuals": self.selection},
            source=self.__class__.__name__,
        )
        if self.verbosity == 1:
            return [state]
        return [
            state,
            PolarsDataFrameMessage(
                topic=SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
                value=self.selected_individuals.hstack(self.selected_targets),
                source=self.__class__.__name__,
            ),
            NumpyArrayMessage(
                topic=SelectorMessageTopics.SELECTED_FITNESS,
                value=self.fitness,
                source=self.__class__.__name__,
            ),
        ]

    def update(self, message: Message) -> None:
        """Handle an incoming message. This operator does not react to messages."""


class IBEASelector(_FitnessPublishingSelector):
    """The adaptive IBEA selection operator.

    Constraints are handled feasibility-first, as in `NSGA3Selector`: while feasible solutions alone
    can fill the population the infeasible ones are discarded and the indicator selection runs
    unchanged, and while they cannot, every feasible solution survives and the remaining places go to
    the least infeasible. The binary indicator itself is left untouched, since it compares objective
    vectors and has no reading of an infeasible one.

    Reference: Zitzler, E., Künzli, S. (2004). Indicator-Based Selection in Multiobjective Search. In: Yao, X., et al.
    Parallel Problem Solving from Nature - PPSN VIII. PPSN 2004. Lecture Notes in Computer Science, vol 3242.
    Springer, Berlin, Heidelberg. https://doi.org/10.1007/978-3-540-30217-9_84
    """

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
            seed (int, optional): The random seed to use. Defaults to 0.
        """
        # TODO(@light-weaver): IBEA doesn't perform as good as expected
        # The distribution of solutions found isn't very uniform
        # Update 21st August, tested against jmetalpy IBEA. Our version is both faster and better
        # What is happening???
        # Results are similar to this https://github.com/Xavier-MaYiMing/IBEA/
        super().__init__(
            problem=problem, verbosity=verbosity, publisher=publisher, population_size=population_size, seed=seed
        )
        self.binary_indicator = binary_indicator
        self.kappa = kappa

    def _indicator_components(self, targets: np.ndarray) -> np.ndarray:
        """Scale the targets to the unit box and return the pairwise binary indicator matrix."""
        target_min = np.min(targets, axis=0)
        target_max = np.max(targets, axis=0)
        span = target_max - target_min
        # A target that is constant across the population carries no information; dividing by its
        # zero span would turn the whole indicator matrix into NaN.
        span[span == 0] = 1.0
        return self.binary_indicator((targets - target_min) / span)

    def _adaptive_kappa(self, components: np.ndarray) -> float:
        """Adaptive IBEA's kappa: the configured kappa scaled by the largest indicator magnitude.

        The scaling makes kappa independent of the objectives' range. When the set has collapsed onto a
        single objective vector every indicator value is zero, and so is the scale: dividing by it
        raised ZeroDivisionError in the fitness kernels and would turn the vectorised survivor
        selection into NaN. A set with no spread has nothing to scale, so the configured kappa is used
        unscaled. Every exp(-0 / kappa) is then 1 and each member's fitness is -(n - 1), a tie, which is
        the honest reading of a set the indicator cannot separate. Wherever the scale is positive the
        value is exactly what it was before.
        """
        scale = float(np.abs(components).max())
        return self.kappa * scale if scale > 0 else self.kappa

    def _infeasible_fitness(self, targets: np.ndarray, violations: np.ndarray) -> np.ndarray:
        """Fitness for a set that is partly or wholly infeasible, feasible solutions first.

        The binary indicator only orders solutions sensibly when they are all feasible, so the
        indicator fitness is kept for the feasible members and every infeasible member is placed
        strictly below all of them, ordered among themselves by total violation. Fitness stays
        higher-is-better, which is what the mating tournament expects.
        """
        components = self._indicator_components(targets)
        fitness = _ibea_fitness(components, kappa=self._adaptive_kappa(components))

        infeasible = violations > 0
        if not np.any(infeasible):
            return fitness
        feasible_worst = fitness[~infeasible].min() if np.any(~infeasible) else 0.0
        fitness[infeasible] = feasible_worst - violations[infeasible] / violations[infeasible].max()
        return fitness

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
        if len(parents[0]) < self.population_size:
            return parents[0], parents[1]
        solutions, outputs = self._merge(parents, offsprings)
        targets = outputs[self.target_symbols].to_numpy()

        violations = total_constraint_violation(outputs, self.constraints_symbols)
        if violations is None:
            candidates = np.arange(len(outputs))
        else:
            candidates = np.flatnonzero(violations <= 0)
            if len(candidates) <= self.population_size:
                # Too few feasible solutions to fill the population, so the indicator has nothing to
                # choose between: keep every feasible solution and top up with the least infeasible.
                chosen = np.argsort(violations, kind="stable")[: self.population_size]
                fitness = self._infeasible_fitness(targets[chosen], violations[chosen])
                return self._finish(solutions, outputs, chosen.tolist(), fitness)
            # Enough feasible solutions to fill the population, so the infeasible ones are simply
            # dropped and the indicator selection proceeds unchanged on the feasible ones.

        # Adaptation
        components = self._indicator_components(targets[candidates])
        survivors = _ibea_select_all(
            components, population_size=self.population_size, kappa=self._adaptive_kappa(components)
        )
        components = components[survivors][:, survivors]
        fitness = _ibea_fitness(components, kappa=self._adaptive_kappa(components))
        return self._finish(solutions, outputs, candidates[survivors].tolist(), fitness)


@njit
def _nsga2_crowding_distance_assignment(
    non_dominated_front: np.ndarray, f_mins: np.ndarray, f_maxs: np.ndarray
) -> np.ndarray:
    """Computes the crowding distance as pecified in the definition of NSGA2.

    This function computed the crowding distances for a non-dominated set of solutions.
    A smaller value means that a solution is more crowded (worse), while a larger value means
    it is less crowded (better).

    Note:
        The boundary point in `non_dominated_front` will be assigned a non-crowding
            distance value of `np.inf` indicating, that they shouls always be included
            in later sorting.

    Args:
        non_dominated_front (np.ndarray): a 2D numpy array (size n x m = number
            of vectors x number of targets (obejctive funcitons)) containing
            mutually non-dominated vectors. The values of the vectors correspond to
            the optimization 'target' (usually the minimized objective function
            values.)
        f_mins (np.ndarray): a 1D numpy array of size m containing the minimum objective function
            values in `non_dominated_front`.
        f_maxs (np.ndarray): a 1D numpy array of size m containing the maximum objective function
            values in `non_dominated_front`.

    Returns:
        np.ndarray: a numpy array of size m containing the crowding distances for each vector
            in `non_dominated_front`.

    Reference: Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. A. M. T.
        (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE
        transactions on evolutionary computation, 6(2), 182-197.
    """
    vectors = non_dominated_front  # I
    num_vectors = vectors.shape[0]  # l
    num_objectives = vectors.shape[1]

    crowding_distances = np.zeros(num_vectors)  # I[i]_distance

    for m in range(num_objectives):
        # An objective that is constant across the whole population separates nothing. Sorting by it
        # gives an arbitrary order, so marking its two ends as boundary points would hand an infinite
        # distance to two arbitrary solutions, and the normalisation below would divide by zero.
        if f_maxs[m] == f_mins[m]:
            continue

        # sort by column (objective)
        m_order = vectors[:, m].argsort()
        # inlcude boundary points
        crowding_distances[m_order[0]], crowding_distances[m_order[-1]] = np.inf, np.inf

        for i in range(1, num_vectors - 1):
            crowding_distances[m_order[i]] = crowding_distances[m_order[i]] + (
                vectors[m_order[i + 1], m] - vectors[m_order[i - 1], m]
            ) / (f_maxs[m] - f_mins[m])

    return crowding_distances


class NSGA2Selector(_FitnessPublishingSelector):
    """Implements the selection operator defined for NSGA2.

    Implements the selection operator defined for NSGA2, which included the crowding
    distance calculation.

    On a constrained problem the ranking switches to the constrained domination of the same paper:
    a feasible solution beats an infeasible one, two infeasible solutions are compared by total
    constraint violation, and two feasible solutions are compared by ordinary Pareto dominance.
    Nothing else changes, since that is where NSGA-II confines its constraint handling.

    Reference: Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. A. M. T.
        (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE
        transactions on evolutionary computation, 6(2), 182-197.
    """

    def _sort(self, targets: np.ndarray, violations: np.ndarray | None) -> np.ndarray:
        """Rank a population into fronts, applying constrained domination when the problem has constraints.

        Everything downstream -- crowding distance, the partial-front trim, the fitness -- is left
        alone, exactly as in NSGA-II, where constraint handling enters only through the ranking.
        See `constrained_fronts`.
        """
        return constrained_fronts(targets, violations)

    def do(
        self, parents: tuple[SolutionType, pl.DataFrame], offsprings: tuple[SolutionType, pl.DataFrame]
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Perform the selection operation."""
        # First iteration, offspring is empty
        # Do basic binary tournament selection, recombination, and mutation
        # In practice, just compute the non-dom ranks and provide them as fitness

        # Off-spring empty (first iteration, compute only non-dominated ranks and provide them as fitness)
        if offsprings[0].is_empty() and offsprings[1].is_empty():
            # just compute non-dominated ranks of population and be done
            parents_a = parents[1][self.target_symbols].to_numpy()
            fronts = self._sort(parents_a, total_constraint_violation(parents[1], self.constraints_symbols))

            # assign fitness according to non-dom rank, flipped to higher-is-better and kept
            # strictly positive for the consumers of SELECTED_FITNESS; see the main branch below
            scores = np.arange(len(fronts))
            self.fitness = len(fronts) - scores @ fronts

            # all selected in first iteration
            self.selection = list(range(len(parents[1])))
            self.selected_individuals = parents[0]
            self.selected_targets = parents[1]

            self.notify()

            return self.selected_individuals, self.selected_targets

        # #Actual selection operator for NSGA2

        # Combine parent and offspring R_t = P_t U Q_t
        r_solutions = parents[0].vstack(offsprings[0])
        r_population = parents[1].vstack(offsprings[1])
        r_targets_arr = r_population[self.target_symbols].to_numpy()

        # the minimum and maximum target values in the whole current population
        f_mins, f_maxs = np.min(r_targets_arr, axis=0), np.max(r_targets_arr, axis=0)

        # Do fast non-dominated sorting on R_t -> F
        fronts = self._sort(r_targets_arr, total_constraint_violation(r_population, self.constraints_symbols))
        crowding_distances = np.ones(self.population_size) * np.nan
        rankings = np.ones(self.population_size) * np.nan
        fitness_values = np.ones(self.population_size) * np.nan

        # Set the new parent population to P_t+1 = empty and i=1
        new_parents = np.ones((self.population_size, parents[1].shape[1])) * np.nan
        new_parents_solutions = np.ones((self.population_size, parents[0].shape[1])) * np.nan
        parents_ptr = 0  # keep track where stuff was last added

        # the -1 is here because searchsorted returns the index where we can insert the population size to preserve the
        # order, hence, the previous index of this will be the last element in the cumsum that is less than
        # the population size
        last_whole_front_idx = (
            np.searchsorted(np.cumsum(np.sum(fronts, axis=1)), self.population_size, side="right") - 1
        )

        last_ranking = 0  # in case first front is larger th population size
        for i in range(last_whole_front_idx + 1):  # inclusive
            # The looped front here will result in a new population with size <= 100.

            # Compute the crowding distances for F_i
            distances = _nsga2_crowding_distance_assignment(r_targets_arr[fronts[i]], f_mins, f_maxs)
            crowding_distances[parents_ptr : parents_ptr + distances.shape[0]] = (
                distances  # distances will have same number of elements as in front[i]
            )

            # keep track of the rankings as well (best = 0, larger worse). First
            # non-dom front will have a rank fitness of 0.
            rankings[parents_ptr : parents_ptr + distances.shape[0]] = i

            #   P_t+1 = P_t+1 U F_i
            new_parents[parents_ptr : parents_ptr + distances.shape[0]] = r_population.filter(fronts[i])
            new_parents_solutions[parents_ptr : parents_ptr + distances.shape[0]] = r_solutions.filter(fronts[i])

            # compute fitness
            # infs are checked since boundary points are assigned this value when computing the crowding distance
            finite_distances = distances[distances != np.inf]
            max_no_inf = np.nanmax(finite_distances) if finite_distances.size > 0 else np.ones(fronts[i].sum())
            distances_no_inf = np.nan_to_num(distances, posinf=max_no_inf * 1.1)

            # Distances for the current front normalized between 0 and 1.
            # The small scalar we add in the nominator and denominator is to
            # ensure that no distance value would result in exactly 0 after
            # normalizing, which would increase the corresponding solution
            # ranking, once reversed, which we do not want to.
            normalized_distances = (distances_no_inf - (distances_no_inf.min() - 1e-6)) / (
                distances_no_inf.max() - (distances_no_inf.min() - 1e-6)
            )

            # since higher is better for the crowded distance, we substract the normalized distances from 1 so that
            # lower is better, which allows us to combine them with the ranking
            # No value here should be 1.0 or greater.
            reversed_distances = 1.0 - normalized_distances

            front_fitness = reversed_distances + rankings[parents_ptr : parents_ptr + distances.shape[0]]
            fitness_values[parents_ptr : parents_ptr + distances.shape[0]] = front_fitness

            # increment parent pointer
            parents_ptr += distances.shape[0]

            # keep track of last given rank
            last_ranking = i

        # deal with last (partial) front, if needed
        trimmed_and_sorted_indices = None
        if parents_ptr < self.population_size:
            distances = _nsga2_crowding_distance_assignment(
                r_targets_arr[fronts[last_whole_front_idx + 1]], f_mins, f_maxs
            )

            # Sort F_i in descending order according to crowding distance
            # This makes picking the selected part of the partial front easier
            trimmed_and_sorted_indices = distances.argsort()[::-1][: self.population_size - parents_ptr]

            crowding_distances[parents_ptr : self.population_size] = distances[trimmed_and_sorted_indices]
            rankings[parents_ptr : self.population_size] = last_ranking + 1

            # P_t+1 = P_t+1 U F_i[1: (N - |P_t+1|)]
            new_parents[parents_ptr : self.population_size] = r_population.filter(fronts[last_whole_front_idx + 1])[
                trimmed_and_sorted_indices
            ]
            new_parents_solutions[parents_ptr : self.population_size] = r_solutions.filter(
                fronts[last_whole_front_idx + 1]
            )[trimmed_and_sorted_indices]

            # compute fitness (see above for details)
            finite_distances = distances[trimmed_and_sorted_indices][distances[trimmed_and_sorted_indices] != np.inf]
            max_no_inf = (
                np.nanmax(finite_distances)
                if finite_distances.size > 0
                else np.ones(len(trimmed_and_sorted_indices))  # we have only boundary points
            )
            distances_no_inf = np.nan_to_num(distances[trimmed_and_sorted_indices], posinf=max_no_inf * 1.1)

            normalized_distances = (distances_no_inf - (distances_no_inf.min() - 1e-6)) / (
                distances_no_inf.max() - (distances_no_inf.min() - 1e-6)
            )

            reversed_distances = 1.0 - normalized_distances

            front_fitness = reversed_distances + rankings[parents_ptr : self.population_size]
            fitness_values[parents_ptr : parents_ptr + self.population_size] = front_fitness

        # back to polars, return values
        solutions = pl.DataFrame(new_parents_solutions, schema=parents[0].schema)
        outputs = pl.DataFrame(new_parents, schema=parents[1].schema)

        # Everything downstream of SELECTED_FITNESS reads it as higher-is-better: the mating
        # tournament takes an argmax, and roulette-wheel selection treats it as a weight, which also
        # requires it to be positive. The NSGA-II quantity built above is the opposite -- front rank
        # plus a reversed crowding distance, lower is better -- so publishing it directly made the
        # binary tournament pick the loser of every pair. Reflecting it about the worst attainable
        # value flips the direction, keeps every value strictly positive (a front's fitness lies in
        # `(n_fronts - rank - 1, n_fronts - rank]`, since the reversed distance never reaches 1) and
        # preserves the ordering exactly.
        self.fitness = (np.nanmax(rankings) + 1.0) - fitness_values

        whole_fronts = fronts[: last_whole_front_idx + 1]
        whole_indices = [np.where(row)[0].tolist() for row in whole_fronts]

        if trimmed_and_sorted_indices is not None:
            # partial front considered
            partial_front = fronts[last_whole_front_idx + 1]
            partial_indices = np.where(partial_front)[0][trimmed_and_sorted_indices].tolist()
        else:
            partial_indices = []

        self.selection = [index for indices in whole_indices for index in indices] + partial_indices
        self.selected_individuals = solutions
        self.selected_targets = outputs

        self.notify()
        return solutions, outputs


class SMSEMOASelector(BaseSelector):
    """Implements the selection operator defined for SMSEMOA.

    Implements the selection operator defined for SMSEMOA, which included the hypervolume
    contribution calculation.

    Beume, N., Naujoks, B., & Emmerich, M. (2007). SMS-EMOA: Multiobjective selection based on dominated hypervolume.
    European Journal of Operational Research, 181(3), 1653-1669. https://doi.org/10.1016/j.ejor.2006.08.008
    """

    @property
    def provided_topics(self):
        """The message topics this operator publishes, keyed by verbosity level."""
        return {
            0: [],
            1: [SelectorMessageTopics.STATE],
            2: [
                SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
                SelectorMessageTopics.STATE,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics this operator subscribes to."""
        return []

    def __init__(
        self,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        normalised_reference_point_component: float,
        seed: int = 0,
    ):
        """Initialize the SMS-EMOA selection operator.

        Args:
            problem (Problem): The optimization problem to be solved.
            verbosity (int): The verbosity level of the operator.
            publisher (Publisher): The publisher to use for communication.
            normalised_reference_point_component (float, optional): The reference point component used for hypervolume
                calculation. The solutions are normalized to the range [0, 1] and the reference point is set to
                a vector of ones multiplied by this component.
            seed (int, optional): The random seed to use. Defaults to 0.
        """
        super().__init__(
            problem,
            verbosity=verbosity,
            publisher=publisher,
            seed=seed,
        )
        self.selection: list[int] | None = None
        self.selected_individuals: SolutionType | None = None
        self.selected_targets: pl.DataFrame | None = None
        if normalised_reference_point_component < 1:
            raise ValueError("The reference point component must be greater than or equal to 1.")
        self.reference_point_component = normalised_reference_point_component
        self.removed: int = 0

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

        if self.constraints_symbols is None or len(self.constraints_symbols) == 0:
            # No constraints, use SMS-EMOA selection
            self.removed = self._sms_emoa_selection(alltargets[self.target_symbols].to_numpy())
        elif not (alltargets.select(self.constraints_symbols) > 0).to_numpy().any():
            # All offsprings are feasible
            self.removed = self._sms_emoa_selection(alltargets[self.target_symbols].to_numpy())
        else:
            # Some offsprings are infeasible. Remove the most infeasible offspring.
            violations = (
                alltargets[self.constraints_symbols].to_numpy(),
                alltargets.select(self.constraints_symbols).to_numpy(),
            )
            self.removed = int(np.argmax(np.sum(np.maximum(0, violations), axis=1)))

        self.selection = list(range(len(alltargets)))
        self.selection.remove(self.removed)
        if isinstance(solutions, pl.DataFrame) and self.selection is not None:
            self.selected_individuals = solutions[self.selection]
        elif isinstance(solutions, list) and self.selection is not None:
            self.selected_individuals = [solutions[i] for i in self.selection]
        else:
            raise RuntimeError("Something went wrong with the selection")

        self.selected_targets = alltargets[self.selection]
        self.notify()
        return self.selected_individuals, self.selected_targets

    def _sms_emoa_selection(self, targets: np.ndarray) -> int:
        """Perform the SMS-EMOA selection operation.

        Note that in the paper in Algorithm 2, the factor (totalHV - currentHV) is minimized. As totalHV is constant,
        this is equivalent to maximizing currentHV, which is what we do here.

        Args:
            targets (np.ndarray): The objective values of the individuals.

        Returns:
            int: The index of the individual to be removed.
        """
        fronts = fast_non_dominated_sort_indices(targets)
        last_front = fronts[-1]
        if len(last_front) == 1:
            return last_front[0]
        # last front has more than one individual, compute hypervolume contributions
        max_hv = -np.inf
        worst_index = -1
        targets = targets - np.min(targets, axis=0)  # shift to origin
        targets = targets / np.max(targets, axis=0)  # scale to [0, 1] (based on the whole population)
        # using moocore hv contribusions
        hv_contribs = hv_contributions(
            targets[last_front], ref=np.ones(targets.shape[1]) * self.reference_point_component
        )
        min_contrib_index = np.argmin(hv_contribs)
        return last_front[min_contrib_index]
        for i in last_front:
            remaining_front = [j for j in last_front if j != i]
            current_hv = hv(targets[remaining_front], reference_point_component=self.reference_point_component)
            if current_hv > max_hv:
                max_hv = current_hv
                worst_index = i
        return worst_index

    def update(self, message: Message) -> None:
        """Handle an incoming message. This operator does not react to messages."""

    def state(self) -> Sequence[Message]:
        """Return the operator's state as messages for the current verbosity level."""
        if self.verbosity == 0 or self.selection is None or self.selected_targets is None:
            return []
        if self.verbosity == 1:
            return [
                DictMessage(
                    topic=SelectorMessageTopics.STATE,
                    value={
                        "selection": self.selection,
                        "removed": self.removed,
                    },
                    source=self.__class__.__name__,
                )
            ]
        # verbosity == 2
        if isinstance(self.selected_individuals, pl.DataFrame):
            message = PolarsDataFrameMessage(
                topic=SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
                value=self.selected_individuals.hstack(self.selected_targets),
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
                    "selection": self.selection,
                    "removed": self.removed,
                },
                source=self.__class__.__name__,
            ),
            message,
        ]


def moead_scalarize(
    targets: np.ndarray,
    weights: np.ndarray,
    ideal: np.ndarray,
    method: Literal["tchebycheff", "pbi", "weighted_sum"],
    pbi_penalty: float = 5.0,
) -> np.ndarray:
    """Evaluate MOEA/D's aggregation functions, one weight vector per row of `targets`.

    All three are written for minimization, as in footnotes 3 and 6 of Zhang and Li (2007).

    - "tchebycheff": `max_k w_k |f_k - z_k|` (Eq. 3).
    - "pbi": `d1 + theta * d2` (Eq. 5), where `d1` is the length of the projection of `f - z` onto
      the weight vector and `d2` is the distance from `f` to the line through `z` along that vector.
      Eq. 5 writes the foot of the perpendicular as `z + d1 * w`, which is the projection only for a
      unit `w`. The weights here sum to one, so the geometric form shown in the paper's Fig. 2 is
      used, as PlatEMO and pymoo do.
    - "weighted_sum": `sum_k w_k f_k` (Eq. 2). The ideal point is not used.

    Args:
        targets (np.ndarray): objective vectors (minimized), shape `(n, m)`.
        weights (np.ndarray): the weight vector for each row, shape `(n, m)`.
        ideal (np.ndarray): the reference point `z`, shape `(m,)`.
        method (str): the aggregation function.
        pbi_penalty (float): the penalty `theta` of the PBI function.

    Returns:
        np.ndarray: the aggregation value of each row, lower is better.
    """
    if method == "tchebycheff":
        return np.max(weights * np.abs(targets - ideal), axis=1)
    if method == "weighted_sum":
        return np.sum(weights * targets, axis=1)
    if method == "pbi":
        translated = targets - ideal
        norm = np.linalg.norm(weights, axis=1)
        norm[norm == 0] = np.finfo(float).eps
        unit = weights / norm[:, None]
        d1 = np.abs(np.sum(translated * unit, axis=1))
        d2 = np.linalg.norm(translated - d1[:, None] * unit, axis=1)
        return d1 + pbi_penalty * d2
    raise ValueError(f"Unknown MOEA/D aggregation function: {method}")


class MOEADSelector(BaseDecompositionSelector):
    """The neighbourhood replacement of MOEA/D and MOEA/D-DE.

    MOEA/D keeps one solution per weight vector (subproblem). Each offspring is produced for one
    subproblem `i` from parents in its mating pool, and then replaces the current solution of every
    subproblem `j` in that pool whose aggregation value it matches or improves,
    `g(y | w_j, z) <= g(x_j | w_j, z)`. The pool is the neighbourhood `B(i)`, the `T` subproblems with
    the closest weight vectors, with probability `delta`, and the whole population otherwise. MOEA/D-DE
    visits the pool in random order and stops after `n_r` replacements, so that one good offspring
    cannot take over a whole neighbourhood. The original MOEA/D is `delta = 1` with no cap.

    Unlike the other selectors this one is driven one offspring at a time by
    [template_moead][desdeo.emo.methods.templates.template_moead]: the template asks for the mating
    pool of subproblem `i` with `mating_pool(i)`, evaluates one offspring, and passes it to `do`, which
    updates the pool `mating_pool` returned. The first call to `do`, with no offspring, takes the
    initial population, one solution per subproblem in order, and sets the ideal point from it. The
    selector publishes its state when the template calls `notify`, once per generation, rather than on
    every replacement.

    Neither paper handles constraints. On a constrained problem the replacement compares total
    constraint violation first, so a solution with a smaller violation always replaces one with a
    larger violation, and the aggregation value decides only between equal violations, which for an
    unconstrained problem is every comparison. This is DESDEO's addition.

    A preference (reference point, preferred or non-preferred solutions, preferred ranges) adapts the
    weight vectors as in the other decomposition selectors (Hakanen et al. 2016). Those adaptations
    treat a vector as a direction in objective space. PBI reads it that way, but a Tchebycheff
    subproblem's optimum lies along `1 / w`, so with a preference the Tchebycheff weights are the
    WS-transformation (Qi et al. 2014) of the adapted vectors. The weighted sum has no direction to
    adapt and rejects preferences.

    References:
        Zhang, Q., & Li, H. (2007). MOEA/D: A multiobjective evolutionary algorithm based on
            decomposition. IEEE Transactions on Evolutionary Computation, 11(6), 712-731.
            https://doi.org/10.1109/TEVC.2007.892759

        Li, H., & Zhang, Q. (2009). Multiobjective optimization problems with complicated Pareto
            sets, MOEA/D and NSGA-II. IEEE Transactions on Evolutionary Computation, 13(2), 284-302.
            https://doi.org/10.1109/TEVC.2008.925798

        Qi, Y., Ma, X., Liu, F., Jiao, L., Sun, J., & Wu, J. (2014). MOEA/D with adaptive weight
            adjustment. Evolutionary Computation, 22(2), 231-264. https://doi.org/10.1162/EVCO_a_00109
            (The WS-transformation used with preferences.)
    """

    @property
    def provided_topics(self):
        """The message topics this operator publishes, keyed by verbosity level."""
        return {
            0: [],
            1: [SelectorMessageTopics.STATE],
            2: [
                SelectorMessageTopics.REFERENCE_VECTORS,
                SelectorMessageTopics.STATE,
                SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
            ],
        }

    @property
    def interested_topics(self):
        """The message topics this operator subscribes to."""
        return []

    def __init__(
        self,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        reference_vector_options: ReferenceVectorOptions | dict | None = None,
        neighbourhood_size: int = 20,
        neighbourhood_probability: float = 1.0,
        max_replacements: int | None = None,
        aggregation: Literal["tchebycheff", "pbi", "weighted_sum"] = "tchebycheff",
        pbi_penalty: float = 5.0,
        seed: int = 0,
    ):
        """Initialize the MOEA/D selector.

        Args:
            problem (Problem): The optimization problem to be solved.
            verbosity (int): The verbosity level of the operator.
            publisher (Publisher): The publisher to use for communication.
            reference_vector_options (ReferenceVectorOptions | dict | None, optional): Options for the
                weight vectors. The vectors are always normalized to sum to one. Defaults to None,
                which uses the default `ReferenceVectorOptions`.
            neighbourhood_size (int, optional): The neighbourhood size `T`, counting the subproblem
                itself. Capped at the number of subproblems. Defaults to 20.
            neighbourhood_probability (float, optional): The probability `delta` that the mating pool
                and the replacement range are the neighbourhood rather than the whole population.
                Defaults to 1.0, the original MOEA/D.
            max_replacements (int | None, optional): The maximum number `n_r` of solutions one
                offspring may replace. None, the default, places no cap, as in the original MOEA/D.
            aggregation (str, optional): The aggregation function, "tchebycheff", "pbi" or
                "weighted_sum". Defaults to "tchebycheff".
            pbi_penalty (float, optional): The penalty `theta` of the PBI function. Defaults to 5.0,
                the value of Zhang and Li (2007), Section V-G.
            seed (int, optional): The random seed to use. Defaults to 0.
        """
        raise NotImplementedError("""
        MOEADSelector is not yet implemented.
        I just haven't gotten around to checking the details of the implementation and testing it.
        It is very slow anyway, I wouldn't recommend using it for anything unless the objective functions are very
        expensive and cannot be evaluated in parallel.
        """)
        if reference_vector_options is None:
            reference_vector_options = ReferenceVectorOptions()
        elif isinstance(reference_vector_options, dict):
            reference_vector_options = ReferenceVectorOptions.model_validate(reference_vector_options)
        # MOEA/D's weight vectors are convex combinations of the objectives.
        reference_vector_options.vector_type = "planar"
        super().__init__(
            problem,
            reference_vector_options=reference_vector_options,
            verbosity=verbosity,
            publisher=publisher,
            seed=seed,
        )
        if neighbourhood_size < 2:  # noqa: PLR2004
            raise ValueError("neighbourhood_size must be at least 2, the subproblem and one neighbour.")
        if not 0 <= neighbourhood_probability <= 1:
            raise ValueError("neighbourhood_probability must be in [0, 1].")
        if max_replacements is not None and max_replacements < 1:
            raise ValueError("max_replacements must be positive, or None for no cap.")
        if aggregation not in ("tchebycheff", "pbi", "weighted_sum"):
            raise ValueError(f"Unknown MOEA/D aggregation function: {aggregation}")

        self.weights = self.reference_vectors
        options = self.reference_vector_options
        if (
            options.reference_point
            or options.preferred_solutions
            or options.non_preferred_solutions
            or (options.preferred_ranges)
        ):
            # The preference adaptations of Hakanen et al. (2016) place the vectors as directions in
            # objective space, which is how PBI reads a weight vector. The optimum of a Tchebycheff
            # subproblem lies along 1 / w instead, so the adapted vectors go through the
            # WS-transformation of Qi et al. (2014), Eq. 3, whose Tchebycheff optimum lies along the
            # vector; a vector with a zero component is shifted by epsilon first, as in their
            # Algorithm 1, Step 2. Without the transformation the population settles on the opposite
            # side of the front: on DTLZ2 with reference point (0.2, 0.5, 0.8), the median angle to
            # the reference direction was 44 degrees, against 5.5 with it (6 for PBI).
            if aggregation == "weighted_sum":
                raise ValueError("Preference handling is not supported with the weighted sum aggregation.")
            if aggregation == "tchebycheff":
                shifted = self.reference_vectors + 1e-6 * np.any(self.reference_vectors <= 0, axis=1, keepdims=True)
                inverse = 1.0 / shifted
                self.weights = inverse / inverse.sum(axis=1, keepdims=True)
        self.neighbourhood_size = min(neighbourhood_size, self.number_of_subproblems)
        self.neighbourhood_probability = neighbourhood_probability
        self.max_replacements = max_replacements
        self.aggregation = aggregation
        self.pbi_penalty = pbi_penalty

        # Step 1.1 (2009) / Step 1.2 (2007): the T closest weight vectors to each weight vector. A
        # subproblem's own vector is placed first explicitly, since preference handling can add edge
        # vectors that duplicate one already in the set.
        distances = cdist(self.weights, self.weights)
        np.fill_diagonal(distances, -1.0)
        self.neighbourhoods = np.argsort(distances, axis=1, kind="stable")[:, : self.neighbourhood_size]

        self.ideal_point: np.ndarray | None = None
        self.solutions: pl.DataFrame | None = None
        self.outputs: pl.DataFrame | None = None
        self._variables: np.ndarray | None = None
        self._outputs: np.ndarray | None = None
        self._targets: np.ndarray | None = None
        self._violations: np.ndarray | None = None
        self._subproblem: int | None = None
        self._pool: np.ndarray | None = None
        self.replaced: list[int] = []

    @property
    def number_of_subproblems(self) -> int:
        """The number of subproblems, which is also the population size."""
        return self.reference_vectors.shape[0]

    def mating_pool(self, subproblem: int) -> np.ndarray:
        """Draw the mating pool of a subproblem, which is also the range the offspring may replace in.

        This is Step 2.1 of MOEA/D-DE. With `neighbourhood_probability = 1` it is always the
        neighbourhood, as in the original MOEA/D. The pool is remembered for the next call to `do`.

        Args:
            subproblem (int): The index `i` of the subproblem an offspring is about to be made for.

        Returns:
            np.ndarray: The indices of the subproblems in the pool. Always contains `subproblem`.
        """
        if self.rng.random() < self.neighbourhood_probability:
            pool = self.neighbourhoods[subproblem]
        else:
            pool = np.arange(self.number_of_subproblems)
        self._subproblem = subproblem
        self._pool = pool
        return pool

    def _aggregate(self, targets: np.ndarray, subproblems: np.ndarray) -> np.ndarray:
        return moead_scalarize(
            targets, self.weights[subproblems], self.ideal_point, self.aggregation, pbi_penalty=self.pbi_penalty
        )

    def do(
        self,
        parents: tuple[SolutionType, pl.DataFrame],
        offsprings: tuple[SolutionType, pl.DataFrame],
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Initialize the population, or update the last mating pool with one or more offspring.

        Args:
            parents (tuple[SolutionType, pl.DataFrame]): The current population, one solution per
                subproblem in order, and its outputs.
            offsprings (tuple[SolutionType, pl.DataFrame]): The offspring and their outputs. Empty on
                the first call, which takes `parents` as the initial population.

        Returns:
            tuple[SolutionType, pl.DataFrame]: The updated population and its outputs.

        Raises:
            ValueError: If the initial population does not hold one solution per subproblem, or if
                offspring arrive before `mating_pool` has been called.
        """
        if not isinstance(parents[0], pl.DataFrame):
            raise TypeError("MOEADSelector works on polars DataFrames only.")
        if offsprings[1].is_empty():
            return self._initialize(parents[0], parents[1])
        if self._pool is None:
            raise ValueError("Call mating_pool(i) for the subproblem before passing its offspring to do().")

        offspring_targets = offsprings[1][self.target_symbols].to_numpy()
        offspring_violations = total_constraint_violation(offsprings[1], self.constraints_symbols)
        offspring_variables = offsprings[0][self.variable_symbols].to_numpy()
        offspring_outputs = offsprings[1][self.outputs.columns].to_numpy()
        self.replaced = []

        for row in range(offspring_targets.shape[0]):
            y = offspring_targets[row]
            y_violation = 0.0 if offspring_violations is None else offspring_violations[row]
            # 2007 Step 2.3 / 2009 Step 2.4: update the ideal point.
            self.ideal_point = np.minimum(self.ideal_point, y)

            # 2009 Step 2.5: visit the pool in random order and stop after n_r replacements. With
            # no cap, the order does not matter and this is 2007 Step 2.4.
            order = self.rng.permutation(self._pool)
            g_new = self._aggregate(np.broadcast_to(y, (len(order), len(y))), order)
            g_old = self._aggregate(self._targets[order], order)
            old_violations = self._violations[order]
            better = (y_violation < old_violations) | ((y_violation == old_violations) & (g_new <= g_old))
            winners = order[better]
            if self.max_replacements is not None:
                winners = winners[: self.max_replacements]

            self._variables[winners] = offspring_variables[row]
            self._outputs[winners] = offspring_outputs[row]
            self._targets[winners] = y
            self._violations[winners] = y_violation
            self.replaced.extend(winners.tolist())

        if self.replaced:
            self.solutions = pl.DataFrame(self._variables, schema=self.solutions.schema, orient="row")
            self.outputs = pl.DataFrame(self._outputs, schema=self.outputs.schema, orient="row")
        return self.solutions, self.outputs

    def _initialize(self, solutions: pl.DataFrame, outputs: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Take the initial population and set the ideal point from it (2007 Step 1.4, 2009 Step 1.3)."""
        if len(solutions) != self.number_of_subproblems:
            raise ValueError(
                f"MOEA/D needs one initial solution per subproblem: got {len(solutions)} solutions for "
                f"{self.number_of_subproblems} weight vectors."
            )
        self.solutions = solutions[self.variable_symbols]
        self.outputs = outputs
        self._variables = self.solutions.to_numpy().astype(float)
        self._outputs = outputs.to_numpy().astype(float)
        self._targets = outputs[self.target_symbols].to_numpy().astype(float)
        violations = total_constraint_violation(outputs, self.constraints_symbols)
        self._violations = np.zeros(len(outputs)) if violations is None else violations.astype(float)
        self.ideal_point = self._targets.min(axis=0)
        self._pool = None
        self.notify()
        return self.solutions, self.outputs

    def state(self) -> Sequence[Message]:
        """Return the operator's state as messages for the current verbosity level."""
        if self.verbosity == 0 or self.solutions is None:
            return []
        state = DictMessage(
            topic=SelectorMessageTopics.STATE,
            value={
                "population_size": self.number_of_subproblems,
                "ideal_point": self.ideal_point.tolist(),
            },
            source=self.__class__.__name__,
        )
        if self.verbosity == 1:
            return [state]
        return [
            Array2DMessage(
                topic=SelectorMessageTopics.REFERENCE_VECTORS,
                value=self.reference_vectors.tolist(),
                source=self.__class__.__name__,
            ),
            state,
            PolarsDataFrameMessage(
                topic=SelectorMessageTopics.SELECTED_VERBOSE_OUTPUTS,
                value=self.solutions.hstack(self.outputs),
                source=self.__class__.__name__,
            ),
        ]

    def update(self, message: Message) -> None:
        """Handle an incoming message. This operator does not react to messages."""


def constrained_dominance_matrix(targets: np.ndarray, violations: np.ndarray | None) -> np.ndarray:
    """`dom[i, j]` is True when solution i dominates solution j under constrained domination.

    A feasible solution dominates every infeasible one, of two infeasible solutions the one with the
    smaller total violation dominates, and two feasible solutions are compared by Pareto dominance
    (Deb et al. 2002). Without constraints this is Pareto dominance.
    """
    dominance = dominance_matrix(targets)
    if violations is None:
        return dominance
    feasible = violations <= 0
    # Basically, feasible solutions dominate infeasible ones, and among infeasible solutions the one with
    # the smaller violation "dominates". Feasible solutions are compared by Pareto dominance.
    return np.where(feasible[:, None] & feasible[None, :], dominance, violations[:, None] < violations[None, :])


def spea2_fitness(targets: np.ndarray, violations: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """The SPEA2 fitness `F = R + D` of every solution, lower is better (Zitzler et al. 2001, Section 3.1).

    The strength `S(i)` counts the solutions `i` dominates and the raw fitness `R(i)` sums the
    strengths of the solutions dominating `i`, so `R = 0` exactly for the nondominated solutions.
    The density `D(i) = 1 / (sigma_i^k + 2)` uses the distance to the k-th nearest other solution in
    objective space, with `k = floor(sqrt(n))` for `n` solutions, and stays below one.

    Args:
        targets (np.ndarray): the minimized objective vectors, shape `(n, m)`.
        violations (np.ndarray | None): total constraint violations for constrained domination, or None.

    Returns:
        tuple[np.ndarray, np.ndarray]: the fitness `F` and the pairwise objective-space distances,
            whose diagonal is infinite.
    """
    n = len(targets)
    dominance = constrained_dominance_matrix(targets, violations)
    strength = dominance.sum(axis=1)
    raw = (dominance * strength[:, None]).sum(axis=0)
    distances = cdist(targets, targets)
    np.fill_diagonal(distances, np.inf)
    if n < 2:  # noqa: PLR2004
        return raw.astype(float), distances
    k = min(int(np.sqrt(n)), n - 1)
    kth_nearest = np.sort(distances, axis=1)[:, k - 1]
    return raw + 1.0 / (kth_nearest + 2.0), distances


def spea2_truncate(distances: np.ndarray, keep: int) -> list[int]:
    """SPEA2's archive truncation: remove the most crowded solution until `keep` remain.

    At each step the solution whose sorted distances to the others still in the set are
    lexicographically smallest is removed: the one closest to another, ties broken by the second
    closest, and so on (Zitzler et al. 2001, Section 3.2). Boundary solutions are kept, since an
    extreme point always has a larger nearest-neighbour distance than its neighbour on the inside.

    Args:
        distances (np.ndarray): pairwise distances among the candidates, with an infinite diagonal.
        keep (int): how many candidates to keep.

    Returns:
        list[int]: the positions of the kept candidates.
    """
    return _spea2_truncate(distances, keep).tolist()


@njit
def _sorts_before(a: float, b: float) -> bool:
    """True when `a` comes before `b` in ascending order, with NaN last as in `np.sort`."""
    return a < b or (np.isnan(b) and not np.isnan(a))


@njit
def _spea2_truncate(distances: np.ndarray, keep: int) -> np.ndarray:
    """The loop of `spea2_truncate`, returning the kept positions in ascending order.

    Each row's candidates are sorted by distance once. Removing a candidate deletes it from every
    row, which leaves the rows sorted, so no row is sorted again.
    """
    n = len(distances)
    neighbours = np.empty((n, n), dtype=np.int64)
    for i in range(n):
        neighbours[i] = np.argsort(distances[i])
    alive = np.ones(n, dtype=np.bool_)
    size = n
    while size > keep:
        # The lexicographically smallest row of sorted distances; the first one wins a tie.
        crowded = -1
        for i in range(n):
            if not alive[i]:
                continue
            if crowded == -1:
                crowded = i
                continue
            for j in range(size):
                current = distances[i, neighbours[i, j]]
                best = distances[crowded, neighbours[crowded, j]]
                if _sorts_before(current, best):
                    crowded = i
                    break
                if _sorts_before(best, current):
                    break
        alive[crowded] = False
        for i in range(n):
            if not alive[i]:
                continue
            j = 0
            while neighbours[i, j] != crowded:
                j += 1
            for t in range(j, size - 1):
                neighbours[i, t] = neighbours[i, t + 1]
        size -= 1
    return np.flatnonzero(alive)


class SPEA2Selector(_FitnessPublishingSelector):
    """The environmental selection of SPEA2, which fills the archive.

    Every solution of the archive and the population with a fitness below one, that is every
    nondominated solution, is copied to the next archive. If they do not fill it, the best dominated
    solutions by fitness complete it; if they overfill it, `spea2_truncate` thins them. The archive is
    what this selector returns, and the fitness it publishes is `1 / (1 + F)`, higher-is-better and
    positive, for the binary tournament that mates within the archive.

    Under template 2 the parents passed to `do` are the archive and the offspring are the population,
    so the archive size is `population_size` and the population size is the mating selection's
    `winner_size`. In the first generation the archive is empty and the initial population is passed
    as the parents, which is the same thing.

    The paper has no constraint handling for continuous problems. On a constrained problem the
    strengths and raw fitness use constrained domination (Deb et al. 2002), so that feasible solutions
    are the nondominated ones whenever there are any. This is DESDEO's addition.

    References:
        Zitzler, E., Laumanns, M., & Thiele, L. (2001). SPEA2: Improving the strength Pareto
            evolutionary algorithm. TIK-Report 103, Computer Engineering and Networks Laboratory
            (TIK), ETH Zurich. https://doi.org/10.3929/ethz-a-004284029
    """

    def do(
        self, parents: tuple[SolutionType, pl.DataFrame], offsprings: tuple[SolutionType, pl.DataFrame]
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Select the next archive from the current archive and population.

        Args:
            parents (tuple[SolutionType, pl.DataFrame]): the archive (or the initial population) and its outputs.
            offsprings (tuple[SolutionType, pl.DataFrame]): the population and its outputs. Empty in the first
                generation.

        Returns:
            tuple[SolutionType, pl.DataFrame]: the next archive and its outputs.
        """
        solutions, outputs = self._merge(parents, offsprings)
        targets = outputs[self.target_symbols].to_numpy().astype(float)
        violations = total_constraint_violation(outputs, self.constraints_symbols)
        fitness, distances = spea2_fitness(targets, violations)

        nondominated = np.flatnonzero(fitness < 1)
        if len(nondominated) > self.population_size:
            kept = spea2_truncate(distances[np.ix_(nondominated, nondominated)], self.population_size)
            chosen = nondominated[kept]
        else:
            dominated = np.flatnonzero(fitness >= 1)
            best_dominated = dominated[np.argsort(fitness[dominated], kind="stable")]
            chosen = np.concatenate([nondominated, best_dominated[: self.population_size - len(nondominated)]])

        chosen = chosen.tolist()
        return self._finish(solutions, outputs, chosen, 1.0 / (1.0 + fitness[chosen]))


def _nan_argmin(values: np.ndarray) -> int:
    """Index of the smallest value skipping NaN, or 0 when every value is NaN, as MATLAB's `min` returns it."""
    return 0 if np.isnan(values).all() else int(np.nanargmin(values))


def _nan_argmax(values: np.ndarray) -> int:
    """Index of the largest value skipping NaN, or 0 when every value is NaN, as MATLAB's `max` returns it."""
    return 0 if np.isnan(values).all() else int(np.nanargmax(values))


def _lp_norm(points: np.ndarray, p: float) -> np.ndarray:
    """`||x||_p` along the last axis; the largest absolute value when `p` is infinite, as MATLAB's `vecnorm`."""
    with np.errstate(all="ignore"):
        if np.isinf(p):
            return np.max(np.abs(points), axis=-1)
        return np.sum(np.abs(points) ** p, axis=-1) ** (1.0 / p)


def agemoea2_extreme_points(front: np.ndarray) -> np.ndarray:
    """The extreme points AGE-MOEA-II normalizes a shifted first front by (`front_normalization` in the author's code).

    For each objective, the point that minimizes the achievement scalarizing function with weight 1 on that
    objective and 1e-6 on the others, as in NSGA-III. One point can be the extreme of several objectives.
    """
    weights = 1e-6 + np.eye(front.shape[1])
    with np.errstate(all="ignore"):
        return np.array([_nan_argmin(np.fmax.reduce(front / w, axis=1)) for w in weights])


def agemoea2_normalize(front: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Normalize a first front shifted to its ideal point (Panichella 2019, Section 3.2, as the author's code does it).

    Each objective is divided by the intercept of the hyperplane through the extreme points
    (`agemoea2_extreme_points`), and the result is shifted so that each objective's smallest value is zero again.
    The largest value of each objective replaces the intercepts only when one of them is NaN, so a negative or
    infinite intercept is kept, although the paper falls back to these min-max constants whenever the plane is
    "indefinite, impossible or leading to abnormal normalization results". The plane is solved by LU factorization,
    as MATLAB's backslash solves a square system, so a singular one gives Inf or NaN instead of an error.

    Returns:
        tuple[np.ndarray, np.ndarray]: the normalized front and the indices of the extreme points.
    """
    extremes = agemoea2_extreme_points(front)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", LinAlgWarning)
        plane = lu_solve(lu_factor(front[extremes], check_finite=False), np.ones(front.shape[1]), check_finite=False)
        intercepts = 1.0 / plane
    if np.isnan(intercepts).any():
        intercepts = np.fmax.reduce(front, axis=0)
    with np.errstate(all="ignore"):
        normalized = front / intercepts
        return normalized - np.fmin.reduce(normalized, axis=0), extremes


def agemoea2_corner_solutions(front: np.ndarray) -> np.ndarray:
    """The point nearest each objective axis by perpendicular distance (`FindCornerSolutions` in the author's code).

    A point can be the corner of several axes. When the front has no more points than objectives, every point is a
    corner.
    """
    m, n = front.shape
    if m <= n:
        return np.arange(m)
    with np.errstate(all="ignore"):
        return np.array([_nan_argmin(np.linalg.norm(np.delete(front, i, axis=1), axis=1)) for i in range(n)])


def agemoea2_curvature(point: np.ndarray, tolerance: float = 1e-3, max_iterations: int = 100) -> float:
    """Estimate the exponent `p` with `sum_i a_i ** p = 1` by Newton-Raphson (Panichella 2022, Eq. 7-9).

    Starts from `p = 1` and stops when two iterates differ by at most `tolerance` (Section 3.1). Coordinates equal to
    zero are left out of the derivative, the paper's convention `0 ** p * log 0 = 0`. A result that is NaN or not
    positive is replaced by 1, a flat front, as `ComputeGeometry` in the author's code does.

    Eq. 9 is printed as `p + log(S) / D`, with `S = sum a ** p` and `D = sum a ** p log a`. That sign sends the
    iteration the wrong way: on the paper's own example B = (cos pi/8, sin pi/8) it reaches -1.44 after four steps.
    Newton's step for `f(p) = log S` is `p - f / f' = p - S log(S) / D`, which the author's code takes and which reaches
    the paper's reported 1.999999999879 in four steps.
    """
    nonzero = point[point != 0]
    p = previous = 1.0
    with np.errstate(all="ignore"):
        for _ in range(max_iterations):
            powered = nonzero**p
            p -= np.log(np.sum(point**p)) * np.sum(powered) / np.sum(powered * np.log(nonzero))
            if abs(p - previous) <= tolerance:
                break
            previous = p
    return 1.0 if np.isnan(p) or p <= 0 else float(abs(p))


def agemoea2_geodesic_distances(front: np.ndarray, p: float) -> np.ndarray:
    """Approximate geodesic distances between the projections of a normalized front (Panichella 2022, Sec. 3.2).

    Each point is projected onto the manifold `sum_i x_i ** p = 1` (Eq. 14). The distance between two projected
    points is the length of the two-segment path through the projection of their midpoint (Eq. 11-13). On a flat
    front (p = 1) the midpoint already lies on the manifold, and the path is the straight segment.
    """
    with np.errstate(all="ignore"):
        projected = front / np.sum(front**p, axis=1, keepdims=True) ** (1.0 / p)
        midpoints = (projected[:, None, :] + projected[None, :, :]) / 2
        midpoints = midpoints / np.sum(midpoints**p, axis=2, keepdims=True) ** (1.0 / p)
        distances = np.linalg.norm(projected[:, None, :] - midpoints, axis=2) + np.linalg.norm(
            projected[None, :, :] - midpoints, axis=2
        )
    np.fill_diagonal(distances, 0.0)
    return distances


def agemoea2_survival_score(front: np.ndarray) -> tuple[np.ndarray, float]:
    """The survival scores of a first front and its curvature (Panichella 2019, Algorithm 2, lines 2-18).

    The front is shifted to its ideal point and normalized (`agemoea2_normalize`), and the curvature `p` is estimated
    on the solution nearest the origin that is not a corner (`agemoea2_corner_solutions`, `agemoea2_curvature`). The
    extreme points score infinity. The rest join the selected set one at a time, each time the one whose diversity
    (the sum of its two smallest geodesic distances to the selected set) divided by its proximity (`||f||_p`) is
    largest, and that ratio is its score. As in the author's code, the last solution left keeps the score 0.

    Returns:
        tuple[np.ndarray, float]: the scores, in the order of `front`, and `p`.
    """
    score = np.zeros(len(front))
    with np.errstate(all="ignore"):
        normalized, extremes = agemoea2_normalize(front - np.fmin.reduce(front, axis=0))
    score[extremes] = np.inf
    selected = np.zeros(len(front), dtype=bool)
    selected[extremes] = True

    nearest = np.linalg.norm(normalized, axis=1)
    nearest[agemoea2_corner_solutions(normalized)] = np.inf
    p = agemoea2_curvature(normalized[_nan_argmin(nearest)])
    with np.errstate(all="ignore"):
        distances = agemoea2_geodesic_distances(normalized, p) / _lp_norm(normalized, p)[:, None]

    remaining = list(np.flatnonzero(~selected))
    for _ in range(len(remaining) - 1):
        # np.sort puts NaN last, as MATLAB's mink does.
        value = np.sort(distances[np.ix_(remaining, np.flatnonzero(selected))], axis=1)[:, :2].sum(axis=1)
        best = _nan_argmax(value)
        score[remaining[best]] = value[best]
        selected[remaining.pop(best)] = True
    return score, p


class AGEMOEA2Selector(_FitnessPublishingSelector):
    """The environmental selection of AGE-MOEA-II, as the author's code implements it.

    This follows Panichella's own implementation, the replication package of the 2022 paper (Zenodo 6462859), whose
    code PlatEMO 4.15 ships unchanged as AGE-MOEA-II. It leaves out one step of that code, described below.

    Parents and offspring are sorted into nondominated fronts, which are copied whole while they fit. The front that
    does not fit is ranked by survival score and cut. First-front scores come from the front's geometry
    (`agemoea2_survival_score`). A solution of a later front scores `1 / ||f - z||_p`, where `f` are its raw
    objective values, `z` holds the smallest value of each objective in the merged population, and `p` is the first
    front's curvature. On a constrained problem the fronts follow constrained domination, as PlatEMO's sorting does.

    The author's code departs from the papers in three places, and this selector follows the code:

    - Normalization keeps a negative or infinite intercept (`agemoea2_normalize`), where the 2019 paper falls back to
      min-max constants.
    - Later fronts are scored on raw objectives. The 2019 paper (Section 3.2) normalizes them with the first front's
      constants.
    - The last first-front solution of the greedy scoring loop keeps the score 0.

    NaN, which degenerate fronts produce through `0 / 0`, is handled the way MATLAB handles it: `min` and `max` skip
    it, and the descending sort that orders the cut front puts it first.

    The author's code also rounds every objective to 12 decimals before sorting. That step is left out here. It is an
    absolute threshold, so what it does depends on the objectives' scale. On 3-objective DTLZ4 its effect is large:
    from a random start, 47 of 50 runs with the rounding reached the whole front, and 26 of 50 without it.

    The fitness published for the binary tournament ranks solutions by front first and survival score second, with
    NaN below every number and equal scores tied, as the author's `TournamentSelection(2, N, FrontNo, -CrowdDis)`
    compares them.

    pymoo 0.6.2's AGEMOEA2 differs from the author's code in several places: it picks the extreme points by distance
    to the axes, falls back to min-max constants on a negative intercept, normalizes later fronts, and never scores
    the cut front unless it is the first.

    References:
        Panichella, A. (2022). An improved Pareto front modeling algorithm for large-scale many-objective
            optimization. In Proceedings of the Genetic and Evolutionary Computation Conference (GECCO '22)
            (pp. 565-573). https://doi.org/10.1145/3512290.3528732

        Panichella, A. (2019). An adaptive evolutionary algorithm based on non-euclidean geometry for many-objective
            optimization. In Proceedings of the Genetic and Evolutionary Computation Conference (GECCO '19)
            (pp. 595-603). https://doi.org/10.1145/3321707.3321839

        Panichella, A. (2022). An improved Pareto front modeling algorithm for large-scale many-objective
            optimization [Source code]. Zenodo. https://doi.org/10.5281/zenodo.6462859
    """

    def do(
        self, parents: tuple[SolutionType, pl.DataFrame], offsprings: tuple[SolutionType, pl.DataFrame]
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Select the next population from parents and offspring (Panichella 2022, Algorithm 2, lines 5-16).

        Args:
            parents (tuple[SolutionType, pl.DataFrame]): the parents and their outputs.
            offsprings (tuple[SolutionType, pl.DataFrame]): the offspring and their outputs. Empty in the first
                generation.

        Returns:
            tuple[SolutionType, pl.DataFrame]: the selected solutions and their outputs.
        """
        solutions, outputs = self._merge(parents, offsprings)
        targets = outputs[self.target_symbols].to_numpy().astype(float)
        fronts = constrained_fronts(targets, total_constraint_violation(outputs, self.constraints_symbols))
        # The front reached when N solutions have been sorted is the one to cut, even when it fits exactly.
        last = min(int(np.searchsorted(np.cumsum(fronts.sum(axis=1)), self.population_size)), len(fronts) - 1)

        score = np.zeros(len(targets))
        score[fronts[0]], p = agemoea2_survival_score(targets[fronts[0]])
        ideal = targets.min(axis=0)
        for d in range(1, last + 1):
            with np.errstate(divide="ignore"):
                score[fronts[d]] = 1.0 / _lp_norm(targets[fronts[d]] - ideal, p)

        chosen = [int(i) for d in range(last) for i in np.flatnonzero(fronts[d])]
        cut = np.flatnonzero(fronts[last])
        # Descending, NaN first, ties in index order, as MATLAB's sort(..., 'descend').
        order = np.lexsort((-np.where(np.isnan(score[cut]), 0.0, score[cut]), ~np.isnan(score[cut])))
        chosen = sorted(chosen + [int(i) for i in cut[order[: self.population_size - len(chosen)]]])

        rank = np.argmax(fronts[:, chosen], axis=0)
        kept = np.where(np.isnan(score[chosen]), -np.inf, score[chosen])
        fitness = np.zeros(len(chosen))
        for d in np.unique(rank):
            members = np.flatnonzero(rank == d)
            levels = np.unique(kept[members], return_inverse=True)[1]
            # Front first, survival score second; positive and higher-is-better for the tournament's argmax.
            fitness[members] = (rank.max() + 1.0 - d) + (levels + 1) / (levels.max() + 2)
        self.curvature = p
        return self._finish(solutions, outputs, chosen, fitness)


def hype_alpha(k: int, size: int) -> np.ndarray:
    """The weights `alpha_i / i` of HypE's fitness `I_h^k` for a set of `size` solutions (Bader and Zitzler, Eq. 12-13).

    `alpha_i = prod_{j=1}^{i-1} (k - j) / (size - j)` is the probability that a region dominated by `i`
    solutions is lost when `k` solutions are removed at random, given that one of them is removed.

    Returns:
        np.ndarray: `weights[i] = alpha_i / i` for `i = 0..size`, with `weights[0] = 0` and zero for `i > k`.
    """
    weights = np.zeros(size + 1)
    alpha = 1.0
    for i in range(1, min(k, size) + 1):
        if i > 1:
            alpha *= (k - (i - 1)) / (size - (i - 1))
        weights[i] = alpha / i
    return weights


@njit
def _hype_exact_3d(points: np.ndarray, reference: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Exact `I_h^k` of every point in three objectives, by sweeping the third objective.

    Within each slab between consecutive values of the third objective, the cells of the grid spanned
    by the first two objectives' values are dominated by a known number `d` of the points added so far;
    each such cell's volume times `weights[d]` goes to every point dominating it, which a suffix sum
    over the grid delivers. The cost is cubic in the number of points.
    """
    n = points.shape[0]
    xs = np.unique(np.append(points[:, 0], reference[0]))
    ys = np.unique(np.append(points[:, 1], reference[1]))
    nx, ny = len(xs) - 1, len(ys) - 1
    ix = np.searchsorted(xs, points[:, 0])
    iy = np.searchsorted(ys, points[:, 1])
    order = np.argsort(points[:, 2])
    counts = np.zeros((nx + 1, ny + 1), dtype=np.int64)
    suffix = np.zeros((nx + 1, ny + 1))
    values = np.zeros(n)
    added = 0
    while added < n:
        z_low = points[order[added], 2]
        while added < n and points[order[added], 2] == z_low:
            q = order[added]
            for i in range(ix[q], nx):
                for j in range(iy[q], ny):
                    counts[i, j] += 1
            added += 1
        z_high = points[order[added], 2] if added < n else reference[2]
        height = z_high - z_low
        if height <= 0:
            continue
        for i in range(nx - 1, -1, -1):
            for j in range(ny - 1, -1, -1):
                count = counts[i, j]
                cell = weights[count] * (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j]) * height if count > 0 else 0.0
                suffix[i, j] = cell + suffix[i + 1, j] + suffix[i, j + 1] - suffix[i + 1, j + 1]
        for u in range(added):
            q = order[u]
            values[q] += suffix[ix[q], iy[q]]
    return values


def hype_fitness_exact(points: np.ndarray, reference: np.ndarray, k: int) -> np.ndarray:
    """Exact HypE fitness `I_h^k(a, A, R)` of every point for two or three objectives (Bader and Zitzler, Def. III.6).

    Args:
        points (np.ndarray): the minimized objective vectors of the set `A`, shape `(n, m)`, `m` 2 or 3.
        reference (np.ndarray): the reference point, shape `(m,)`.
        k (int): the fitness parameter, the number of solutions to be removed.

    Returns:
        np.ndarray: the fitness of each point.
    """
    n, m = points.shape
    if m not in (2, 3):
        raise ValueError("Exact HypE fitness is implemented for two and three objectives.")
    clipped = np.minimum(points, reference)
    if m == 2:  # noqa: PLR2004
        clipped = np.column_stack([clipped, np.zeros(n)])
        reference = np.append(reference, 1.0)
    return _hype_exact_3d(clipped.astype(float), np.asarray(reference, dtype=float), hype_alpha(k, n))


@njit
def _hype_monte_carlo_hits(points: np.ndarray, samples: np.ndarray, weights: np.ndarray, k: int) -> np.ndarray:
    """Sum `weights[d]` over the samples each point dominates, `d` being the sample's dominator count.

    A sample with more than `k` dominators credits nobody, so counting stops there.
    """
    n, m = points.shape
    values = np.zeros(n)
    dominators = np.empty(n, dtype=np.int64)
    for s in range(samples.shape[0]):
        count = 0
        for a in range(n):
            dominates = True
            for j in range(m):
                if points[a, j] > samples[s, j]:
                    dominates = False
                    break
            if dominates:
                dominators[count] = a
                count += 1
                if count > k:
                    break
        if 0 < count <= k:
            weight = weights[count]
            for u in range(count):
                values[dominators[u]] += weight
    return values


def hype_fitness_monte_carlo(
    points: np.ndarray, reference: np.ndarray, k: int, n_samples: int, rng: np.random.Generator
) -> np.ndarray:
    """Monte Carlo estimate of the HypE fitness `I_h^k` (Bader and Zitzler, Algorithm 3).

    Samples are drawn uniformly from the box between the points' minimum and the reference point.
    Each sample dominated by `d <= k` points credits each of them `weights[d]` times the box volume
    over the number of samples.
    """
    lower = points.min(axis=0)
    span = np.maximum(reference - lower, 0.0)
    samples = lower + span * rng.random((n_samples, points.shape[1]))
    hits = _hype_monte_carlo_hits(points.astype(float), samples, hype_alpha(k, len(points)), k)
    return hits * float(np.prod(span)) / n_samples


class HypESelector(_FitnessPublishingSelector):
    """The environmental selection of HypE, and the hypervolume fitness for its mating selection.

    Parents and offspring are sorted into nondominated fronts, copied whole while they fit. From the
    front that does not fit, solutions are removed one at a time, each time the one with the smallest
    `I_h^k`, where `k` is the number still to be removed and the fitness is recomputed after every
    removal; ties are broken at random (Bader and Zitzler, Algorithm 7 and Section V). The fitness
    published for the binary tournament is `I_h^N(a, P, R)` over the selected population (Algorithm 6).

    The fitness is computed exactly up to `exact_max_objectives` objectives (three, as the paper
    recommends) and estimated from `n_samples` Monte Carlo samples above that.

    The paper leaves the reference point to the user. Here the objectives are normalized to [0, 1] by
    the minimum and maximum over parents and offspring each generation, as DESDEO's SMS-EMOA does, and
    the reference point is `normalised_reference_point_component` in every objective.

    On a constrained problem the fronts follow constrained domination (Deb et al. 2002), and the
    published fitness places every infeasible solution below every feasible one. This is DESDEO's
    addition.

    References:
        Bader, J., & Zitzler, E. (2011). HypE: An algorithm for fast hypervolume-based many-objective
            optimization. Evolutionary Computation, 19(1), 45-76. https://doi.org/10.1162/EVCO_a_00009
            (Implemented from the technical report version: Bader, J., & Zitzler, E. (2008). TIK
            Report 286, ETH Zurich. https://doi.org/10.3929/ethz-a-005703480)
    """

    def __init__(
        self,
        problem: Problem,
        verbosity: int,
        publisher: Publisher,
        population_size: int,
        n_samples: int = 10_000,
        exact_max_objectives: int = 3,
        normalised_reference_point_component: float = 1.1,
        seed: int = 0,
    ):
        """Initialize the HypE selector.

        Args:
            problem (Problem): The optimization problem to be solved.
            verbosity (int): The verbosity level of the operator.
            publisher (Publisher): The publisher to use for communication.
            population_size (int): The number of solutions selected each generation, `N`.
            n_samples (int, optional): The number of Monte Carlo samples `M`. Defaults to 10 000, the paper's.
            exact_max_objectives (int, optional): The most objectives for which the fitness is computed
                exactly, at most 3. Defaults to 3, as the paper recommends.
            normalised_reference_point_component (float, optional): The reference point in every
                normalized objective. Must exceed one. Defaults to 1.1.
            seed (int, optional): The random seed to use. Defaults to 0.
        """
        raise NotImplementedError(
            """
            HypESelector is not implemented yet. (I haven't checked the implementation fully yet.)
            Plus, it's very slow, and the behaviour is similar to IBEA. You aren't missing much.
            """
        )
        super().__init__(problem, verbosity=verbosity, publisher=publisher, population_size=population_size, seed=seed)
        if n_samples < 1:
            raise ValueError("n_samples must be positive.")
        if not 0 <= exact_max_objectives <= 3:  # noqa: PLR2004
            raise ValueError("exact_max_objectives must be between 0 and 3.")
        if normalised_reference_point_component <= 1:
            raise ValueError("normalised_reference_point_component must exceed one.")
        self.n_samples = n_samples
        self.exact_max_objectives = exact_max_objectives
        self.reference_point_component = normalised_reference_point_component

    def hypervolume_fitness(self, points: np.ndarray, k: int) -> np.ndarray:
        """`I_h^k` of every point against the normalized reference point, exact or estimated."""
        reference = np.full(points.shape[1], self.reference_point_component)
        if 2 <= points.shape[1] <= self.exact_max_objectives:  # noqa: PLR2004
            return hype_fitness_exact(points, reference, k)
        return hype_fitness_monte_carlo(points, reference, k, self.n_samples, self.rng)

    def do(
        self, parents: tuple[SolutionType, pl.DataFrame], offsprings: tuple[SolutionType, pl.DataFrame]
    ) -> tuple[SolutionType, pl.DataFrame]:
        """Select the next population from parents and offspring.

        Args:
            parents (tuple[SolutionType, pl.DataFrame]): the parents and their outputs.
            offsprings (tuple[SolutionType, pl.DataFrame]): the offspring and their outputs. Empty in the first
                generation.

        Returns:
            tuple[SolutionType, pl.DataFrame]: the selected solutions and their outputs.
        """
        solutions, outputs = self._merge(parents, offsprings)
        targets = outputs[self.target_symbols].to_numpy().astype(float)
        lower, upper = targets.min(axis=0), targets.max(axis=0)
        span = np.where(upper > lower, upper - lower, 1.0)
        normalized = (targets - lower) / span
        violations = total_constraint_violation(outputs, self.constraints_symbols)
        fronts = constrained_fronts(targets, violations)

        # Algorithm 7, lines 6-18: copy whole fronts while they fit.
        chosen: list[int] = []
        last = np.array([], dtype=int)
        for front in fronts:
            members = np.flatnonzero(front)
            if len(chosen) + len(members) > self.population_size:
                last = members
                break
            chosen.extend(int(i) for i in members)

        # Lines 19-38: remove the worst of the last front one at a time, recomputing I_h^k each time.
        to_remove = len(chosen) + len(last) - self.population_size
        while to_remove > 0:
            fitness = self.hypervolume_fitness(normalized[last], to_remove)
            worst = np.flatnonzero(fitness == fitness.min())
            last = np.delete(last, worst[0] if len(worst) == 1 else self.rng.choice(worst))
            to_remove -= 1
        chosen.extend(int(i) for i in last)

        # Algorithm 6: the mating fitness is I_h^N(a, P, R) over the new population.
        fitness = self.hypervolume_fitness(normalized[chosen], len(chosen))
        if violations is not None:
            selected_violations = violations[chosen]
            infeasible = selected_violations > 0
            if infeasible.all():
                fitness = 1.0 / (1.0 + selected_violations)
            elif infeasible.any():
                # Below every feasible solution, the least infeasible highest.
                floor = fitness[~infeasible].min()
                fitness[infeasible] = (
                    floor * 0.5 * (1.0 - selected_violations[infeasible] / (2.0 * selected_violations.max()))
                )
        return self._finish(solutions, outputs, chosen, fitness)
