"""Tests related to the NAUTILUS method."""

import numpy as np
import polars as pl
import pytest

from desdeo.mcdm.enautilus import (
    ENautilusResult,
    calculate_closeness,
    calculate_intermediate_points,
    calculate_lower_bounds,
    calculate_reachable_subset,
    enautilus_get_representative_solutions,
    enautilus_step,
    prune_by_average_linkage,
)
from desdeo.problem import Objective, Problem, Variable, VariableTypeEnum
from desdeo.tools import SolverResults


@pytest.mark.enautilus
def test_pruning():
    """Test the prune_by_average_linkage_method."""
    cluster1 = np.array([[0.0, 0.0], [0.1, 0.1], [0.2, 0.0], [0.0, 0.2], [0.1, 0.2]])
    cluster2 = np.array([[10.0, 10.0], [10.1, 10.2], [9.9, 10.1], [10.2, 9.9], [9.8, 9.9]])
    points = np.vstack((cluster1, cluster2))

    # Prune to 2 representative points
    pruned = prune_by_average_linkage(points, k=2)

    assert pruned.shape == (2, 2)
    # Should be close to one point from each cluster
    assert any(np.linalg.norm(p - [0.1, 0.1]) < 0.3 for p in pruned)
    assert any(np.linalg.norm(p - [10.0, 10.0]) < 0.3 for p in pruned)


@pytest.mark.enautilus
def test_calculate_intermediate_points():
    """Test that intermediate points are calculated correctly."""
    z_prev = np.array([2.0, 4.0])
    zs_reps = np.array([[6.0, 8.0], [10.0, 12.0]])
    iterations_left = 2

    expected = np.array(
        [
            [4.0, 6.0],  # (1/2)*z_prev + (1/2)*[6,8]
            [6.0, 8.0],  # (1/2)*z_prev + (1/2)*[10,12]
        ]
    )

    result = calculate_intermediate_points(z_prev, zs_reps, iterations_left)

    assert result.shape == expected.shape
    np.testing.assert_allclose(result, expected)


@pytest.mark.enautilus
def test_calculate_reachable_subset():
    """Tests that the reachable subset is calculated in a sane way."""
    non_dominated = np.array(
        [
            [1.0, 1.0],  # too small
            [2.0, 2.0],  # on lower bound
            [2.5, 2.5],  # inside bounds
            [3.0, 3.0],  # on upper bound
            [3.5, 3.5],  # too large
            [2.0, 3.1],  # second objective too high
            [1.9, 2.9],  # first objective too low
        ]
    )

    lower_bounds = np.array([2.0, 2.0])
    z_preferred = np.array([3.0, 3.0])

    expected_indices = [1, 2, 3]  # rows 1-3 are within bounds

    result = calculate_reachable_subset(non_dominated, lower_bounds, z_preferred)

    assert isinstance(result, list)
    assert sorted(result) == expected_indices


def test_calculate_lower_bounds():
    """Test that calculate_lower_bounds works as expected."""
    nd_points = np.array(
        [
            [1.0, 2.0, 9.0],
            [0.5, 3.0, 6.0],
            [2.0, 1.5, 5.0],  # This one will be included only for f1
            [1.5, 2.5, 4.0],
        ]
    )
    z_intermediate = np.array([1.6, 2.6, 6.5])

    # Expected:
    # For f0 (min f0 s.t. f1, f2 ≤ 2.6, 6.5):
    #   feasible: [0.5, 3.0, 6.0] (fails f1), [1.5, 2.5, 4.0] -> min f0 = 1.5
    #
    # For f1 (min f1 s.t. f0, f2 ≤ 1.6, 6.5):
    #   feasible: [0.5, 3.0, 6.0], [1.5, 2.5, 4.0] -> min f1 = 2.5
    #
    # For f2 (min f2 s.t. f0, f1 ≤ 1.6, 2.6):
    #   feasible: [1.0, 2.0, 9.0] (too high), [1.5, 2.5, 4.0] -> min f2 = 4.0

    expected = np.array([1.5, 2.5, 4.0])
    result = calculate_lower_bounds(nd_points, z_intermediate)

    assert result.shape == expected.shape
    np.testing.assert_allclose(result, expected)


