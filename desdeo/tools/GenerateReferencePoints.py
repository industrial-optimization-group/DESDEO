"""Generate reference points for the IPA algorithm."""

from itertools import product

import numpy as np
from numba import njit
from scipy.spatial import ConvexHull


def normalize(vectors):
    """Normalize a set of vectors.

    The length of the returned vectors will be 1.

    Parameters
    ----------
    vectors : np.ndarray
        Set of vectors of any length, except zero.

    """
    if len(np.asarray(vectors).shape) == 1:
        return vectors / np.linalg.norm(vectors)
    norm = np.linalg.norm(vectors, axis=1)
    return vectors / norm[:, np.newaxis]


def householder(vector):
    """Return reflection matrix via householder transformation."""
    identity_mat = np.eye(len(vector))
    v = vector[np.newaxis]
    denominator = np.matmul(v, v.T)
    numerator = np.matmul(v.T, v)
    rot_mat = identity_mat - (2 * numerator / denominator)
    return rot_mat


def rotate(initial_vector, rotated_vector, other_vectors):
    """Calculate the rotation matrix that rotates the initial_vector to the
    rotated_vector. Apply that rotation on other_vectors and return.
    Uses Householder reflections twice to achieve this."""

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


def get_reference_hull(num_dims):
    """Get the convex hull of the valid reference points for IPA.

    This algorithm generates the vertices of the unit hypercube in the (num_dims)-dimensional space.
    Then, the vertices are projected onto the plane perpendicular to the largest space diagonal (vertex first parallel
    projection) and rotated such that the plane is perpendular to one of the axes. Then, the points are are flattened
    to (num_dims-1)-dimensional space. A convex hull is then constructed from the projected vertices, and a bounding box
    is constructed around the convex hull.

    Args:
        num_dims (int): The number of dimensions of the space in which the reference points are generated.

    Returns:
        np.ndarray: A (2) x (num_dims-1) array of the bounding box. Reference points are guaranteed to be within
            this box. However, not all points within this box are valid reference points.
        np.ndarray: A (num_dims-1) x (num_dims-1) array of the coefficients of the hyperplanes defining the convex hull
            of the bounds of the reference points. A point is a valid reference point if it lies within the convex hull.
        np.ndarray: A (num_dims-1) array of the constants of the hyperplanes defining the convex hull. See above.
        scipy.spatial.ConvexHull: The convex hull of the projected vertices/valid reference points.
    """
    vertices = np.array(list(product([0, 1], repeat=num_dims)))

    # Project vertices onto plane perpendicular to largest space diagonal, rotate to make one of the objectives zero.
    # Then flatten to (num_dims-1) dimensions.
    rotated_vertices = rotate_in(vertices)

    bounding_box = np.array([np.min(rotated_vertices, axis=0), np.max(rotated_vertices, axis=0)])

    hull = ConvexHull(rotated_vertices)

    A, b = get_hull_equations(hull)

    return bounding_box, A, b, hull


def rotate_in(vertices: np.ndarray) -> np.ndarray:
    """Project the vertices to a lower dimensional space.

    First, the vertices are rotated such that the plane perpendicular to the ideal-nadir line
    becomes perpendicular to one of the axes. Essentially, (1,1,...,1) is rotated to (0,0,...,0,1).
    Then, the last dimension is dropped.

    Args:
        vertices (np.ndarray): The vertices to be projected.

    Returns:
        np.ndarray: The projected vertices.
    """
    num_dims = len(vertices[0])
    rotated_vertices = rotate([1] * num_dims, ([0] * (num_dims - 1) + [1]), vertices)
    rotated_vertices = rotated_vertices[:, :-1]
    return rotated_vertices


def rotate_out(points: np.ndarray) -> np.ndarray:
    """Undo the `rotate_in` operation.

    Args:
        points (np.ndarray): The points to be projected back.

    Returns:
        np.ndarray: The projected points.
    """
    points = np.atleast_2d(points)
    num_points, num_dims = points.shape
    points_rotated = np.hstack((points, np.ones((len(points), 1))))
    points_rotated = rotate(([0] * (num_dims) + [1]), [1] * (num_dims + 1), points_rotated)
    # Move (along nadir-ideal direction) the plane of these points such that it passes through nadir
    points_rotated = points_rotated + 1 - 1 / np.sqrt(num_dims + 1)
    return points_rotated


def get_hull_equations(hull: ConvexHull) -> tuple[np.ndarray, np.ndarray]:
    """Get the equations of the hyperplanes defining the convex hull.

    Args:
        hull (scipy.spatial.ConvexHull): A convex hull.

    Returns:
        np.ndarray: A (num_dims-1) x num_hyperplanes array of the coefficients of the hyperplanes defining the convex
            hull.
        np.ndarray: A (num_hyperplanes) array of the constants of the hyperplanes defining the convex hull.
    """
    return np.ascontiguousarray(hull.equations[:, :-1].T), np.ascontiguousarray(hull.equations[:, -1].T)


def generate_points(
    num_points: int, num_dims: int
) -> tuple[
    np.ndarray,
    np.ndarray,
]:
    """Generate reference points for the IPA algorithm.

    Creates a (large) number of reference points on a plane perpendicular to the largest space diagonal of the unit
    hypercube in the num_dims-dimensional space. First, the vertices of the unit hypercube are generated. Then, the
    vertices are projected onto the plane perpendicular to the largest space diagonal (vertex first parallel
    projection) and rotated such that the plane is perpendular to one of the axes, making all objective values zero.
    A convex hull is then constructed from the projected vertices, and a bounding box is constructed
    around the convex hull. Finally, points are generated uniformly within the bounding box until num_points points
    are generated _inside_ the convex hull. Note that the number of dimensions must be at least 2. Also, the number of
    dimensions of the reference points is one less than the number of dimensions of the objective space. This is because
    the reference points are generated on the projected plane.

    Args:
        num_points (int): The number of reference points to generate.
        num_dims (int): The number of dimensions of the space in which the reference points are generated.

    Returns:
        np.ndarray: A (num_points) x (num_dims-1) array of reference points.
    """
    bounding_box, A, b, _ = get_reference_hull(num_dims)
    points = numba_random_gen(num_points, bounding_box, A, b)
    # Project vertices onto plane perpendicular to largest space diagonal
    points_rotated = rotate_out(points)
    return points, points_rotated


@njit()
def numba_random_gen(num_points: int, bounding_box: np.ndarray, A: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Generates num_points random points within the convex hull defined by A and b.

    Args:
        num_points (int): The number of points to generate.
        bounding_box (np.ndarray): A (2) x (num_objs - 1) array defining the bounding box within which to
            generate points initially.
        A (np.ndarray): A (num_hyperplanes) x (num_objs - 1) array of the coefficients of the hyperplanes defining the
            convex hull. Basically the first num_objs - 1 columns of hull.equations.
        b (np.ndarray): A (num_hyperplanes) array of the constants of the hyperplanes defining the convex hull.
            Basically the last column of hull.equations.

    Returns:
        np.ndarray: A (num_points) x (num_objs - 1) array of points within the convex hull defined by A and b.
    """
    num_dims_ = bounding_box.shape[1]
    points = np.zeros((num_points, num_dims_))

    eps = np.finfo(np.float32).eps

    counter = 0

    while counter < num_points:
        point = np.zeros(num_dims_)
        for i in range(num_dims_):
            # Generate a random point within the bounding box
            point[i] = np.random.uniform(bounding_box[0, i], bounding_box[1, i])
        if np.all(point @ A + b < eps):
            # If the point is inside the convex hull, add it to the list of points
            points[counter] = point
            counter += 1
    return points
