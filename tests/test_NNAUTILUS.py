import os

from desdeo.method import NNAUTILUS
from desdeo.optimization.OptimizationMethod import PointSearch
from desdeo.problem.Problem import PreGeneratedProblem
from examples.AuxiliaryServices import example_path


def run(method, ref_point, steps=100, bounds=None):
    """ test method for steps iterations with given  reference point and bounds (if any)"""
    vals = []
    for i in range(steps):
        dist, fh, zh, lo, up, nP = method.next_iteration(ref_point, bounds)
        vals.append([dist, lo, up, zh])
        if not nP:
            break
    return vals


def test_running_NNAUTILUS():
    method = NNAUTILUS(
        PreGeneratedProblem(
            filename=os.path.join(example_path, "AuxiliaryServices.csv")
        ),
        PointSearch,
    )
    vals = run(method, [-43000, 2, -60], 6)
    assert len(vals) == 6