@pytest.mark.enautilus
def test_calculate_closeness():
    """Tests that the closeness is calculated correctly."""
    z_nadir = np.array([0.0, 0.0])
    z_rep = np.array([4.0, 0.0])

    # Case 1: halfway: expect 50.0
    z_half = np.array([2.0, 0.0])
    result_half = calculate_closeness(z_half, z_nadir, z_rep)
    np.testing.assert_allclose(result_half, 50.0)

    # Case 2: same as nadir: expect 0.0
    z_same_as_nadir = z_nadir
    result_nadir = calculate_closeness(z_same_as_nadir, z_nadir, z_rep)
    np.testing.assert_allclose(result_nadir, 0.0)

    # Case 3: same as representative: expect 100.0
    z_same_as_rep = z_rep
    result_rep = calculate_closeness(z_same_as_rep, z_nadir, z_rep)
    np.testing.assert_allclose(result_rep, 100.0)


def test_enautilus_step_basic():
    """Test the basic function of the enautilus_step."""

    class DummyObjective:
        def __init__(self, symbol: str):
            self.symbol = symbol
            self.maximize = "2" in symbol

    class DummyProblem:
        def __init__(self, symbols: list[str]):
            self.objectives = [DummyObjective(sym) for sym in symbols]

    # Problem definition with two objectives
    problem = DummyProblem(["f1", "f2"])  # f1 to minimize, f2 to maximize

    # Define non-dominated points with both original and minimized values
    nd_points = pl.DataFrame(
        {
            "f1": [0.5, 1.0, 0.8, 1.2, 0.7, 1.1],  # to minimize
            "f2": [3.1, 2.9, 3.4, 3.15, 3.0, 3.2],  # to maximize
            "f1_min": [0.5, 1.0, 0.8, 1.2, 0.7, 1.1],  # f1 already min
            "f2_min": [-3.1, -2.9, -3.4, -3.15, -3.0, -3.2],  # f2_max turned into min
        }
    )

    # Selected point is dominated: worse f1, worse f2
    selected_point = {"f1": 1.5, "f2": 2.5}

    result = enautilus_step(
        problem=problem,
        non_dominated_points=nd_points,
        current_iteration=2,
        iterations_left=3,
        selected_point=selected_point,
        reachable_point_indices=list(range(len(nd_points))),
        total_number_of_iterations=5,
        number_of_intermediate_points=3,
    )

    # --- Assertions ---

    assert isinstance(result, ENautilusResult)
    assert result.current_iteration == 3
    assert result.iterations_left == 2

    # Intermediate points
    assert len(result.intermediate_points) == 3
    for pt in result.intermediate_points:
        assert isinstance(pt, dict)
        assert set(pt.keys()) == {"f1", "f2"}
        assert all(isinstance(v, float) for v in pt.values())

    # Bounds and closeness
    assert len(result.reachable_worst_bounds) == 3
    assert len(result.reachable_best_bounds) == 3
    assert len(result.closeness_measures) == 3
    for c in result.closeness_measures:
        assert 0.0 <= c <= 100.0

    # Reachable point indices
    assert all(isinstance(i, list) for i in result.reachable_point_indices)
    assert all(0 <= len(i) <= len(nd_points) for i in result.reachable_point_indices)


