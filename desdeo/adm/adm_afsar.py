from desdeo.emo.operators.selection import ReferenceVectorOptions
import numpy as np
from desdeo.tools.reference_vectors import ReferenceVectors
from desdeo.tools.non_dominated_sorting import non_dominated as nds
from desdeo.problem.schema import Problem
from scipy.special import comb
from itertools import combinations


class ADMAfsar:
    def __init__(
        self,
        problem: Problem,
        it_learning_phase: int,
        it_decision_phase: int,
        reference_vector_options: ReferenceVectorOptions = None,
    ):
        # Initialize variables
        self.problem = problem
        self.it_learning_phase = it_learning_phase
        self.it_decision_phase = it_decision_phase

        self.composite_front = []
        self.iteration_counter = 0
        self.max_iterations = it_learning_phase + it_decision_phase

        self.number_of_objectives = len(problem.objectives)
        self.target_symbols = [f"{x.symbol}_min" for x in problem.objectives]

        self.max_assigned_vector = None

        # Initial random reference point
        self.generate_initial_reference_point()

        self.reference_vector_options = reference_vector_options
        if reference_vector_options is None:
            self.reference_vector_options: ReferenceVectorOptions = (
                ReferenceVectorOptions(
                    adaptation_frequency=100,
                    creation_type="simplex",
                    vector_type="spherical",
                    number_of_vectors=500,
                )
            )
        self._create_simplex()

    def has_next(self):
        """
        Check if there are more iterations left to run.
        """
        return self.iteration_counter < self.max_iterations

    def generate_initial_reference_point(self):
        self.preference = {
            name: np.random.uniform(min_val, max_val)
            for name, min_val, max_val in zip(
                self.target_symbols,
                self.problem.get_ideal_point().values(),
                self.problem.get_nadir_point().values(),
            )
        }

    def get_next_reference_point(self, *fronts):
        if len(self.composite_front) == 0:
            self.composite_front = self.generate_composite_front(*fronts)
        else:
            self.composite_front = self.generate_composite_front(
                self.composite_front, *fronts
            )
        ideal_point = self.composite_front.min(axis=0)
        translated_front = self.translate_front(self.composite_front, ideal_point)
        normalized_front = self.normalize_front(self.composite_front, translated_front)
        assigned_vectors = self.assign_vectors(normalized_front)
        if self.iteration_counter < self.it_learning_phase:
            self.preference = self.generate_RP_learning(
                ideal_point, translated_front, assigned_vectors
            )
        else:
            if self.iteration_counter == self.it_learning_phase:
                self.max_assigned_vector = self.get_max_assigned_vector(
                    assigned_vectors
                )
            self.preference = self.generate_RP_decision(
                ideal_point,
                translated_front,
                assigned_vectors,
                self.max_assigned_vector,
            )
        self.iteration_counter = self.iteration_counter + 1

    def assign_vectors(self, front):
        cosine = np.dot(front, np.transpose(self.reference_vectors))
        if cosine[np.where(cosine > 1)].size:
            cosine[np.where(cosine > 1)] = 1
        if cosine[np.where(cosine < 0)].size:
            cosine[np.where(cosine < 0)] = 0

        # theta = np.arccos(cosine) #check this theta later, if needed or not
        assigned_vectors = np.argmax(cosine, axis=1)

        return assigned_vectors

    def normalize_front(self, front, translated_front):
        translated_norm = np.linalg.norm(translated_front, axis=1)
        translated_norm = np.repeat(
            translated_norm, len(translated_front[0, :])
        ).reshape(len(front), len(front[0, :]))

        translated_norm[translated_norm == 0] = np.finfo(float).eps
        normalized_front = np.divide(translated_front, translated_norm)
        return normalized_front

    def generate_composite_front(self, *fronts):
        _fronts = np.vstack(fronts)
        cf = _fronts[nds(_fronts)]

        return cf

    def translate_front(self, front, ideal):
        translated_front = np.subtract(front, ideal)
        return translated_front

    def generate_RP_learning(self, ideal_point, translated_front, assigned_vectors):
        ideal_cf = ideal_point
        translated_cf = translated_front
        # Assigment of the solutions to the vectors
        # Find the vector which has a minimum number of assigned solutions
        number_assigned = np.bincount(assigned_vectors)
        min_assigned_vector = np.atleast_1d(
            np.squeeze(
                np.where(
                    number_assigned
                    == np.min(number_assigned[np.nonzero(number_assigned)])
                )
            )
        )
        sub_population_index = np.atleast_1d(
            np.squeeze(np.where(assigned_vectors == min_assigned_vector[0]))
            # If there are multiple vectors which have the minimum number of solutions, first one's index is used
        )
        # Assigned solutions to the vector which has a minimum number of solutions
        sub_population_fitness = translated_cf[sub_population_index]
        # Distances of these solutions to the origin
        sub_pop_fitness_magnitude = np.sqrt(
            np.sum(np.power(sub_population_fitness, 2), axis=1)
        )
        # Index of the solution which has a minimum distance to the origin
        minidx = np.where(
            sub_pop_fitness_magnitude == np.nanmin(sub_pop_fitness_magnitude)
        )
        distance_selected = sub_pop_fitness_magnitude[minidx]

        # Create the reference point
        reference_point = (
            distance_selected[0] * self.reference_vectors[min_assigned_vector[0]]
        )
        reference_point = np.squeeze(reference_point + ideal_cf)
        # reference_point = reference_point + ideal_cf
        return dict(zip(self.target_symbols, reference_point))

    def generate_RP_decision(
        self, ideal_point, translated_front, assigned_vectors, max_assigned_vector
    ):
        # assigned_vectors = base.assigned_vectors

        ideal_cf = ideal_point

        translated_cf = translated_front

        sub_population_index = np.atleast_1d(
            np.squeeze(np.where(assigned_vectors == max_assigned_vector))
        )
        sub_population_fitness = translated_cf[sub_population_index]
        # Distances of these solutions to the origin
        sub_pop_fitness_magnitude = np.sqrt(
            np.sum(np.power(sub_population_fitness, 2), axis=1)
        )
        # Index of the solution which has a minimum distance to the origin
        minidx = np.where(
            sub_pop_fitness_magnitude == np.nanmin(sub_pop_fitness_magnitude)
        )
        distance_selected = sub_pop_fitness_magnitude[minidx]

        # Create the reference point
        reference_point = (
            distance_selected[0] * self.reference_vectors[max_assigned_vector]
        )
        reference_point = np.squeeze(reference_point + ideal_cf)
        # reference_point = reference_point + ideal_cf
        return dict(zip(self.target_symbols, reference_point))

    def approx_lattice_resolution(
        self, number_of_vectors: int, number_of_objectives: int
    ) -> int:
        """Approximate the lattice resolution based on the number of vectors."""
        temp_lattice_resolution = 0
        while True:
            temp_lattice_resolution += 1
            temp_number_of_vectors = comb(
                temp_lattice_resolution + number_of_objectives - 1,
                number_of_objectives - 1,
                exact=True,
            )
            if temp_number_of_vectors > number_of_vectors:
                break
        return temp_lattice_resolution - 1

    def _create_simplex(self):
        """Create the reference vectors using simplex lattice design."""

        if "lattice_resolution" in self.reference_vector_options:
            lattice_resolution = self.reference_vector_options["lattice_resolution"]
        elif "number_of_vectors" in self.reference_vector_options:
            lattice_resolution = self.approx_lattice_resolution(
                self.reference_vector_options["number_of_vectors"],
                number_of_objectives=self.number_of_objectives,
            )
        else:
            lattice_resolution = self.approx_lattice_resolution(
                500, number_of_objectives=self.number_of_objectives
            )

        number_of_vectors: int = comb(
            lattice_resolution + self.number_of_objectives - 1,
            self.number_of_objectives - 1,
            exact=True,
        )

        self.reference_vector_options["number_of_vectors"] = number_of_vectors
        self.reference_vector_options["lattice_resolution"] = lattice_resolution

        temp1 = range(1, self.number_of_objectives + lattice_resolution)
        temp1 = np.array(list(combinations(temp1, self.number_of_objectives - 1)))
        temp2 = np.array([range(self.number_of_objectives - 1)] * number_of_vectors)
        temp = temp1 - temp2 - 1
        weight = np.zeros((number_of_vectors, self.number_of_objectives), dtype=int)
        weight[:, 0] = temp[:, 0]
        for i in range(1, self.number_of_objectives - 1):
            weight[:, i] = temp[:, i] - temp[:, i - 1]
        weight[:, -1] = lattice_resolution - temp[:, -1]
        self.reference_vectors = weight / lattice_resolution
        # self.reference_vectors_initial = np.copy(self.reference_vectors)
        self._normalize_rvs()

    def _normalize_rvs(self):
        """Normalize the reference vectors to a unit hypersphere."""
        if self.reference_vector_options["vector_type"] == "spherical":
            norm = np.linalg.norm(self.reference_vectors, axis=1).reshape(-1, 1)
            norm[norm == 0] = np.finfo(float).eps
        elif self.reference_vector_options["vector_type"] == "planar":
            norm = np.sum(self.reference_vectors, axis=1).reshape(-1, 1)
        else:
            raise ValueError(
                "Invalid vector type. Must be either 'spherical' or 'planar'."
            )
        self.reference_vectors = np.divide(self.reference_vectors, norm)

    def get_max_assigned_vector(self, assigned_vectors):
        number_assigned = np.bincount(assigned_vectors)
        max_assigned_vector = np.atleast_1d(
            np.squeeze(
                np.where(
                    number_assigned
                    == np.max(number_assigned[np.nonzero(number_assigned)])
                )
            )
        )
        return max_assigned_vector
