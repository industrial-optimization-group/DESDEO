from desdeo.adm import BaseADM
from desdeo.problem.schema import Problem
from desdeo.tools import payoff_table_method, non_dominated_sorting as nds
import numpy as np

"""ADMChen.py
This module implements the ADM proposed by Chen et al.

References:
Chen, L., Miettinen, K., Xin, B., & Ojalehto, V. (2023). 
Comparing reference point based interactive multiobjective 
optimization methods without a human decision maker.
"""


class ADMChen(BaseADM):
    def __init__(
        self,
        problem: Problem,
        it_learning_phase: int,
        it_decision_phase: int,
        initial_reference_point: np.ndarray = None,
    ):
        self.true_ideal, self.true_nadir = payoff_table_method(problem)
        problem = problem.update_ideal_and_nadir(
            new_ideal=self.true_ideal, new_nadir=self.true_nadir
        )
        super().__init__(problem, it_learning_phase, it_decision_phase)
        self.num_objectives = len(problem.objectives)
        self.num_variables = len(problem.variables)
        self.preference = self.generate_initial_preference(initial_reference_point)
        self.iteration_counter += 1

    def generate_initial_preference(self, initial_reference_point=None):
        # If there is an initial reference point, validate that it is between ideal and nadir
        if initial_reference_point is not None:
            if not (
                self.true_ideal <= initial_reference_point <= self.true_nadir
            ).all():
                raise ValueError(
                    "Initial reference point must be between the ideal and nadir points."
                )
            return initial_reference_point
        else:
            return np.array(
                [
                    np.random.uniform(min_val, max_val)
                    for min_val, max_val in zip(
                        self.problem.get_ideal_point().values(),
                        self.problem.get_nadir_point().values(),
                    )
                ]
            )

    def get_next_preference(self, front):
        extreme_solutions = self.get_extreme_solutions(front)
        if self.iteration_counter < self.it_learning_phase:
            self.preference = self.generate_preference_learning(
                front, extreme_solutions
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

    def get_extreme_solutions(self, front: np.ndarray) -> np.ndarray:
        """
        Get the extreme solutions of the solution set. An extreme point is
        defined as the objective vector which has the minimum value of one of the
        objective functions on the Pareto front.
        """
        # Find the extreme solutions in the given front
        extreme_solutions = []
        for i in range(front.shape[1]):
            idx_min_i = np.argmin(front[:, i])
            extreme_solutions.append(front[idx_min_i])
        return np.array(extreme_solutions)

    def normalized_euclidean_distance(za, zb, znad, zstar, eps=None):
        """
        Compute normalized Euclidean distance between two solutions za and zb.

        Parameters
        ----------
        za, zb : array-like, shape (k,)
            Two solution vectors.
        znad : array-like, shape (k,)
            Nadir point (worst values for each objective).
        zstar : array-like, shape (k,)
            Ideal point (best values for each objective).
        eps : array-like or float, optional
            Small positive value(s) for utopian shift. If None, defaults to 1e-6.
        """
        za, zb, znad, zstar = map(np.asarray, (za, zb, znad, zstar))
        if eps is None:
            eps = 1e-6
        if np.isscalar(eps):
            eps = np.full_like(zstar, eps, dtype=float)

        # Compute utopian point
        z_utopian = zstar - eps

        # Denominator (znad - z**)
        denom = znad - z_utopian

        # Avoid division by 0 (in case znad ≈ z**)
        denom = np.where(denom <= 0, 1e-12, denom)

        # Normalized Euclidean distance
        diff = (za - zb) / denom
        return np.sqrt(np.sum(diff**2))

    def are_neighbors(za, zb, solutions):
        """
        Check if za and zb are neighbors with respect to solutions.
        solutions should be a 2D numpy array: shape (n_solutions, n_objectives)
        """
        za = np.asarray(za)
        zb = np.asarray(zb)
        z_ab = np.minimum(za, zb)  # componentwise minimum

        for i in range(len(solutions)):
            zc = solutions[i]
            # Skip comparing to za and zb themselves
            if np.array_equal(zc, za) or np.array_equal(zc, zb):
                continue
            if nds.dominates(z_ab, zc):
                return False
        return True

    def generate_preference_learning(self, front, extreme_solutions: np.ndarray):
        # Add the extreme points to the front
        """Learning phase where reference points are iteratively updated."""
        # extend the front with extreme solutions as rows
        extended_set = np.append(front, extreme_solutions, axis=0)

        neighbors_1 = []
        neighbors_2 = []
        Eucdist = []

        # Loop through pairs of solutions in the extended set
        for i in range(extended_set.shape[0] - 1):
            z1 = extended_set[i, :]
            for j in range(i + 1, extended_set.shape[0]):
                z2 = extended_set[j, :]
                if self.are_neighbors(z1, z2, extended_set):
                    neighbors_1.append(z1)
                    neighbors_2.append(z2)
                    Eucdist.append(
                        self.normalized_euclidean_distance(
                            z1, z2, self.true_nadir, self.true_ideal
                        )
                    )
            # Select the pair with the biggest normalized distance
        # return newrefpoint

    def generate_preference_decision(self):
        return super().generate_preference_decision()
