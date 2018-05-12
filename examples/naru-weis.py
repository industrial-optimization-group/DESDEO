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

import os
import sys

from prompt_toolkit import prompt

from desdeo.core.ResultFactory import IterationPointFactory
from desdeo.method.NAUTILUS import ENAUTILUS, NAUTILUSv1
from desdeo.optimization.OptimizationMethod import PointSearch, SciPyDE
from desdeo.optimization.OptimizationProblem import AchievementProblem
from desdeo.problem.Problem import PreGeneratedProblem
from desdeo.utils import misc, tui
from utils.misc import Logger

from .NarulaWeistroffer import WEIGHTS, RiverPollution

sys.stdout = Logger(os.path.splitext(os.path.basename(__file__))[0])


if __name__ == "__main__":

    # SciPy breaks box constraints
    method_v1 = NAUTILUSv1(RiverPollution(), SciPyDE)
    nadir = method_v1.problem.nadir
    ideal = method_v1.problem.ideal

    solution = tui.iter_nautilus(method_v1)

    ci = method_v1.current_iter
    if ci > 0:
        weights = prompt(
            u"Weights (10 or 20): ", default=u"20", validator=tui.NumberValidator()
        )

        factory = IterationPointFactory(SciPyDE(AchievementProblem(RiverPollution())))
        points = misc.new_points(factory, solution, WEIGHTS[weights])

        method_e = ENAUTILUS(PreGeneratedProblem(points=points), PointSearch)
        method_e.current_iter = ci
        method_e.zh_prev = solution
        print(
            "E-NAUTILUS\nselected iteration point: %s:"
            % ",".join(map(str, method_e.zh_prev))
        )

    while method_e.current_iter > 0:
        if solution is None:
            solution = method_e.problem.nadir
            # Generate new points
        # print solution

        method_e.problem.nadir = nadir
        method_e.problem.ideal = ideal
        tui.iter_enautilus(method_e)
        solution = method_e.zh_prev
    method_e.print_current_iteration()
    a = prompt(u"Press ENTER to exit")
