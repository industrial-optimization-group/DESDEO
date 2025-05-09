"""Utilities specific to explainable multiobjective optimization."""

import cvxpy as cp
import numpy as np


def generate_biased_mean_data(
    data: np.ndarray, target_means: np.ndarray, min_size: int = 2, max_size: int | None = None, solver: str = "SCIP"
) -> list | None:
    r"""Finds a subset of the provided data that has a mean value close to provided target values.

    Finds a subset of the provided data that has a mean value close to the
    provided target values.  Formulates a mixed-integer quadratic programming problem to
    find a subset of `data` with a mean as close as possible to `target_values`
    and a size between `min_size` and `max_size`. In other words, the following problems is solved:

    \begin{align}
        &\min_{\mathbf{x}} & f(\mathbf{x}) & = \sum_{i=1}^m \left[ \left(\frac{1}{k}
            \sum_{j=1}^n x_j \times \text{data}_j\right)_i - \text{target}_i \right]^2 \\
        &\text{s.t.,}   & k & = \sum_{i=1}^n x_i,\\
        &               & k & \leq \text{max_size},\\
        &               & k & \geq \text{min_size},\\
    \end{align},
    where $n$ is the number of rows in `data`, $m$ is the number of columns in
    `data`, and $k$ is the size of the subset. Notice that the closeness to the
    target means is based on the Euclidean distance.

    Note:
        Be mindful that this functions can take a long time with a very large
            data set and large upper bound for the desired subset.

    Args:
        data (np.ndarray): the data from which to generate the subset with a
            biased mean. Should be a 2D array with each row representing a sample
            and each column the value of the variables in the sample.
        target_means (np.ndarray): the target mean values for each column the
            generated subset should have values close to.
        min_size (int, optional): the minimum size of the generated subset. Defaults to 2.
        max_size (int | None, optional): the maximum size of the generated
            subset. If None, then the maximum size is bound by the numbers of rows
            in `data`. Defaults to None.
        solver (str, optional): the selected solver to be used by cvxpy. The
            solver should support mixed-integer quadratic programming. Defaults to
            "SCIP".

    Returns:
        list | None: the indices of the samples of the generated subset respect to
            `data`, i.e., the generated subset is `data[indices]`. If optimization is not successful,
            returns None instead.
    """
    # Number of rows and columns
    n_rows, n_cols = data.shape
    max_size = n_rows if max_size is None else max_size

    # Big M used to penalize the auxiliary variable z
    big_m = data.max(axis=0)

    # Binary variables to select rows from the data
    x = cp.Variable(n_rows, boolean=True)

    # Auxiliary variables, z represents the mean. phi is the weighted sum of the data (weighted by x)
    z = cp.Variable(n_cols)
    phi = cp.Variable((n_rows, n_cols))

    # The objective function, squared values of the difference between the mean
    # of the currently selected subset and the target values.
    objective = cp.sum_squares(z - target_means)

    # Define the constraints
    constraints = [
        # Sets the value of phi
        *[cp.sum(phi[:, col]) == cp.sum(cp.multiply(x, data[:, col])) for col in range(n_cols)],
        # Constraints the values of phi using big M, in practice setting z to be the mean values
        *[phi[:, col] <= cp.multiply(big_m[col], x) for col in range(n_cols)],
        *[phi[:, col] <= z[col] for col in range(n_cols)],
        *[phi[:, col] >= z[col] - cp.multiply(big_m[col], 1 - x) for col in range(n_cols)],
        phi >= 0,
        # Bounds the size of the set: min_size <= k <= max_size
        cp.sum(x) >= min_size,
        cp.sum(x) <= max_size,
    ]

    # Create the problem model
    problem = cp.Problem(cp.Minimize(objective), constraints)

    # Solve the problem
    problem.solve(solver=solver)

    # Return the indices of the found subset
    return [i for i in range(n_rows) if x.value[i] == 1]
