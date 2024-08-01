"""The base class for selection operators.

This whole file should be rewritten. Everything is a mess.
TODO:@light-weaver
"""

from abc import abstractmethod
from collections.abc import Sequence
from enum import Enum

import numpy as np

from desdeo.tools.message import Array2DMessage, DictMessage, Message, SelectorMessageTopics, TerminatorMessageTopics
from desdeo.tools.non_dominated_sorting import fast_non_dominated_sort
from desdeo.tools.patterns import Subscriber


class BaseSelector(Subscriber):
    """A base class for selection operators."""

    def __init__(self, **kwargs):
        """Initialize a selection operator."""
        super().__init__(**kwargs)

    @abstractmethod
    def do(
        self,
        parents: tuple[np.ndarray, np.ndarray, np.ndarray | None],
        offsprings: tuple[np.ndarray, np.ndarray, np.ndarray | None],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        """Perform the selection operation.

        Args:
            parents (tuple[np.ndarray, np.ndarray]): the parent population, their targets, and constraint violations.
            offsprings (tuple[np.ndarray, np.ndarray]): the offspring population and their targets and constraint
                violations.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray | None]: the selected population, their targets and constraint
                violations.
        """


class ParameterAdaptationStrategy(Enum):
    """The parameter adaptation strategies for the RVEA selector."""

    GENERATION_BASED = 1  # Based on the current generation and the maximum generation.
    FUNCTION_EVALUATION_BASED = 2  # Based on the current function evaluation and the maximum function evaluation.
    OTHER = 3  # As of yet undefined strategies.


class RVEASelector(BaseSelector):
    def __init__(
        self,
        reference_vectors: np.ndarray,
        alpha: float = 2.0,
        ideal: np.ndarray = None,
        nadir: np.ndarray = None,
        parameter_adaptation_strategy: ParameterAdaptationStrategy = ParameterAdaptationStrategy.GENERATION_BASED,
        **kwargs,
    ):
        if not isinstance(parameter_adaptation_strategy, ParameterAdaptationStrategy):
            raise TypeError(f"Parameter adaptation strategy must be of Type {type(ParameterAdaptationStrategy)}")
        if parameter_adaptation_strategy == ParameterAdaptationStrategy.OTHER:
            raise ValueError("Other parameter adaptation strategies are not yet implemented.")
        if parameter_adaptation_strategy == ParameterAdaptationStrategy.GENERATION_BASED:
            topics = [TerminatorMessageTopics.GENERATION, TerminatorMessageTopics.MAX_GENERATIONS]
        elif parameter_adaptation_strategy == ParameterAdaptationStrategy.FUNCTION_EVALUATION_BASED:
            topics = [TerminatorMessageTopics.EVALUATION, TerminatorMessageTopics.MAX_EVALUATIONS]
        super().__init__(topics=topics, **kwargs)
        self.reference_vectors = reference_vectors
        self.adapted_reference_vectors = None
        self.reference_vectors_gamma = None
        self.numerator = None
        self.denominator = None
        self.alpha = alpha
        self.ideal = ideal
        self.nadir = nadir
        self.selection = None
        self.penalty = None
        self.parameter_adaptation_strategy = parameter_adaptation_strategy

    def do(
        self,
        parents: tuple[np.ndarray, np.ndarray, np.ndarray | None],
        offsprings: tuple[np.ndarray, np.ndarray, np.ndarray | None],
    ) -> tuple[np.ndarray, np.ndarray]:
        solutions = np.vstack((parents[0], offsprings[0]))
        targets = np.vstack((parents[1], offsprings[1]))
        if parents[2] is None:  # noqa: SIM108
            constraints = None
        else:
            constraints = np.vstack((parents[2], offsprings[2]))

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
                if (feasible_bool is False).all():
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
        self.selection = (
            solutions[selection.flatten()],
            targets[selection.flatten()],
            (constraints[selection.flatten()] if constraints is not None else None),
        )
        self.notify()
        return self.selection

    def _partial_penalty_factor(self) -> float:
        """Calculate and return the partial penalty factor for APD calculation.

            This calculation does not include the angle related terms, hence the name.
            If the calculated penalty is outside [0, 1], it will round it up/down to 0/1

        Returns:
            float: The partial penalty factor
        """
        if self.denominator == 0 or self.numerator is None or self.denominator is None:
            return 0
        penalty = self.numerator / self.denominator
        if penalty < 0:
            penalty = 0
        if penalty > 1:
            penalty = 1
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

    def state(self) -> Sequence[Message] | None:
        if self.verbosity == 0 or self.selection is None:
            return None
        return [
            Array2DMessage(
                topic=SelectorMessageTopics.SELECTION, value=self.selection.tolist(), source=self.__class__.__name__
            ),
            """ "reference_vectors": self.reference_vectors,
            "adapted_reference_vectors": self.adapted_reference_vectors,
            "gamma": self.reference_vectors_gamma,
            "alpha": self.alpha,
            "ideal": self.ideal,
            "partial_penalty_factor": self._partial_penalty_factor(),
            "selection": self.selection, """,
        ]

    def _adapt(self):
        self.adapted_reference_vectors = self.reference_vectors
        if self.ideal is not None and self.nadir is not None:
            for i in range(self.reference_vectors.shape[0]):
                self.adapted_reference_vectors[i] = self.reference_vectors[i] * (self.nadir - self.ideal)
        self.adapted_reference_vectors = (
            self.adapted_reference_vectors / np.linalg.norm(self.adapted_reference_vectors, axis=1)[:, None]
        )
        self.reference_vectors_gamma = np.zeros(self.reference_vectors.shape[0])
        self.reference_vectors_gamma[:] = np.inf

        for i in range(self.reference_vectors.shape[0]):
            for j in range(self.reference_vectors.shape[0]):
                if i != j:
                    angle = np.arccos(np.dot(self.adapted_reference_vectors[i], self.adapted_reference_vectors[j]))
                    if angle < self.reference_vectors_gamma[i]:
                        self.reference_vectors_gamma[i] = angle


class NSGAIII_select(BaseSelector):
    """The NSGA-III selection operator. Code is heavily based on the version of nsga3 in
        the pymoo package by msu-coinlab.

    Parameters
    ----------
    pop : Population
        [description]
    n_survive : int, optional
        [description], by default None

    """

    def __init__(
        self,
        reference_vectors: np.ndarray,
        n_survive: int,
        ideal: np.ndarray = None,
        nadir: np.ndarray = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.reference_vectors = reference_vectors
        self.adapted_reference_vectors = None
        self.worst_fitness: np.ndarray = nadir
        self.extreme_points: np.ndarray = None
        self.n_survive = n_survive
        self.ideal: np.ndarray = ideal
        self.selection: tuple[np.ndarray, np.ndarray, np.ndarray | None] = None

        match self.verbosity:
            case 0:
                self.provided_topics = []
            case 1:
                self.provided_topics = [
                    SelectorMessageTopics.REFERENCE_VECTORS,
                    SelectorMessageTopics.STATE,
                ]
            case 2:
                self.provided_topics = [
                    SelectorMessageTopics.REFERENCE_VECTORS,
                    SelectorMessageTopics.STATE,
                    SelectorMessageTopics.SELECTED_INDIVIDUALS,
                    SelectorMessageTopics.SELECTED_TARGETS,
                    SelectorMessageTopics.SELECTED_CONSTRAINTS,
                ]

    def do(
        self,
        parents: tuple[np.ndarray, np.ndarray, np.ndarray | None],
        offsprings: tuple[np.ndarray, np.ndarray, np.ndarray | None],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        """Perform the selection operation for NSGA-III.

        Args:
            parents (tuple[np.ndarray, np.ndarray, np.ndarray  |  None]): The parent population, their targets, and
                constraint violations.
            offsprings (tuple[np.ndarray, np.ndarray, np.ndarray  |  None]): The offspring population and their targets
                and constraint violations.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray | None]: The selected population, their targets and constraint
                violations.
        """
        solutions = np.vstack((parents[0], offsprings[0]))
        targets = np.vstack((parents[1], offsprings[1]))
        if parents[2] is None:  # noqa: SIM108
            constraints = None
        else:
            constraints = np.vstack((parents[2], offsprings[2]))
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
        nadir_point = self.get_nadir_point(
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

        self.selection = (
            solutions[final_selection],
            targets[final_selection],
            (constraints[final_selection] if constraints is not None else None),
        )
        self.notify()
        return self.selection

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

    def state(self) -> Sequence[Message] | None:
        if self.verbosity == 0 or self.selection is None:
            return None
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
            Array2DMessage(
                topic=SelectorMessageTopics.SELECTED_INDIVIDUALS,
                value=self.selection[0].tolist(),
                source=self.__class__.__name__,
            ),
            Array2DMessage(
                topic=SelectorMessageTopics.SELECTED_TARGETS,
                value=self.selection[1].tolist(),
                source=self.__class__.__name__,
            ),
        ]

        if self.selection[2] is not None:
            state_verbose.append(
                Array2DMessage(
                    topic=SelectorMessageTopics.SELECTED_CONSTRAINTS,
                    value=self.selection[2].tolist(),
                    source=self.__class__.__name__,
                )
            )
        return state_verbose

    def update(self, message: Message) -> None:
        pass
