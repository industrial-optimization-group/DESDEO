import numpy as np
from scipy.spatial import Delaunay
from timeit import default_timer as timer
from typing import Optional

from scipy.spatial.qhull import QhullError

import itertools

from scipy.optimize import linprog


def inherently_nondominated(
    A: np.ndarray, epsilon: Optional[float] = 1e-06, method: Optional[str] = "highs"
) -> bool:
    return not polytope_dominates(A, A, epsilon, method)


def polytope_dominates(
    k1: np.ndarray,
    k2: np.ndarray,
    epsilon: Optional[float] = 1e-6,
    method: Optional[str] = "highs",
) -> bool:
    k1 = np.atleast_2d(k1)
    k2 = np.atleast_2d(k2)
    a, k = k1.shape
    b = k2.shape[0]

    # First optimization problem
    coef = np.hstack((np.ones(1), np.zeros(a + b)))
    lower_bounds = np.hstack((np.array([None]), np.zeros(a + b)))
    upper_bounds = np.hstack((np.array([None]), np.ones(a + b)))
    bounds = np.vstack((lower_bounds, upper_bounds)).T

    # Constructing the matrix A_ub in the constraint A_ub x <= b_ub
    A1 = np.hstack((-np.ones((k, 1)), k1.T, -k2.T))
    A2 = np.hstack((np.zeros((1, 1)), np.ones((1, a)), np.zeros((1, b))))
    A3 = np.hstack((np.zeros((1, 1)), np.zeros((1, a)), np.ones((1, b))))
    A_ub = np.vstack((A1, np.zeros((2, a + b + 1))))
    b_ub = np.zeros(k + 2)

    A_eq = np.vstack(
        (np.zeros((k, a + b + 1)), A2, A3)
    )  # Add k rows for correct size, will be ignored
    b_eq = np.hstack((np.zeros(k), np.ones(2)))

    res = linprog(coef, A_ub, b_ub, A_eq, b_eq, bounds, method=method)

    if not res["success"]:
        print("unsuccessful optimization in first problem.")
    if res["fun"] < -epsilon:
        return True

    if abs(res["fun"]) <= epsilon:
        lower_bounds = np.zeros(a + b)
        upper_bounds = np.ones(a + b)
        bounds = np.vstack((lower_bounds, upper_bounds)).T

        coef = np.hstack(([np.sum(k1, axis=1), -np.sum(k2, axis=1)]))
        A1 = np.hstack((np.ones((1, a)), np.zeros((1, b))))
        A2 = np.hstack((np.zeros((1, a)), np.ones((1, b))))
        A3 = np.hstack((k1.T, -k2.T))

        A_eq = np.vstack((A1, A2, np.zeros((k, a + b))))
        b_eq = np.hstack((np.ones(2), np.zeros(k)))

        A_ub = np.vstack((np.zeros((2, a + b)), A3))
        b_ub = np.zeros((k + 2, 1))

        res = linprog(coef, A_ub, b_ub, A_eq, b_eq, bounds, method=method)

        if not res["success"]:
            print("unsuccessful optimization in second problem.")
        if res["fun"] < -epsilon:
            return True
    return False


def generate_polytopes(simplices: np.ndarray) -> np.ndarray:
    simplices = np.sort(simplices)
    a, b = simplices.shape
    k = np.max(simplices)  # point count
    F = (np.ones((b, k + 1)) * np.arange(k + 1)).T
    for i in range(a):
        for j in range(2, b + 1):
            # All combinations of size j from row i
            addition = np.array(list(itertools.combinations(simplices[i], j)))
            # Add all combinations to F, so that we repeat the value at index 0 until enough values
            chunks = addition[:, 0].shape[0]  # How many chunks to split into
            repeated = np.split(
                np.repeat(addition[:, 0], b - j), chunks
            )  # Repeat the values at index 0
            addition = np.hstack((addition, repeated))  # Add the repeated values
            F = np.vstack((F, addition))  # Add new rows to F
    # F(F(:,1)==0,:) = []; ?
    return np.unique(F, axis=0).astype(int)

class PAINTException(Exception):
    pass

