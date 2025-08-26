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
        # Initialize problem with true ideal and nadir points
        self.true_ideal, self.true_nadir = payoff_table_method(problem)
        problem = problem.update_ideal_and_nadir(
            new_ideal=self.true_ideal, new_nadir=self.true_nadir
        )
        super().__init__(problem, it_learning_phase, it_decision_phase)
        
        # Store problem dimensions
        self.num_objectives = len(problem.objectives)
        self.num_variables = len(problem.variables)
        
        # Generate initial preference
        self.preference = self.generate_initial_preference(initial_reference_point)
        self.iteration_counter += 1
        
        # Initialize equal weights for all objectives
        # NOTE: In the original article, weights were set manually
        self.weights = np.ones(self.num_objectives) / self.num_objectives
        
        # Compute utility function bounds on the Pareto front
        self.UF_max = np.max([
            self.utility_function(sol, self.true_ideal, self.true_nadir, self.weights) 
            for sol in pareto_front
        ])
        self.UF_opt = np.min([
            self.utility_function(sol, self.true_ideal, self.true_nadir, self.weights) 
            for sol in pareto_front
        ])
        
        # Store extreme solutions from the 
        self.extreme_solutions = self.get_extreme_solutions(pareto_front)

    def generate_initial_preference(self, initial_reference_point: Optional[np.ndarray] = None) -> np.ndarray:
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
            if not (self.true_ideal <= initial_reference_point <= self.true_nadir).all():
                raise ValueError(
                    "Initial reference point must be between the ideal and nadir points."
                )
            return initial_reference_point
        else:
            # Generate random reference point between ideal and nadir
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
        
        This method determines whether the ADM is in the learning or decision phase
        and calls the appropriate preference generation method.
        
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
        one of the objective functions on the Pareto front. These solutions
        represent the boundaries of the achievable objective space.
        
        Args:
            front (np.ndarray): Pareto front with shape (n_solutions, n_objectives).
        
        Returns:
            np.ndarray: Array of extreme solutions with shape (n_objectives, n_objectives).
                Each row represents an extreme solution for one objective.
        
        Example:
            For a 2-objective problem with front = [[1, 3], [2, 2], [3, 1]]:
            - Extreme for obj 1: [1, 3] (min value 1 in first objective)
            - Extreme for obj 2: [3, 1] (min value 1 in second objective)
        """
        extreme_solutions = []
        for i in range(front.shape[1]):  # For each objective
            idx_min_i = np.argmin(front[:, i])  # Find solution with minimum value
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
        
        The normalization is performed using the range between the utopian point
        (ideal - eps) and the nadir point. This ensures that the distance metric
        is scale-independent across different objectives.
        
        Args:
            za (np.ndarray): First solution vector of shape (n_objectives,).
            zb (np.ndarray): Second solution vector of shape (n_objectives,).
            znad (np.ndarray): Nadir point (worst values) of shape (n_objectives,).
            zstar (np.ndarray): Ideal point (best values) of shape (n_objectives,).
            eps (Optional[float]): Small positive value for utopian shift. 
                Defaults to 1e-6 if None.
        
        Returns:
            float: Normalized Euclidean distance between za and zb.
            
        Note:
            The utopian point is computed as zstar - eps to ensure strict
            improvement over the ideal point. Division by zero is avoided
            by replacing zero denominators with 1e-12.
        """
        za, zb, znad, zstar = map(np.asarray, (za, zb, znad, zstar))
        if eps is None:
            eps = 1e-6
        if np.isscalar(eps):
            eps = np.full_like(zstar, eps, dtype=float)

        # Compute utopian point (strictly better than ideal)
        z_utopian = zstar - eps

        # Compute normalization denominator
        denom = znad - z_utopian

        # Avoid division by zero when nadir ≈ utopian
        denom = np.where(denom <= 0, 1e-12, denom)

        # Compute normalized difference and Euclidean distance
        diff = (za - zb) / denom
        return np.sqrt(np.sum(diff**2))

    @staticmethod
    def are_neighbors(za: np.ndarray, zb: np.ndarray, solutions: np.ndarray) -> bool:
        """
        Check if two solutions are neighbors in the context of a solution set.
        
        Two solutions za and zb are considered neighbors if their componentwise
        minimum is not dominated by any other solution in the set. 
        
        Args:
            za (np.ndarray): First solution vector of shape (n_objectives,).
            zb (np.ndarray): Second solution vector of shape (n_objectives,).
            solutions (np.ndarray): Complete solution set with shape 
                (n_solutions, n_objectives).
        
        Returns:
            bool: True if za and zb are neighbors, False otherwise.
            
        Note:
            The componentwise minimum z_ab = min(za, zb) represents a point
            that is at least as good as both za and zb in all objectives.
            If any other solution dominates z_ab, then za and zb are not
            considered neighbors.
        """
        za = np.asarray(za)
        zb = np.asarray(zb)
        z_ab = np.minimum(za, zb)  # Componentwise minimum

        for i in range(len(solutions)):
            zc = solutions[i]
            # Skip comparing to za and zb themselves
            if np.array_equal(zc, za) or np.array_equal(zc, zb):
                continue
            if nds.dominates(z_ab, zc):
                return False
        return True

    def generate_preference_learning(self, front: np.ndarray) -> np.ndarray:
        """
        Generate preference during the learning phase through systematic exploration.
        
        The learning phase explores the Pareto front by identifying neighboring
        solution pairs with the maximum normalized Euclidean distance. 
        
        Args:
            front (np.ndarray): Current Pareto front with shape (n_solutions, n_objectives).
        
        Returns:
            np.ndarray: New reference point derived from the most distant neighbors.
            
        Note:
            The reference point is set as the componentwise minimum of the
            most distant neighboring pair, which represents an aspirational
            point that is better than both neighbors in all objectives.
            
        TODO:
            Validate that the same region has not been selected before to
            avoid redundant exploration.
        """
        # Extend front with extreme solutions for comprehensive exploration
        extended_set = np.append(front, self.extreme_solutions, axis=0)

        neighbors_1 = []
        neighbors_2 = []
        euclidean_distances = []

        # Find all neighboring pairs and compute their distances
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
        
        # Select the pair with maximum distance for exploration
        max_distance_idx = np.argmax(euclidean_distances)

        # Generate reference point as componentwise minimum of the distant pair
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
        
        The utility function measures the maximum weighted normalized distance
        from the utopian point. Lower values indicate better solutions.

        Args:
            z (np.ndarray): Solution vector of shape (n_objectives,).
            zstar (np.ndarray): Ideal point of shape (n_objectives,).
            znad (np.ndarray): Nadir point of shape (n_objectives,).
            weight (np.ndarray): Objective weights of shape (n_objectives,).
            type (str): Type of utility function. Options: 'deterministic', 'random'.
                Defaults to 'deterministic'.
            eps (Optional[float]): Small positive value for utopian shift.
                Defaults to 1e-6.
        
        Returns:
            float: Utility function value (lower is better).
            
        Note:
            When type='random', Gaussian noise is added with standard deviation
            that decreases over iterations to simulate learning behavior.
            The noise magnitude is based on the utility function range.
        """
        z, znad, zstar, weight = map(np.asarray, (z, znad, zstar, weight))
        if eps is None:
            eps = 1e-6
        if np.isscalar(eps):
            eps = np.full_like(zstar, eps, dtype=float)

        # Compute utopian point (strictly better than ideal)
        z_utopian = zstar - eps

        # Compute normalization denominator
        denom = znad - z_utopian

        # Avoid division by zero
        denom = np.where(denom <= 0, 1e-12, denom)

        # Compute weighted normalized distances
        diff = weight * ((z - z_utopian) / denom)
        U_minus = np.max(diff)  # Chebyshev scalarization

        # Add random component if requested
        if type == 'random':
            # Noise decreases over iterations to simulate learning
            sigma = (self.UF_max - self.UF_opt) * 0.2 / (2 ** (self.it_decision_phase - 1))
            noise = np.random.uniform(low=0, high=sigma)
            U_minus = noise + U_minus

        return U_minus

    def generate_preference_decision(self, front: np.ndarray) -> np.ndarray:
        """
        Generate preference during the decision phase by selecting the best solution.
        
        In the decision phase, the ADM acts more decisively by evaluating all
        solutions in the current front using the utility function and selecting
        the one with minimum disutility (best utility value). This represents
        the final decision-making behavior after the learning phase.
        
        Args:
            front (np.ndarray): Current Pareto front with shape (n_solutions, n_objectives).
        
        Returns:
            np.ndarray: The solution with minimum disutility as the preferred reference point.
            
        Note:
            The returned solution represents the ADM's final preference and
            should be close to the decision maker's most preferred solution.
        """
        min_disutility = np.inf
        preferred_solution = None

        # Evaluate all solutions and find the one with minimum disutility
        for solution in front:
            disutility = self.utility_function(
                solution, self.true_ideal, self.true_nadir, self.weights
            )
            if disutility < min_disutility:
                min_disutility = disutility
                preferred_solution = solution

        return preferred_solution
