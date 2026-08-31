"""Reference vector generation for decomposition-based evolutionary methods."""

from functools import lru_cache
from itertools import combinations

import numpy as np
from pymoo.util.ref_dirs import get_reference_directions
from scipy.special import comb


def shear(vectors, degrees: float = 5):
    """Shear a set of vectors lying on the plane z=0 towards the z-axis.

    The resulting vectors are'degrees' angle away from the z axis.

    Parameters
    ----------
    vectors : numpy.ndarray
        The final element of each vector should be zero.
    degrees : float, optional
        The angle that the resultant vectors make with the z axis. Unit is radians.
        (the default is 5)
    """
    angle = degrees * np.pi / 180
    m = 1 / np.tan(angle)
    norm = np.linalg.norm(vectors, axis=1)
    vectors[:, -1] += norm * m
    return normalize(vectors)


def rotate(initial_vector, rotated_vector, other_vectors):
    """Calculate the rotation matrix that rotates the initial_vector to the rotated_vector.

    Apply that rotation on other_vectors and return.
    Uses Householder reflections twice to achieve this.
    """
    init_vec_norm = normalize(initial_vector)
    rot_vec_norm = normalize(np.asarray(rotated_vector))
    middle_vec_norm = normalize(init_vec_norm + rot_vec_norm)
    first_reflector = init_vec_norm - middle_vec_norm
    second_reflector = middle_vec_norm - rot_vec_norm
    Q1 = householder(first_reflector)  # noqa: N806
    Q2 = householder(second_reflector)  # noqa: N806
    reflection_matrix = np.matmul(Q2, Q1)
    return np.matmul(other_vectors, np.transpose(reflection_matrix))


def householder(vector):
    """Return reflection matrix via householder transformation."""
    identity_mat = np.eye(len(vector))
    v = vector[np.newaxis]
    denominator = np.matmul(v, v.T)
    numerator = np.matmul(v.T, v)
    return identity_mat - (2 * numerator / denominator)


def rotate_toward(initial_vector, final_vector, other_vectors, degrees: float = 5):
    """Rotate other_vectors (with the centre at initial_vector) towards final_vector by an angle degrees.

    Parameters
    ----------
    initial_vector : np.ndarray
        Centre of the vectors to be rotated.
    final_vector : np.ndarray
        The final position of the center of other_vectors.
    other_vectors : np.ndarray
        The array of vectors to be rotated
    degrees : float, optional
        The amount of rotation (the default is 5)

    Returns:
    -------
    rotated_vectors : np.ndarray
        The rotated vectors
    reached: bool
        True if final_vector has been reached
    """
    final_vector = normalize(final_vector)
    initial_vector = normalize(initial_vector)
    cos_phi = np.dot(initial_vector, final_vector)
    theta = degrees * np.pi / 180
    cos_theta = np.cos(theta)
    phi = np.arccos(cos_phi)
    if phi < theta:
        return (rotate(initial_vector, final_vector, other_vectors), True)
    cos_phi_theta = np.cos(phi - theta)
    A = np.asarray([[cos_phi, 1], [1, cos_phi]])  # noqa: N806
    B = np.asarray([cos_phi_theta, cos_theta])  # noqa: N806
    x = np.linalg.solve(A, B)
    rotated_vector = x[0] * initial_vector + x[1] * final_vector
    return (rotate(initial_vector, rotated_vector, other_vectors), False)


def approx_lattice_resolution(number_of_vectors: int, num_dims: int) -> int:
    """Approximate the lattice resolution based on the number of vectors and dimensions.

    Args:
        number_of_vectors (int): Desired number of reference vectors.
        num_dims (int): Number of objectives (dimensions).

    Returns:
        int: The smallest lattice resolution that produces more than the desired number of vectors.
    """
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


def create_simplex(
    number_of_objectives: int,
    lattice_resolution: int | None = None,
    number_of_vectors: int | None = None,
) -> np.ndarray:
    """Create reference vectors using the simplex lattice design.

    Args:
        number_of_objectives (int): Number of objectives (dimensions).
        lattice_resolution (int, optional): Lattice resolution to use. If None, will be
            determined from number_of_vectors.
        number_of_vectors (int, optional): Desired number of reference vectors. Used if lattice_resolution is None.

    Returns:
        np.ndarray: Array of normalized reference vectors.

    Raises:
        ValueError: If both lattice_resolution and number_of_vectors are None.
    """
    if lattice_resolution is None and number_of_vectors is None:
        raise ValueError("Either lattice resolution or number of vectors must be specified.")

    if lattice_resolution is None:
        lattice_resolution = approx_lattice_resolution(number_of_vectors, number_of_objectives)

    number_of_vectors = comb(
        lattice_resolution + number_of_objectives - 1,
        number_of_objectives - 1,
        exact=True,
    )

    temp1 = range(1, number_of_objectives + lattice_resolution)
    temp1 = np.array(list(combinations(temp1, number_of_objectives - 1)))
    temp2 = np.array([range(number_of_objectives - 1)] * number_of_vectors)
    temp = temp1 - temp2 - 1
    weight = np.zeros((number_of_vectors, number_of_objectives), dtype=int)
    weight[:, 0] = temp[:, 0]
    for i in range(1, number_of_objectives - 1):
        weight[:, i] = temp[:, i] - temp[:, i - 1]
    weight[:, -1] = lattice_resolution - temp[:, -1]
    values = weight / lattice_resolution
    return normalize(values)


