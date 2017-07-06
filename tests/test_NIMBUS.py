import os

import numpy as np

from method.NIMBUS import NIMBUS
from preference.PreferenceInformation import Classification
from examples.NarulaWeistroffer import NaurulaWeistroffer, WEIGHTS
from problem.Problem import PreGeneratedProblem
from optimization.OptimizationMethod import PointSearch
from examples.AuxiliaryServices import example_path


def run(method, preference):
    ''' test method for steps iterations with given  reference point and bounds (if any)'''
    return method.nextIteration(preference = preference)

def test_running_NIMBUS():
    vals = []
    method = NIMBUS(PreGeneratedProblem(filename = os.path.join(example_path, "AuxiliaryServices.csv")), PointSearch)

    run1 = run(method, Classification(method.problem, [("<", None), (">=", 1), ("<", None)]))
    assert run1[0][1] < 1
    assert len(run1) == 2

    # When using point search, there should not be better solutions when projected
    cls = []
    for v in run1[0]:
        cls.append(("<=", v))
    run2 = run(method, Classification(method.problem, cls))

    assert np.isclose(run1[0], run2[1]).all() # pylint: disable=E1101
    print ""
    print run1
    print run2
