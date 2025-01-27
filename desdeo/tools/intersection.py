"""Utility methods to check if reference vectors intersect a bounding box."""

import numpy as np


def line_box_intersection(
    box_min: np.ndarray, box_max: np.ndarray, reference_points: np.ndarray, thickness
) -> np.ndarray:
    """Find the reference directions that intersect the box defined by box_min and box_max.

    Args:
        box_min (np.ndarray): The infimum of the box.
        box_max (np.ndarray): The supremum of the box.
        reference_points (np.ndarray): The reference directions.
        thickness (float): The threshold for thickness. Defines the thickness of the box. The thickness is added to
            the box_min and subtracted from the box_max to define the box. The reference directions that intersect
            the box are marked as bad. The thickness is a hyperparameter that needs to be tuned. The default value
            is 0.05.
            Try out some values close to 0.05. Lower values
            will result in lesser number of reference points being marked as bad. Note that a value of zero does not
            imply that only reference directions that directly intersect the box are marked as bad. Floating point
            shenanigans (np.isclose) happen.

    Returns:
        np.ndarray: A boolean array of length num_points, where True indicates that the reference direction intersects
            the box.
    """
    # Find the reference directions that intersect the box

    # Vector through the reference point = reference point + k * (nadir - ideal)

    k_bmin = box_min - reference_points
    k_bmax = box_max - reference_points

    # Find the reference directions that intersect the box
    k_min = np.min((k_bmax, k_bmin), axis=0).max(axis=1) - thickness / 2
    k_max = np.max((k_bmax, k_bmin), axis=0).min(axis=1) + thickness / 2

    intersect_mask = np.logical_or((k_max >= k_min), np.isclose(k_max, k_min))
    return intersect_mask


def find_bad_indicesREF(solution, ref_point, reference_points, thickness):
    box_max, box_min = find_bad_limits(solution, ref_point)
    bad_points = line_box_intersection(box_min, box_max, reference_points, thickness)
    return bad_points, box_min, box_max


def find_bad_limits(solution, ref_point, threshold=0.05):
    # Find projections of solution on the ref direction
    k = solution - ref_point
    box_max = ref_point + k.max()
    box_min = solution
    return box_max, box_min - threshold / 2