@lru_cache(maxsize=64)
def _create_s_energy_cached(number_of_objectives: int, number_of_vectors: int, seed: int) -> tuple:
    """Build and cache one Riesz s-energy design, returned as a hashable tuple of rows.

    The construction is a seeded optimization costing roughly 0.5-3 s, and a benchmarking run
    rebuilds the same design once per algorithm instantiation. Caching on the three inputs that
    fully determine the result keeps that to once per process.
    """
    vectors = np.asarray(
        get_reference_directions("energy", number_of_objectives, number_of_vectors, seed=seed),
        dtype=float,
    )
    vectors = _ensure_axis_vectors(vectors)
    return tuple(map(tuple, vectors))


def _ensure_axis_vectors(vectors: np.ndarray) -> np.ndarray:
    """Guarantee that every axis direction is represented exactly, without changing the count.

    A decomposition-based algorithm only searches towards directions it has a vector for, so a set
    missing an axis never targets that objective's extreme and the corresponding edge of the front is
    simply not approximated. The current energy optimizer happens to pin the simplex vertices, but
    that is its implementation detail; enforcing it here makes the guarantee DESDEO's own.

    Any missing axis replaces whichever vector is closest to it, so the returned array keeps its
    shape and the substitution costs the least in spacing.
    """
    number_of_objectives = vectors.shape[1]
    axes = np.eye(number_of_objectives)
    for axis_index in range(number_of_objectives):
        axis = axes[axis_index]
        if np.any(np.all(np.isclose(vectors, axis, atol=1e-9), axis=1)):
            continue
        closest = int(np.argmin(np.linalg.norm(vectors - axis, axis=1)))
        vectors[closest] = axis
    return vectors


def create_s_energy(
    number_of_objectives: int,
    number_of_vectors: int,
    seed: int = 0,
) -> np.ndarray:
    """Create reference vectors by minimizing the Riesz s-energy over the unit simplex.

    Unlike the simplex lattice design, this produces *exactly* `number_of_vectors` vectors for any
    combination of count and dimension. The lattice can only realize the binomial counts
    `C(H + m - 1, m - 1)`, so it cannot hit an arbitrary target: at `m = 8` the reachable counts jump
    36, 120, 330, and asking for 100 vectors yields 36. That matters because the population size of a
    decomposition-based algorithm is its reference vector count.

    Every axis direction is guaranteed to be present exactly, so each objective's extreme is always
    a search target; see `_ensure_axis_vectors`.

    Args:
        number_of_objectives (int): Number of objectives (dimensions).
        number_of_vectors (int): Exact number of reference vectors to produce.
        seed (int, optional): Seed for the energy optimization, which is stochastic. Defaults to 0.

    Returns:
        np.ndarray: Array of reference vectors, shape `(number_of_vectors, number_of_objectives)`,
            lying on the unit simplex (rows sum to one), including the `number_of_objectives` axis
            vectors.

    Raises:
        ValueError: If `number_of_vectors` is smaller than `number_of_objectives`, which cannot
            cover the simplex vertices.

    References:
        Blank, J., Deb, K., Dhebar, Y., Bandaru, S., & Seada, H. (2021). Generating Well-Spaced
            Points on a Unit Simplex for Evolutionary Many-Objective Optimization. IEEE Transactions
            on Evolutionary Computation, 25(1), 48-60. https://doi.org/10.1109/TEVC.2020.2992387
    """
    if number_of_vectors < number_of_objectives:
        raise ValueError(
            f"Cannot place {number_of_vectors} reference vectors in {number_of_objectives} dimensions: "
            f"at least one vector per objective is needed to cover the simplex vertices."
        )
    return np.array(_create_s_energy_cached(number_of_objectives, number_of_vectors, seed), dtype=float)


def normalize(values: np.ndarray) -> np.ndarray:
    """Normalize a set of vectors to unit length (project onto the unit hypersphere).

    Args:
        values (np.ndarray): Array of vectors to normalize.

    Returns:
        np.ndarray: Normalized vectors.
    """
    norm_2 = np.linalg.norm(values, axis=1).reshape(-1, 1)
    norm_2[norm_2 == 0] = np.finfo(float).eps
    return np.divide(values, norm_2)


def neighbouring_angles(values: np.ndarray) -> np.ndarray:
    """Calculate the angles to the nearest neighbor for each reference vector.

    Args:
        values (np.ndarray): Array of normalized reference vectors.

    Returns:
        np.ndarray: Array of angles (in radians) to the nearest neighbor for each vector.
    """
    cosvv = np.dot(values, values.transpose())
    cosvv.sort(axis=1)
    cosvv = np.flip(cosvv, 1)
    cosvv[cosvv > 1] = 1
    return np.arccos(cosvv[:, 1])


def add_edge_vectors(values: np.ndarray) -> np.ndarray:
    """Add edge (axis-aligned) vectors to the set of reference vectors.

    This ensures that each axis direction is represented in the set.

    Args:
        values (np.ndarray): Array of reference vectors.

    Returns:
        np.ndarray: Array of reference vectors with edge vectors added and normalized.
    """
    edge_vectors = np.eye(values.shape[1])
    values = np.vstack([values, edge_vectors])
    return normalize(values)