class PAINT: 
    def __init__(self, po_outcomes: np.ndarray) -> None:
        self.po_outcomes = np.atleast_2d(po_outcomes)
        rows, cols = self.po_outcomes.shape
        if cols >= rows:
            msg = (
                "The count of Pareto optimal outcomes "
                "must be higher than the dimension of the objective space."
            )
            raise PAINTException(msg)
    
    def sort_wrt_entries(self, arr: np.ndarray) -> np.ndarray:
        return np.array(sorted(arr, key=lambda x: (len(np.unique(x)), min(x))))
    
    def perturbate(self, epsilon: Optional[float] = 1e-06):
        self._po_outcomes = self.po_outcomes + np.random.uniform(-epsilon, epsilon, self.po_outcomes.shape)

    def approximate(
            self,
            po_outcomes: Optional[np.ndarray] = None,
            epsilon: Optional[float] = 1e-06,
            method: Optional[str] = 'simplex',
            print_info: Optional[bool] = False
    ) -> np.ndarray: 
        if po_outcomes is None: po_outcomes = self.po_outcomes

        if print_info: 
            start = timer()
            print("Constructing the Delaunay triangulation")
        try:
            D = Delaunay(po_outcomes).simplices
        except QhullError:
            msg = (
                "Failed to construct the Delaunay triangulation\n"
                "Try removing points that are not in general position.\n"
                "I.e use the perturbate function but notice that\n"
                "this will change the values of the Pareto optimal outcomes\n"
                "by maximum of given value epsilon."
            )
            raise PAINTException(msg)
        if print_info: 
            print("Delaunay triangulation constructed\n")
            print("Generating polytopes")
        D = generate_polytopes(D)
        if print_info: print("Polytopes generated\n")

        a = D.shape[0]
        p = len(po_outcomes)

        d = 0 # Deleted
        ind = 0 # Inherently nondominated
        conflict = 0 # Is dominated by or dominates a outcome in po_outcomes
        rule2 = 0 # Deleted because of rule 2
        
        if print_info: print("Started removing by Rule 1")

        # RULE 1
        for i in range(a):
            vertices_i = po_outcomes[D[i]]
            if not inherently_nondominated(vertices_i, epsilon, method):
                if print_info: print(f"Removing polytope {np.unique(D[i])} because it is not inherently nondominated")
                D[[i, d]] = D[[d, i]] # Interchange the rows
                d += 1
                ind += 1
            else:
                for j in range(p):
                    if polytope_dominates(po_outcomes[j], vertices_i, epsilon, method) or polytope_dominates(vertices_i, po_outcomes[j], epsilon, method):
                        if print_info: print(f"Removing polytope {D[i]} because of point {j}")
                        D[[i, d]] = D[[d, i]]
                        d += 1
                        conflict += 1
                        break
        if print_info: 
            r1end = timer()
            msg = (
                f"{100*(ind+conflict)/a if a != 0 else 0}% of all polytopes were removed by Rule 1: \n"
                f"{100*ind/a if a != 0 else 0}% of the polytopes were not inherently nondominated and\n"
                f"{100*conflict/a if a != 0 else 0}% of the polytopes were conflicting with the initial Pareto optimal points.\n"
                f"Removal by Rule 1 took {r1end - start} seconds"
                )
            print(msg)

        # RULE 2
        T = D[d:]
        T = self.sort_wrt_entries(T)
        old_a = a
        a = T.shape[0]
        d = 0
        if print_info: print("Started removing by Rule 2")
        for i in reversed(range(a)):
            for l in range(i+1, a):
                vertices_i = po_outcomes[T[i]]
                if T[l][0] == -1: continue
                vertices_l = po_outcomes[T[l]]

                if polytope_dominates(vertices_i, vertices_l) or polytope_dominates(vertices_l, vertices_i):
                    if print_info: print(f"Removing polytope {T[i]} because of polytope {T[l]}")
                    T[i] = -1
                    rule2 += 1
                    d += 1
                    break 

        if print_info: 
            end = timer()
            msg = (
                f"The rest of the polytopes {100*rule2/old_a if old_a != 0 else 0}% were removed by Rule 2.\n"
                f"That is {100*rule2/a if a != 0 else 0}% of the polytopes that survived Rule 1\n"
                f"Removal by Rule 2 took {end - r1end} seconds.\n"
                f"The whole process took {end - start} seconds."
                )
            print(msg)
        T = np.atleast_2d(T)
        return T[(T >= 0).any(axis=1)]


# Testing the paint method against the examples in the article
if __name__ == "__main__":
    # Example

    print("Starting an example of PAINT usage\n")

    # An array of Pareto optimal outcomes
    arr = np.random.rand(5, 4)
    # Instansiate PAINT object
    p = PAINT(po_outcomes = arr) 
    # If points are not in general position, you can use perturbation:
    p.perturbate(epsilon = 0.01) 
    # Construct the approximation:
    approx = p.approximate(epsilon = 1e-06, method = 'simplex', print_info=True) 
    # If you wish the values are sorted in descending order in regards to unique entries in a row:
    approx = p.sort_wrt_entries(approx) 
    if len(approx > 0):
        # The approximation returns all the indices that form the approximation
        print(f"The indices forming the approximation:\n{approx}\n\n") 
        # To get the original points:
        print(f"The points forming the approximation:\n{p.po_outcomes[approx]}\n\n")
    else:
        print("Every polytope removed")


    # Testing against the wastewater treatment planning problem from the article

    print("\nTesting against the wastewater treatment planning problem:")

    # Pareto optimal outcomes for the wastewater treatment planning problem
    wastewater = np.array([
        [8.05,218,460],
        [3.52,286,490],
        [1.69,326,506],
        [4.9,298,477],
        [1.11,336,515],
        [0.55,347,528],
        [9.36,246,448],
        [30.2,7.23,308],
        [0.9,333,519],
        [0.72,332,524],
    ])

    # The solution from the matlab implementation
    # This is the solution used in the article.
    wastewater_matlab = np.array([
        [0,0,0,0], [1,1,1,1], [2,2,2,2],
        [3,3,3,3], [4,4,4,4], [5,5,5,5],
        [6,6,6,6], [7,7,7,7], [8,8,8,8],
        [9,9,9,9], [0,1,0,0], [0,6,0,0],
        [0,7,0,0], [1,2,1,1], [1,3,1,1],
        [1,6,1,1], [1,9,1,1], [2,3,2,2],
        [2,4,2,2], [2,8,2,2], [2,9,2,2],
        [3,6,3,3], [3,7,3,3], [4,8,4,4],
        [5,8,5,5], [5,9,5,5], [6,7,6,6],
        [8,9,8,8], [0,1,6,0], [0,6,7,0],
        [1,2,3,1], [1,2,9,1], [1,3,6,1],
        [2,4,8,2], [2,8,9,2], [3,6,7,3],
        [5,8,9,5],
    ])

    wastewater_paint = PAINT(wastewater)
    wastewater_approx = wastewater_paint.approximate()
    if (
        wastewater_approx.shape == wastewater_matlab.shape and
        np.all(np.sort(wastewater_approx, axis = 0) == np.sort(wastewater_matlab, axis = 0))
    ):
        print("Paint approximation method for wastewater example gives same results as the matlab implementation of paint")
    else:
        print("Wastewater example failed")