@pytest.mark.enautilus
def test_enautilus_full_run_boring():
    """Test E-NAUTILUS in a ''full run''."""
    variables = [Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real)]
    objectives = [
        Objective(name="cost", symbol="f1", maximize=False),
        Objective(name="quality", symbol="f2", maximize=True),
    ]

    problem = Problem(
        name="Synthetic-E-NAUTILUS",
        description="Unit-test problem",
        variables=variables,
        objectives=objectives,
    )

    f1 = np.array([0.60, 0.90, 0.70, 1.00, 0.80, 1.10])
    f2 = np.array([3.40, 3.10, 3.30, 2.90, 3.20, 3.00])

    nd_df = pl.DataFrame(
        {
            "f1": f1,  # original   (min)
            "f2": f2,  # original   (max)
            "f1_min": f1,  # already min
            "f2_min": -f2,  # convert max -> min
        }
    )

    # start from nadir
    nadir_point = {
        "f1": float(nd_df["f1"].max()),  # largest cost
        "f2": float(nd_df["f2"].min()),  # smallest quality
    }

    reachable_indices = list(range(len(nd_df)))  # everything reachable from nadir

    total_iterations = 3
    current_iter = 0
    selected_point = nadir_point  # first selected point is the nadir point

    while current_iter < total_iterations:
        result = enautilus_step(
            problem=problem,
            non_dominated_points=nd_df,
            current_iteration=current_iter,
            iterations_left=total_iterations - current_iter,
            selected_point=selected_point,
            reachable_point_indices=reachable_indices,
            total_number_of_iterations=total_iterations,
            number_of_intermediate_points=2,
        )

        assert result.current_iteration == current_iter + 1
        assert result.iterations_left == total_iterations - current_iter - 1

        assert len(result.intermediate_points) == 2
        assert len(result.reachable_best_bounds) == 2
        assert len(result.reachable_worst_bounds) == 2
        assert len(result.closeness_measures) == 2
        assert len(result.reachable_point_indices) == 2

        # every list of indices must be a subset of the ND set
        for idx_list in result.reachable_point_indices:
            assert all(isinstance(i, int) for i in idx_list)
            assert all(0 <= i < len(nd_df) for i in idx_list)

        # pick the first intermediate point as the DM's next selection
        selected_point = result.intermediate_points[0]
        reachable_indices = result.reachable_point_indices[0]
        current_iter += 1

    assert result.iterations_left == 0

    final_min_vec = np.array([selected_point["f1"], -selected_point["f2"]])
    nd_min_mat = nd_df.select(["f1_min", "f2_min"]).to_numpy()

    # The final point must match (be equal to) one of the rows of the ND front
    assert any(np.allclose(final_min_vec, row) for row in nd_min_mat)


