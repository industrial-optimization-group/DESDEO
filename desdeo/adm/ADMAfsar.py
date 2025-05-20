from desdeo.adm import BaseADM
import numpy as np
from desdeo.tools.reference_vectors import create_simplex
from desdeo.tools.non_dominated_sorting import non_dominated as nds
from desdeo.problem.schema import Problem


class ADMAfsar(BaseADM):
    """
    Adaptive Decision Maker using the AFSAR approach.

    This ADM generates preferences for interactive evolutionary multiobjective optimization
    based on the method described in:
    Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
    An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.

    Attributes:
        composite_front (list): Stores the composite front of solutions.
        max_assigned_vector (int or None): Index of the vector with the maximum assigned solutions.
        reference_vectors (np.ndarray): Array of reference vectors.
        preference (dict): Current preference information.
    """

    def __init__(
        self,
        problem: Problem,
        it_learning_phase: int,
        it_decision_phase: int,
        preference_type: str = "reference_point",
        lattice_resolution: int = None,
        number_of_vectors: int = None,
    ):
        """
        Initialize the ADMAfsar artificial decision maker.

        Args:
            problem (Problem): The optimization problem to solve.
            it_learning_phase (int): Number of iterations for the learning phase.
            it_decision_phase (int): Number of iterations for the decision phase.
            lattice_resolution (int, optional): Lattice resolution for reference vectors.
            number_of_vectors (int, optional): Number of reference vectors.
        """
        super().__init__(problem, it_learning_phase, it_decision_phase)
        self.composite_front = []
        self.max_assigned_vector = None
        self.preference_type = preference_type

        self.reference_vectors = create_simplex(
            self.number_of_objectives, lattice_resolution, number_of_vectors
        )
        self.generate_initial_preference()

    def generate_initial_preference(self):
        """
        Generate the initial preference as a random point between the ideal and nadir points.

        The preference is stored in self.preference as a dictionary mapping target symbols to values.
        """
        self.preference = {
            name: np.random.uniform(min_val, max_val)
            for name, min_val, max_val in zip(
                self.target_symbols,
                self.problem.get_ideal_point().values(),
                self.problem.get_nadir_point().values(),
            )
        }

    def get_next_preference(self, *fronts):
        """
        Generate the next preference based on the current phase and provided solution fronts.

        Args:
            *fronts: One or more solution fronts (arrays) to be considered.

        Returns:
            dict: The generated preference information.
        """
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
            self.preference = self.generate_preference_learning(
                ideal_point, translated_front, assigned_vectors
            )
        else:
            if self.iteration_counter == self.it_learning_phase:
                self.max_assigned_vector = self.get_max_assigned_vector(
                    assigned_vectors
                )
            self.preference = self.generate_preference_decision(
                ideal_point,
                translated_front,
                assigned_vectors,
                self.max_assigned_vector,
            )
        self.iteration_counter += 1
        return self.preference

    def assign_vectors(self, front):
        """
        Assign each solution in the front to the closest reference vector using cosine similarity.

        Args:
            front (np.ndarray): The normalized solution front.

        Returns:
            np.ndarray: Indices of the assigned reference vectors for each solution.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        cosine = np.dot(front, np.transpose(self.reference_vectors))
        if cosine[np.where(cosine > 1)].size:
            cosine[np.where(cosine > 1)] = 1
        if cosine[np.where(cosine < 0)].size:
            cosine[np.where(cosine < 0)] = 0

        assigned_vectors = np.argmax(cosine, axis=1)
        return assigned_vectors

    def normalize_front(self, front, translated_front):
        """
        Normalize the translated front so that each solution has unit length.

        Args:
            front (np.ndarray): The original solution front.
            translated_front (np.ndarray): The translated solution front.

        Returns:
            np.ndarray: The normalized solution front.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        translated_norm = np.linalg.norm(translated_front, axis=1)
        translated_norm = np.repeat(
            translated_norm, len(translated_front[0, :])
        ).reshape(len(front), len(front[0, :]))

        translated_norm[translated_norm == 0] = np.finfo(float).eps
        normalized_front = np.divide(translated_front, translated_norm)
        return normalized_front

    def generate_composite_front(self, *fronts):
        """
        Generate the composite front by stacking and extracting the non-dominated solutions.

        Args:
            *fronts: One or more solution fronts (arrays).

        Returns:
            np.ndarray: The composite non-dominated front.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        _fronts = np.vstack(fronts)
        cf = _fronts[nds(_fronts)]
        return cf

    def translate_front(self, front, ideal):
        """
        Translate the front by subtracting the ideal point from each solution.

        Args:
            front (np.ndarray): The solution front.
            ideal (np.ndarray): The ideal point.

        Returns:
            np.ndarray: The translated front.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        translated_front = np.subtract(front, ideal)
        return translated_front

    def generate_preference_learning(
        self, ideal_point, translated_front, assigned_vectors
    ):
        """
        Generate preference information during the learning phase.

        The preference is generated according to the selected preference type:
        - 'reference_point': Returns a reference point.
        - 'ranges': Returns a preferred range.
        - 'preferred_solutions': Returns preferred solutions.

        Args:
            ideal_point (np.ndarray): The ideal point.
            translated_front (np.ndarray): The translated solution front.
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.

        Returns:
            dict or np.ndarray: The generated preference information.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        if self.preference_type == "reference_point":
            return self.generate_reference_point_learning(
                ideal_point, translated_front, assigned_vectors
            )
        elif self.preference_type == "ranges":
            return self.generate_ranges_learning(
                ideal_point, translated_front, assigned_vectors
            )
        elif self.preference_type == "preferred_solutions":
            return self.generate_preferred_solutions_learning(
                ideal_point, translated_front, assigned_vectors
            )

        else:
            raise ValueError(
                f"Invalid preference type: {self.preference_type}. "
                "Valid options are 'reference_point', 'ranges', 'preferred_solutions', or 'non_preferred_solutions'."
            )

    def generate_preference_decision(
        self, ideal_point, translated_front, assigned_vectors, max_assigned_vector
    ):
        """
        Generate preference information during the decision phase.

        The preference is generated according to the selected preference type:
        - 'reference_point': Returns a reference point.
        - 'ranges': Returns a preferred range.
        - 'preferred_solutions': Returns preferred solutions.

        Args:
            ideal_point (np.ndarray): The ideal point.
            translated_front (np.ndarray): The translated solution front.
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.
            max_assigned_vector (int): Index of the reference vector with the maximum assigned solutions.

        Returns:
            dict or np.ndarray: The generated preference information.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        if self.preference_type == "reference_point":
            return self.generate_reference_point_decision(
                ideal_point,
                translated_front,
                assigned_vectors,
                max_assigned_vector,
            )
        elif self.preference_type == "ranges":
            return self.generate_ranges_decision(
                ideal_point, translated_front, assigned_vectors, max_assigned_vector
            )
        elif self.preference_type == "preferred_solutions":
            return self.generate_preferred_solutions_decision(
                ideal_point, translated_front, assigned_vectors, max_assigned_vector
            )
        else:
            raise ValueError(
                f"Invalid preference type: {self.preference_type}. "
                "Valid options are 'reference_point', 'ranges', 'preferred_solutions', or 'non_preferred_solutions'."
            )

    def get_max_assigned_vector(self, assigned_vectors):
        """
        Find the reference vector with the maximum number of assigned solutions.

        Args:
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.

        Returns:
            np.ndarray: Indices of the reference vector(s) with the maximum assignments.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
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

    def generate_reference_point_learning(
        self, ideal_point, translated_front, assigned_vectors
    ):
        """
        Generate a reference point for the learning phase.

        The reference point is based on the solution assigned to the reference vector with the minimum
        number of assigned solutions and closest to the origin.

        Args:
            ideal_point (np.ndarray): The ideal point.
            translated_front (np.ndarray): The translated solution front.
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.

        Returns:
            dict: The generated reference point.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        ideal_cf = ideal_point
        translated_cf = translated_front
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
        )
        sub_population_fitness = translated_cf[sub_population_index]
        sub_pop_fitness_magnitude = np.sqrt(
            np.sum(np.power(sub_population_fitness, 2), axis=1)
        )
        minidx = np.where(
            sub_pop_fitness_magnitude == np.nanmin(sub_pop_fitness_magnitude)
        )
        distance_selected = sub_pop_fitness_magnitude[minidx]
        reference_point = (
            distance_selected[0] * self.reference_vectors[min_assigned_vector[0]]
        )
        reference_point = np.squeeze(reference_point + ideal_cf)
        return dict(zip(self.target_symbols, reference_point))

    def generate_reference_point_decision(
        self, ideal_point, translated_front, assigned_vectors, max_assigned_vector
    ):
        """
        Generate a reference point for the decision phase.

        The reference point is based on the solution assigned to the reference vector with the maximum
        number of assigned solutions and closest to the origin.

        Args:
            ideal_point (np.ndarray): The ideal point.
            translated_front (np.ndarray): The translated solution front.
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.
            max_assigned_vector (int): Index of the reference vector with the maximum assigned solutions.

        Returns:
            dict: The generated reference point.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        ideal_cf = ideal_point
        translated_cf = translated_front
        sub_population_index = np.atleast_1d(
            np.squeeze(np.where(assigned_vectors == max_assigned_vector))
        )
        sub_population_fitness = translated_cf[sub_population_index]
        sub_pop_fitness_magnitude = np.sqrt(
            np.sum(np.power(sub_population_fitness, 2), axis=1)
        )
        minidx = np.where(
            sub_pop_fitness_magnitude == np.nanmin(sub_pop_fitness_magnitude)
        )
        distance_selected = sub_pop_fitness_magnitude[minidx]
        reference_point = (
            distance_selected[0] * self.reference_vectors[max_assigned_vector]
        )
        reference_point = np.squeeze(reference_point + ideal_cf)
        return dict(zip(self.target_symbols, reference_point))

    def generate_ranges_learning(self, ideal_point, translated_front, assigned_vectors):
        """
        Generate the preferred ranges for the learning phase.

        Args:
            ideal_point (np.ndarray): The ideal point.
            translated_front (np.ndarray): The translated solution front.
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.

        Returns:
            tuple: (preferred_range, reference_point), where preferred_range is an array of ranges and reference_point is the center.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
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
        )
        sub_population_fitness = translated_front[sub_population_index]
        sub_pop_fitness_magnitude = np.sqrt(
            np.sum(np.power(sub_population_fitness, 2), axis=1)
        )
        minidx = np.where(
            sub_pop_fitness_magnitude == np.nanmin(sub_pop_fitness_magnitude)
        )
        distance_selected = sub_pop_fitness_magnitude[minidx]
        reference_point = (
            distance_selected[0] * self.reference_vectors[min_assigned_vector[0]]
        )
        distance = min(
            np.linalg.norm(reference_point - i) for i in sub_population_fitness
        )
        reference_point = np.squeeze(reference_point + ideal_point)
        temp = reference_point - distance
        temp2 = reference_point + distance

        true_ideal = self.problem.get_ideal_point()
        true_nadir = self.problem.get_nadir_point()

        for i in range(reference_point.shape[0]):
            if reference_point[i] < true_ideal[i]:
                reference_point[i] = true_ideal[i]
            if reference_point[i] > true_nadir[i]:
                reference_point[i] = true_nadir[i]
            if temp[i] < true_ideal[i]:
                temp[i] = true_ideal[i]
            if temp[i] > true_nadir[i]:
                temp[i] = true_nadir[i]
            if temp2[i] < true_ideal[i]:
                temp2[i] = true_ideal[i]
            if temp2[i] > true_nadir[i]:
                temp2[i] = true_nadir[i]

        preferred_range = np.vstack((temp, temp2)).T
        return preferred_range, reference_point

    def generate_ranges_decision(
        self, ideal_point, translated_front, assigned_vectors, max_assigned_vector
    ):
        """
        Generate the preferred ranges for the decision phase.

        Args:
            ideal_point (np.ndarray): The ideal point.
            translated_front (np.ndarray): The translated solution front.
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.
            max_assigned_vector (int): Index of the reference vector with the maximum assigned solutions.

        Returns:
            tuple: (preferred_range, reference_point), where preferred_range is an array of ranges and reference_point is the center.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        sub_population_index = np.atleast_1d(
            np.squeeze(np.where(assigned_vectors == max_assigned_vector))
        )
        sub_population_fitness = translated_front[sub_population_index]
        sub_pop_fitness_magnitude = np.sqrt(
            np.sum(np.power(sub_population_fitness, 2), axis=1)
        )
        minidx = np.where(
            sub_pop_fitness_magnitude == np.nanmin(sub_pop_fitness_magnitude)
        )
        distance_selected = sub_pop_fitness_magnitude[minidx]
        reference_point = (
            distance_selected[0] * self.reference_vectors[max_assigned_vector]
        )
        distance = min(
            np.linalg.norm(reference_point - i) for i in sub_population_fitness
        )
        reference_point = np.squeeze(reference_point + ideal_point)
        reference_point = np.squeeze(reference_point - distance)
        temp = reference_point - distance
        temp2 = reference_point + distance

        true_ideal = self.problem.get_ideal_point()
        true_nadir = self.problem.get_nadir_point()

        for i in range(reference_point.shape[0]):
            if reference_point[i] < true_ideal[i]:
                reference_point[i] = true_ideal[i]
            if reference_point[i] > true_nadir[i]:
                reference_point[i] = true_nadir[i]
            if temp[i] < true_ideal[i]:
                temp[i] = true_ideal[i]
            if temp[i] > true_nadir[i]:
                temp[i] = true_nadir[i]
            if temp2[i] < true_ideal[i]:
                temp2[i] = true_ideal[i]
            if temp2[i] > true_nadir[i]:
                temp2[i] = true_nadir[i]

        preferred_range = np.vstack((temp, temp2)).T
        return preferred_range, reference_point

    def generate_preferred_solutions_learning(
        self, ideal_point, translated_front, assigned_vectors
    ):
        """
        Generate the preferred solutions during the learning phase.

        Args:
            ideal_point (np.ndarray): The ideal point.
            translated_front (np.ndarray): The translated solution front.
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.

        Returns:
            np.ndarray: The preferred solutions.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
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
        )
        sub_population_fitness = translated_front[sub_population_index]
        sub_pop_fitness_magnitude = np.sqrt(
            np.sum(np.power(sub_population_fitness, 2), axis=1)
        )
        solution_selected = sub_population_fitness
        preferred_solution = np.squeeze(solution_selected + ideal_point)
        return preferred_solution

    def generate_preferred_solutions_decision(
        self, ideal_point, translated_front, assigned_vectors, max_assigned_vector
    ):
        """
        Generate the preferred solutions during the decision phase.

        Args:
            ideal_point (np.ndarray): The ideal point.
            translated_front (np.ndarray): The translated solution front.
            assigned_vectors (np.ndarray): Indices of assigned reference vectors.
            max_assigned_vector (int): Index of the reference vector with the maximum assigned solutions.

        Returns:
            np.ndarray: The preferred solutions.

        Reference:
            Afsar, B., Miettinen, K., & Ruiz, A. B. (2021).
            An Artificial Decision Maker for Comparing Reference Point Based Interactive Evolutionary Multiobjective Optimization Methods.
        """
        sub_population_index = np.atleast_1d(
            np.squeeze(np.where(assigned_vectors == max_assigned_vector))
        )
        sub_population_fitness = translated_front[sub_population_index]
        sub_pop_fitness_magnitude = np.sqrt(
            np.sum(np.power(sub_population_fitness, 2), axis=1)
        )
        minidx = np.argpartition(sub_pop_fitness_magnitude, 4)
        solution_selected = sub_population_fitness[minidx[:4]]
        preferred_solution = np.squeeze(solution_selected + ideal_point)
        return preferred_solution
