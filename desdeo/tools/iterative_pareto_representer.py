"""Implements the Iterative Pareto Representer algorithm."""

import numpy as np
from pydantic import BaseModel, Field
from scipy.spatial.distance import cdist

from desdeo.tools.intersection import find_bad_indicesREF


class _EvaluatedPoint(BaseModel):
    reference_point: dict[str, float] = Field(
        description="""Reference point used to evaluate the point.
                    The objective space is assumed to be normalized such that the ideal point is (0, 0, ..., 0)
                    and the nadir point is (1, 1, ..., 1). Naturally, all objectives are assumed to be minimized.
                    The reference point must lie on a plane perpendicular to the ideal-nadir line, and passing through
                    the nadir point. The reference point must be used together with an ASF to find an exact Pareto
                    optimal solution."""
    )
    targets: dict[str, float] = Field(
        description="""Target values for each objective function. The target values are used to evaluate the point.
                    These are the objective function values that have been scaled between the ideal and nadir points,
                    and assumed to be minimized."""
    )
    objectives: dict[str, float] = Field(
        description="""The actual objective function values of the evaluated point. These values are not scaled.
        Not required for the algorithm, but useful for archiving."""
    )


def _choose_reference_point(
    refp_array: np.ndarray,
    evaluated_points: list[_EvaluatedPoint] | None = None,
):
    """Choose the next reference point to evaluate using the Iterative Pareto Representer algorithm.

    Args:
        refp_array (np.ndarray): The reference points to choose from.
        evaluated_points (list[_EvaluatedPoint]): Already evaluated reference points and their targets.
            If None, a random reference point is chosen.
    """
    if evaluated_points is None or len(evaluated_points) == 0:
        return refp_array[np.random.choice(refp_array.shape[0])], None
    bad_points_mask = _find_bad_RPs(refp_array, evaluated_points)
    available_points_mask = ~bad_points_mask
    solution_projections = _project(np.array([list(eval_result.targets.values()) for eval_result in evaluated_points]))
    return _DSS_with_pruning(
        available=refp_array[available_points_mask],
        taken=np.vstack((solution_projections, refp_array[bad_points_mask])),
    ), bad_points_mask


def _find_bad_RPs(
    reference_points_array: np.ndarray, eval_results: list[_EvaluatedPoint], thickness: float = 0.02
) -> np.ndarray:
    """Find the reference points that will lead to repeated evaluations according to the ASF pruning rule."""
    mask = np.zeros(reference_points_array.shape[0], dtype=bool)
    dict_to_numpy = lambda x: np.array(list(x.values()))
    for eval_result in eval_results:
        bad_indices, _, _ = find_bad_indicesREF(
            dict_to_numpy(eval_result.targets),
            dict_to_numpy(eval_result.reference_point),
            reference_points_array,
            thickness,
        )
        bad_indices = np.where(bad_indices)[0]
        mask[bad_indices] = True
    return mask


def _DSS_with_pruning(
    available: np.ndarray,
    taken: np.ndarray,
) -> int:
    """One-liner implementation of the DSS algorithm using scipy."""
    assert len(available) > 0, "No reference points available."

    assert np.allclose(
        available.sum(axis=1), available.shape[1]
    ), "Reference points must lie on plane perpendicular to ideal-nadir line."

    assert np.allclose(
        taken.sum(axis=1), taken.shape[1]
    ), "Reference points must lie on plane perpendicular to ideal-nadir line."

    if taken is None or len(taken) == 0:
        return np.random.choice(available)

    distances = cdist(available, taken, metric="chebyshev").min(axis=1)

    return available[np.argmax(distances)]


def _project(solutions):
    """Project the solution to the reference plane defined by the reference_point and the normal vector."""
    reference_point = np.ones(solutions.shape[1])
    normal = reference_point / np.linalg.norm(reference_point)
    perp_dist = np.atleast_2d(np.inner(solutions - reference_point, normal)).T
    projected_points = solutions - perp_dist * normal
    return projected_points
