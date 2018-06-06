import os

import numpy as np

from desdeo.method import NIMBUS
from desdeo.optimization.OptimizationMethod import PointSearch, SciPyDE
from desdeo.preference.PreferenceInformation import NIMBUSClassification
from desdeo.problem.Problem import PreGeneratedProblem
from examples.AuxiliaryServices import example_path
from examples.NarulaWeistroffer import RiverPollution


def run(method, preference):
    """ test method for steps iterations with given  reference point and bounds (if any)"""
    return method.next_iteration(preference=preference)


def test_point_search():
    method = NIMBUS(
        PreGeneratedProblem(
            filename=os.path.join(example_path, "AuxiliaryServices.csv")
        ),
        PointSearch,
    )

    run1 = run(
        method, NIMBUSClassification(method, [("<", None), (">=", 1), ("<", None)])
    )

    assert run1.objective_vars[0][1] >= 1
    assert len(run1.items) == 4

    # When using point search, there should not be better solutions when projected
    cls = []
    for v in run1.objective_vars[0]:
        cls.append(("<=", v))
    run2 = run(method, NIMBUSClassification(method, cls))

    assert np.isclose(
        run1.objective_vars[0], run2.objective_vars[1]
    ).all()  # pylint: disable=E1101


def test_optimization():
    method = NIMBUS(RiverPollution(), SciPyDE)

    vals = method.init_iteration()
    assert len(vals.items) == 1
    vals = method.next_iteration(
        preference=NIMBUSClassification(
            method, [("<", None), ("<=", .1), ("<", None), ("<=", 0.4)]
        )
    )
    assert len(vals.items) == 4
    vals = method.next_iteration(
        preference=NIMBUSClassification(
            method, [("<", None), ("<=", .1), ("<", None), ("<=", 0.4)]
        ),
        scalars=["NIM"],
    )
    assert len(vals.items) == 1


def test_classification(method):
    vals = method.init_iteration()
    method.problem.selected = vals.objective_vars[0]
    cls = NIMBUSClassification(method, vals.objective_vars[0])
    assert cls.reference_point() == vals.objective_vars[0]
