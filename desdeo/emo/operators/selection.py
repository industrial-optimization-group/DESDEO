"""The base class for selection operators."""

from abc import ABC, abstractmethod
from typing import Callable

import numpy as np
from numba import njit
from desdeo.tools.patterns import Subscriber


class BaseSelector(Subscriber):
    """A base class for selection operators."""

    def __init__(self, publisher, *args, **kwargs):
        """Initialize a selection operator."""
        super().__init__(publisher, *args, **kwargs)

    @abstractmethod
    def do(
        self,
        parents: tuple[np.ndarray, np.ndarray, np.ndarray | None],
        offsprings: tuple[np.ndarray, np.ndarray, np.ndarray | None],
        termination_criteria_state: dict | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Perform the selection operation.

        Args:
            parents (tuple[np.ndarray, np.ndarray]): the parent population, their targets, and constraint violations.
            offsprings (tuple[np.ndarray, np.ndarray]): the offspring population and their targets and constraint
                violations.
            termination_criteria_state (dict): the state of the termination criteria. Includes information
                about the current generation and other relevant information.

        Returns:
            tuple[np.ndarray, np.ndarray]: the selected population and their targets.
        """


class RVEASelector(BaseSelector):
    def __init__(
        self,
        reference_vectors: np.ndarray,
        publisher: Callable,
        alpha: float = 2.0,
        ideal: np.ndarray = None,
        nadir: np.ndarray = None,
        *args,
        **kwargs,
    ):
        super().__init__(publisher, *args, **kwargs)
        self.reference_vectors = reference_vectors
        self.adapted_reference_vectors = None
        self.reference_vectors_gamma = None
        self.numerator = None
        self.denominator = None
        self.alpha = alpha
        self.ideal = ideal
        self.nadir = None
        self.selection = None

    def do(
        self,
        parents: tuple[np.ndarray, np.ndarray, np.ndarray | None],
        offsprings: tuple[np.ndarray, np.ndarray, np.ndarray | None],
    ) -> tuple[np.ndarray, np.ndarray]:
        solutions = np.vstack((parents[0], offsprings[0]))
        targets = np.vstack((parents[1], offsprings[1]))
        if parents[2] is None:
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
        self.selection = selection
        self.notify()
        return solutions[selection.flatten()], targets[selection.flatten()], (constraints[selection.flatten()] if constraints is not None else None)

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
        penalty = (penalty**self.alpha) * self.reference_vectors.shape[1]
        return penalty

    def update(self, message: dict):
        if "current_evaluation" in message:
            self.numerator = message["current_evaluation"]
            return
        if "max_evaluation" in message:
            self.denominator = message["max_evaluation"]
            return
        if "current_generation" in message:
            self.numerator = message["current_generation"]
            return
        if "max_generation" in message:
            self.denominator = message["max_generation"]
            return

    def state(self) -> dict:
        return {
            "reference_vectors": self.reference_vectors,
            "adapted_reference_vectors": self.adapted_reference_vectors,
            "gamma": self.reference_vectors_gamma,
            "alpha": self.alpha,
            "ideal": self.ideal,
            "partial_penalty_factor": self._partial_penalty_factor(),
            "selection": self.selection,
        }

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
