import os
import pytest

from method.NAUTILUS import NNAUTILUS
from examples.NarulaWeistroffer import NaurulaWeistroffer, WEIGHTS
from problem.Problem import PreGeneratedProblem
from optimization.OptimizationMethod import PointSearch
from examples.AuxiliaryServices import example_path


def run(method, ref_point, steps = 100, bounds = None):
    ''' test method for steps iterations with given  reference point and bounds (if any)'''
    vals = []
    for i in range(steps):
        dist, fh, zh, lo, up, nP = method.nextIteration(ref_point, bounds)
        vals.append([dist, lo, up, zh])
        if not nP:
            break
    return vals


def test_running_NNAUTILUS():
    method = NNAUTILUS(PreGeneratedProblem(filename = os.path.join(example_path, "AuxiliaryServices.csv")), PointSearch)
    vals = run(method, [-30000, 4, -60], 6)
    assert len(vals) == 6


