# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
River pollution problem by Narula and Weistroffer [1]

The problem has four objectives and two variables

The problem describes a (hypothetical) pollution problem of a river,
where a fishery and a city are polluting water. The decision variables
represent the proportional amounts of biochemical oxygen demanding
material removed from water in two treatment plants located after the
fishery and after the city.

The first and second objective functions describe the quality of water
after the fishery and after the city, respectively, while objective
functions three and four represent the percent return on investment at
the fishery and the addition to the tax rate in the city.
respectively.


References
----------

[1] Narula, S. & Weistroffer,
    H. A flexible method for nonlinear multicriteria decision-making problems Systems,
    Man and Cybernetics, IEEE Transactions on, 1989 , 19 , 883-887.

"""
import sys, os


example_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(example_path, ".."))


from desdeo.utils import tui

from desdeo.method.NAUTILUS import NAUTILUSv1, ENAUTILUS

from desdeo.optimization.OptimizationMethod import PointSearch
from desdeo.problem.Problem import PreGeneratedProblem


if __name__ == "__main__":
    # SciPy breaks box constraints
    method_e = ENAUTILUS(
        PreGeneratedProblem(
            filename=os.path.join(example_path, "AuxiliaryServices.csv")
        ),
        PointSearch,
    )
    zh = tui.iter_enautilus(method_e)
    ci = method_e.current_iter

    if ci > 0:
        if zh is None:
            fh = zh = method_e.problem.nadir
            fh_lo = method_e.problem.ideal

        else:
            zh = method_e.zh_prev
            fh_lo = method_e.fh_lo_prev
            fh = method_e.nsPoint_prev
        method_v1 = NAUTILUSv1(
            PreGeneratedProblem(
                filename=os.path.join(example_path, "AuxiliaryServices.csv")
            ),
            PointSearch,
        )
        method_v1.current_iter = ci + 1
        method_v1.zh_prev = method_v1.zh = zh
        method_v1.fh = fh
        method_v1.fh_lo = fh_lo
        # method_v1.fh_lo=list(method_v1.bounds_factory.result(method_v1.zh_prev))

        solution = tui.iter_nautilus(method_v1)
    method_v1.printCurrentIteration()
    try:
        from prompt_toolkit import prompt

        a = prompt(u"Press ENTER to exit")
    except:
        pass
