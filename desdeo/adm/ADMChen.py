from desdeo.adm import BaseADM
from desdeo.problem.schema import Problem
from desdeo.tools import payoff_table_method, non_dominated_sorting as nds
import numpy as np
from typing import Optional


"""ADMChen.py

This module implements the Artificial Decision Maker (ADM) proposed by Chen et al.

References:
    Chen, L., Miettinen, K., Xin, B., & Ojalehto, V. (2023). 
    Comparing reference point based interactive multiobjective 
    optimization methods without a human decision maker.
    European Journal of Operational Research, 307(1), 327-345.

IMPORTANT: This module is WIP. There are multiple things not clear in the article that need further clarification.
"""


class ADMChen(BaseADM):
    """
    Artificial Decision Maker implementation based on Chen et al. (2023).

    This ADM simulates human decision-making behavior in interactive multiobjective
    optimization by operating in two phases: learning and decision-making. During the
    learning phase, it explores the Pareto front by identifying neighboring solutions
    with maximum normalized Euclidean distance. In the decision phase, it selects
    solutions based on a utility function that minimizes disutility.

    Attributes:
        true_ideal (np.ndarray): True ideal point computed from the problem.
        true_nadir (np.ndarray): True nadir point computed from the problem.
        num_objectives (int): Number of objectives in the problem.
        num_variables (int): Number of variables in the problem.
        preference (np.ndarray): Current reference point preference.
        weights (np.ndarray): Objective weights (equal weights by default).
        UF_max (float): Maximum utility function value on the Pareto front.
        UF_opt (float): Optimal (minimum) utility function value on the Pareto front.
        extreme_solutions (np.ndarray): Extreme solutions from the Pareto front.

    Args:
        problem (Problem): The multiobjective optimization problem.
        it_learning_phase (int): Number of iterations for the learning phase.
        it_decision_phase (int): Number of iterations for the decision phase.
        pareto_front (np.ndarray): Known Pareto front solutions for initialization.
        initial_reference_point (Optional[np.ndarray]): Initial reference point.
            If None, a random point between ideal and nadir is generated.

    Raises:
        ValueError: If the initial reference point is not between ideal and nadir points.

    Example:
        >>> problem = Problem(...)  # Define your problem
        >>> pareto_front = np.array([[1, 2], [2, 1], [1.5, 1.5]])
        >>> adm = ADMChen(problem, it_learning_phase=5, it_decision_phase=3,
        ...               pareto_front=pareto_front)
        >>> preference = adm.get_next_preference(current_front)
    """

    def __init__(
        self,
        problem: Problem,
        it_learning_phase: int,
        it_decision_phase: int,
        pareto_front: np.ndarray,
        initial_reference_point: Optional[np.ndarray] = None,
    ):
        # CHANGE 1: payoff_table_method returns dictionaries {objective_name: value}, not np.ndarray.
        # The values are extracted and converted to arrays so arithmetic operations
        # can be performed in utility_function (zstar - eps previously failed with TypeError: 'dict' - float).
        ideal_dict, nadir_dict = payoff_table_method(problem)
        self.true_ideal = np.array(list(ideal_dict.values()))
        self.true_nadir = np.array(list(nadir_dict.values()))

        problem = problem.update_ideal_and_nadir(
            new_ideal=ideal_dict, new_nadir=nadir_dict
        )
        super().__init__(problem, it_learning_phase, it_decision_phase)

        self.num_objectives = len(problem.objectives)
        self.num_variables = len(problem.variables)

        self.preference = self.generate_initial_preference(initial_reference_point)
        self.iteration_counter += 1

        # NOTE: In the original article, weights were set manually
        self.weights = np.ones(self.num_objectives) / self.num_objectives

        self.UF_max = np.max([
            self.utility_function(sol, self.true_ideal, self.true_nadir, self.weights)
            for sol in pareto_front
        ])
        self.UF_opt = np.min([
            self.utility_function(sol, self.true_ideal, self.true_nadir, self.weights)
            for sol in pareto_front
        ])

        self.extreme_solutions = self.get_extreme_solutions(pareto_front)

    def generate_initial_preference(
        self,
        initial_reference_point: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Generate the initial reference point for the ADM.

        If an initial reference point is provided, it validates that the point lies
        between the ideal and nadir points. Otherwise, generates a random point
        within the feasible objective space.

        Args:
            initial_reference_point (Optional[np.ndarray]): User-specified initial
                reference point. Must be between ideal and nadir points.

        Returns:
            np.ndarray: Valid initial reference point.

        Raises:
            ValueError: If the provided reference point is outside the valid range.
        """
        if initial_reference_point is not None:
            # CHANGE 2: Chained comparison (a <= b <= c) does not work with NumPy arrays
            # in modern versions—it raises ValueError: "The truth value of an array is ambiguous".
            # It is replaced with two separate np.all() calls, which is the correct approach.
            if not (
                np.all(initial_reference_point >= self.true_ideal)
                and np.all(initial_reference_point <= self.true_nadir)
            ):
                raise ValueError(
                    "Initial reference point must be between the ideal and nadir points."
                )
            return initial_reference_point
        else:
            return np.array([
                np.random.uniform(min_val, max_val)
                for min_val, max_val in zip(
                    self.problem.get_ideal_point().values(),
                    self.problem.get_nadir_point().values(),
                )
            ])

    def get_next_preference(self, front: np.ndarray) -> np.ndarray:
        """
        Get the next preference (reference point) based on the current iteration phase.

        Args:
            front (np.ndarray): Current Pareto front approximation with shape
                (n_solutions, n_objectives).

        Returns:
            np.ndarray: Next reference point for the interactive method.
        """
        if self.iteration_counter < self.it_learning_phase:
            self.preference = self.generate_preference_learning(front)
        else:
            self.preference = self.generate_preference_decision(front)
        self.iteration_counter += 1
        return self.preference

    def get_extreme_solutions(self, front: np.ndarray) -> np.ndarray:
        """
        Extract extreme solutions from the Pareto front.

        An extreme solution is defined as the objective vector that minimizes
        one of the objective functions on the Pareto front.

        Args:
            front (np.ndarray): Pareto front with shape (n_solutions, n_objectives).

        Returns:
            np.ndarray: Array of extreme solutions with shape (n_objectives, n_objectives).
        """
        extreme_solutions = []
        for i in range(front.shape[1]):
            idx_min_i = np.argmin(front[:, i])
            extreme_solutions.append(front[idx_min_i])
        return np.array(extreme_solutions)

    @staticmethod
    def normalized_euclidean_distance(
        za: np.ndarray,
        zb: np.ndarray,
        znad: np.ndarray,
        zstar: np.ndarray,
        eps: Optional[float] = None
    ) -> float:
        """
        Compute normalized Euclidean distance between two solutions.

        Args:
            za (np.ndarray): First solution vector.
            zb (np.ndarray): Second solution vector.
            znad (np.ndarray): Nadir point.
            zstar (np.ndarray): Ideal point.
            eps (Optional[float]): Small positive value for utopian shift. Defaults to 1e-6.

        Returns:
            float: Normalized Euclidean distance between za and zb.
        """
        za, zb, znad, zstar = map(np.asarray, (za, zb, znad, zstar))
        if eps is None:
            eps = 1e-6
        if np.isscalar(eps):
            eps = np.full_like(zstar, eps, dtype=float)

        z_utopian = zstar - eps
        denom = znad - z_utopian
        denom = np.where(denom <= 0, 1e-12, denom)
        diff = (za - zb) / denom
        return np.sqrt(np.sum(diff**2))

    @staticmethod
    def are_neighbors(za: np.ndarray, zb: np.ndarray, solutions: np.ndarray) -> bool:
        """
        Check if two solutions are neighbors in the context of a solution set.

        Args:
            za (np.ndarray): First solution vector.
            zb (np.ndarray): Second solution vector.
            solutions (np.ndarray): Complete solution set.

        Returns:
            bool: True if za and zb are neighbors, False otherwise.
        """
        za = np.asarray(za)
        zb = np.asarray(zb)
        z_ab = np.minimum(za, zb)

        for i in range(len(solutions)):
            zc = solutions[i]
            if np.array_equal(zc, za) or np.array_equal(zc, zb):
                continue
            if nds.dominates(z_ab, zc):
                return False
        return True

    def generate_preference_learning(self, front: np.ndarray) -> np.ndarray:
        """
        Generate preference during the learning phase through systematic exploration.

        Args:
            front (np.ndarray): Current Pareto front with shape (n_solutions, n_objectives).

        Returns:
            np.ndarray: New reference point derived from the most distant neighbors.

        TODO:
            Validate that the same region has not been selected before to
            avoid redundant exploration.
        """
        extended_set = np.append(front, self.extreme_solutions, axis=0)

        neighbors_1 = []
        neighbors_2 = []
        euclidean_distances = []

        for i in range(extended_set.shape[0] - 1):
            z1 = extended_set[i, :]
            for j in range(i + 1, extended_set.shape[0]):
                z2 = extended_set[j, :]
                if self.are_neighbors(z1, z2, extended_set):
                    neighbors_1.append(z1)
                    neighbors_2.append(z2)
                    euclidean_distances.append(
                        self.normalized_euclidean_distance(
                            z1, z2, self.true_nadir, self.true_ideal
                        )
                    )

        max_distance_idx = np.argmax(euclidean_distances)
        new_ref_point = np.minimum(
            neighbors_1[max_distance_idx],
            neighbors_2[max_distance_idx]
        )
        return new_ref_point

    def utility_function(
        self,
        z: np.ndarray,
        zstar: np.ndarray,
        znad: np.ndarray,
        weight: np.ndarray,
        type: str = 'deterministic',
        eps: Optional[float] = None
    ) -> float:
        """
        Compute the utility function value for a given solution.

        Args:
            z (np.ndarray): Solution vector.
            zstar (np.ndarray): Ideal point.
            znad (np.ndarray): Nadir point.
            weight (np.ndarray): Objective weights.
            type (str): 'deterministic' or 'random'. Defaults to 'deterministic'.
            eps (Optional[float]): Utopian shift. Defaults to 1e-6.

        Returns:
            float: Utility function value (lower is better).
        """
        z, znad, zstar, weight = map(np.asarray, (z, znad, zstar, weight))
        if eps is None:
            eps = 1e-6
        if np.isscalar(eps):
            eps = np.full_like(zstar, eps, dtype=float)

        z_utopian = zstar - eps
        denom = znad - z_utopian
        denom = np.where(denom <= 0, 1e-12, denom)
        diff = weight * ((z - z_utopian) / denom)
        U_minus = np.max(diff)

        if type == 'random':
            sigma = (self.UF_max - self.UF_opt) * 0.2 / (2 ** (self.it_decision_phase - 1))
            noise = np.random.uniform(low=0, high=sigma)
            U_minus = noise + U_minus

        return U_minus

    def generate_preference_decision(self, front: np.ndarray) -> np.ndarray:
        """
        Generate preference during the decision phase by selecting the best solution.

        Args:
            front (np.ndarray): Current Pareto front with shape (n_solutions, n_objectives).

        Returns:
            np.ndarray: The solution with minimum disutility as the preferred reference point.
        """
        min_disutility = np.inf
        preferred_solution = None

        for solution in front:
            disutility = self.utility_function(
                solution, self.true_ideal, self.true_nadir, self.weights
            )
            if disutility < min_disutility:
                min_disutility = disutility
                preferred_solution = solution

        return preferred_solution