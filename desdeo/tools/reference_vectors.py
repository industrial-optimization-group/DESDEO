from itertools import combinations

import numpy as np
from scipy.special import comb


def normalize(vectors):
    """Normalize a set of vectors.

    The length of the returned vectors will be unity.

    Parameters
    ----------
    vectors : np.ndarray
        Set of vectors of any length, except zero.

    """
    if len(np.asarray(vectors).shape) == 1:
        return vectors / np.linalg.norm(vectors)
    norm = np.linalg.norm(vectors, axis=1)
    return vectors / norm[:, np.newaxis]


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
    Q1 = householder(first_reflector)
    Q2 = householder(second_reflector)
    reflection_matrix = np.matmul(Q2, Q1)
    rotated_vectors = np.matmul(other_vectors, np.transpose(reflection_matrix))
    return rotated_vectors


def householder(vector):
    """Return reflection matrix via householder transformation."""
    identity_mat = np.eye(len(vector))
    v = vector[np.newaxis]
    denominator = np.matmul(v, v.T)
    numerator = np.matmul(v.T, v)
    rot_mat = identity_mat - (2 * numerator / denominator)
    return rot_mat


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
    A = np.asarray([[cos_phi, 1], [1, cos_phi]])
    B = np.asarray([cos_phi_theta, cos_theta])
    x = np.linalg.solve(A, B)
    rotated_vector = x[0] * initial_vector + x[1] * final_vector
    return (rotate(initial_vector, rotated_vector, other_vectors), False)


def approx_lattice_resolution(number_of_vectors: int, num_dims: int) -> int:
    """
    Approximate the lattice resolution based on the number of vectors and dimensions.

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
    lattice_resolution: int = None,
    number_of_vectors: int = None,
) -> np.ndarray:
    """
    Create reference vectors using the simplex lattice design.

    Args:
        number_of_objectives (int): Number of objectives (dimensions).
        lattice_resolution (int, optional): Lattice resolution to use. If None, will be determined from number_of_vectors.
        number_of_vectors (int, optional): Desired number of reference vectors. Used if lattice_resolution is None.

    Returns:
        np.ndarray: Array of normalized reference vectors.

    Raises:
        ValueError: If both lattice_resolution and number_of_vectors are None.
    """
    if lattice_resolution is None and number_of_vectors is None:
        raise ValueError(
            "Either lattice resolution or number of vectors must be specified."
        )

    if lattice_resolution is None:
        lattice_resolution = approx_lattice_resolution(
            number_of_vectors, number_of_objectives
        )

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


def normalize(values: np.ndarray) -> np.ndarray:
    """
    Normalize a set of vectors to unit length (project onto the unit hypersphere).

    Args:
        values (np.ndarray): Array of vectors to normalize.

    Returns:
        np.ndarray: Normalized vectors.
    """
    norm_2 = np.linalg.norm(values, axis=1).reshape(-1, 1)
    norm_2[norm_2 == 0] = np.finfo(float).eps
    values = np.divide(values, norm_2)
    return values


def neighbouring_angles(values: np.ndarray) -> np.ndarray:
    """
    Calculate the angles to the nearest neighbor for each reference vector.

    Args:
        values (np.ndarray): Array of normalized reference vectors.

    Returns:
        np.ndarray: Array of angles (in radians) to the nearest neighbor for each vector.
    """
    cosvv = np.dot(values, values.transpose())
    cosvv.sort(axis=1)
    cosvv = np.flip(cosvv, 1)
    cosvv[cosvv > 1] = 1
    acosvv = np.arccos(cosvv[:, 1])
    return acosvv


def add_edge_vectors(values: np.ndarray) -> np.ndarray:
    """
    Add edge (axis-aligned) vectors to the set of reference vectors.

    This ensures that each axis direction is represented in the set.

    Args:
        values (np.ndarray): Array of reference vectors.

    Returns:
        np.ndarray: Array of reference vectors with edge vectors added and normalized.
    """
    edge_vectors = np.eye(values.shape[1])
    values = np.vstack([values, edge_vectors])
    return normalize(values)
