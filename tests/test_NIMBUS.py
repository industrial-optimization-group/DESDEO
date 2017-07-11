import os

import numpy as np

from pyDESDEO.method.NIMBUS import NIMBUS
from pyDESDEO.preference.PreferenceInformation import Classification
from pyDESDEO.examples.NarulaWeistroffer import NaurulaWeistroffer
from pyDESDEO.problem.Problem import PreGeneratedProblem
from pyDESDEO.optimization.OptimizationMethod import PointSearch, SciPyDE
from pyDESDEO.examples.AuxiliaryServices import example_path


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

    assert np.isclose(run1[0], run2[1]).all()  # pylint: disable=E1101

def test_narula():
    method = NIMBUS(NaurulaWeistroffer(), SciPyDE)

    vals = method.initIteration()
    assert len(vals) == 1
    vals = method.nextIteration(preference = Classification(method.problem, [("<", None), ("<=", .1), ("<", None), ("<=", 0.4)]))
    assert len(vals) == 2
    vals = method.nextIteration(preference = Classification(method.problem, [("<", None), ("<=", .1), ("<", None), ("<=", 0.4)]), scalars = ["NIM"])
    assert len(vals) == 1


def test_classification(method):
    vals = method.initIteration()
    method.problem.selected = vals[0]
    cls = Classification(method.problem, vals[0])
    assert cls.reference_point() == vals[0]