@pytest.mark.enautilus
def test_enautilus_full_run_dynamic():
    """Run E-NAUTILUS through several itearions.

    Run E-NAUTILUS through several iterations (4-objective case)
    while changing both the number of iterations left and the number
    of intermediate points on the fly.
    """
    problem = Problem(
        name="Synthetic-4D",
        description="Unit-test Problem for E-NAUTILUS",
        variables=[Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real)],
        objectives=[
            Objective(name="f1", symbol="f1", maximize=False),
            Objective(name="f2", symbol="f2", maximize=True),
            Objective(name="f3", symbol="f3", maximize=False),
            Objective(name="f4", symbol="f4", maximize=True),
        ],
    )

    f1 = np.array([0.40, 0.60, 0.50, 0.70, 0.45, 0.55, 0.65, 0.48])
    f2 = np.array([4.00, 3.80, 4.10, 3.70, 4.05, 3.90, 3.60, 4.20])
    f3 = np.array([1.00, 1.30, 1.10, 1.40, 1.05, 1.20, 1.35, 1.15])
    f4 = np.array([2.50, 2.30, 2.60, 2.20, 2.55, 2.40, 2.10, 2.65])

    nd_df = pl.DataFrame(
        {
            "f1": f1,
            "f2": f2,
            "f3": f3,
            "f4": f4,
            "f1_min": f1,
            "f2_min": -f2,
            "f3_min": f3,
            "f4_min": -f4,
        }
    )

    selected_point = {
        "f1": float(nd_df["f1"].max()),
        "f2": float(nd_df["f2"].min()),
        "f3": float(nd_df["f3"].max()),
        "f4": float(nd_df["f4"].min()),
    }
    reachable_indices = list(range(len(nd_df)))  # entire front reachable

    total_iters = 2  # DM first thinks 2 iterations are enough
    n_points = 3  # DM wants to see 3 points at first
    current = 0

    while True:
        res = enautilus_step(
            problem=problem,
            non_dominated_points=nd_df,
            current_iteration=current,
            iterations_left=total_iters - current,
            selected_point=selected_point,
            reachable_point_indices=reachable_indices,
            total_number_of_iterations=total_iters,
            number_of_intermediate_points=n_points,
        )

        # basic structural sanity
        assert len(res.intermediate_points) == n_points
        assert len(res.reachable_point_indices) == n_points
        for idxs in res.reachable_point_indices:
            assert all(0 <= i < len(nd_df) for i in idxs)

        # DM behaviour:
        # After first step, DM “speeds up” by asking more points (n=4).
        # After second step, DM “slows down” by adding another iteration
        # and asking fewer points (2).
        if current == 0:  # after 1st iteration
            n_points = 4  # asks for 4 points next
        elif current == 1:  # after 2nd iteration
            n_points = 2  # ok with 2 points now
            total_iters += 1  # adds one more iteration
        elif res.iterations_left == 0:
            # finished: break loop after final result
            final_result = res
            break

        # choose first intermediate as new selection
        selected_point = res.intermediate_points[0]
        reachable_indices = res.reachable_point_indices[0]
        current += 1

    assert final_result.iterations_left == 0

    final_vec = np.array([selected_point["f1"], -selected_point["f2"], selected_point["f3"], -selected_point["f4"]])
    nd_min_mat = nd_df.select(["f1_min", "f2_min", "f3_min", "f4_min"]).to_numpy()

    # final selected point must coincide with a point on the Pareto front
    assert any(np.allclose(final_vec, row) for row in nd_min_mat)


@pytest.mark.enautilus
def test_get_representative_solutions():
    """Test that the representative solutions are fetched correctly."""
    problem = Problem(
        name="tiny",
        description="unit-test",
        variables=[Variable(name="x", symbol="x", variable_type=VariableTypeEnum.real)],
        objectives=[
            Objective(name="f1", symbol="f1", maximize=False),
            Objective(name="f2", symbol="f2", maximize=False),
        ],
    )

    nd_df = pl.DataFrame(
        {
            "x": [10, 20, 30],
            "f1": [1.0, 2.0, 3.5],
            "f2": [1.0, 2.0, 2.5],
        }
    )

    intermed = [
        {"f1": 1.2, "f2": 0.9},  # closest to [1.0, 1.0]
        {"f1": 3.0, "f2": 2.7},  # closest to [3.5, 2.5]
    ]

    dummy_bounds = [{"f1": 0.0, "f2": 0.0}] * 2  # not used in this test
    dummy_meas = [0.0, 0.0]
    dummy_idx = [[0, 1, 2], [0, 1, 2]]

    result = ENautilusResult(
        current_iteration=1,
        iterations_left=1,
        intermediate_points=intermed,
        reachable_best_bounds=dummy_bounds,
        reachable_worst_bounds=dummy_bounds,
        closeness_measures=dummy_meas,
        reachable_point_indices=dummy_idx,
    )

    sols = enautilus_get_representative_solutions(problem, result, nd_df)

    assert isinstance(sols, list) and len(sols) == 2
    assert all(isinstance(s, SolverResults) for s in sols)

    # Expected mapping indices
    expected_rows = [0, 2]
    for sol, idx in zip(sols, expected_rows, strict=True):
        row = nd_df[idx]

        assert np.isclose(sol.optimal_objectives["f1"], row["f1"])
        assert np.isclose(sol.optimal_objectives["f2"], row["f2"])
        assert np.isclose(sol.optimal_variables["x"], row["x"])

        assert sol.success
