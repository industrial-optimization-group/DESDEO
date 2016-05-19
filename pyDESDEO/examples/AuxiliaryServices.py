# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
from preference.PreferenceInformation import DirectSpecification
'''
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

'''

import math

from problem.Problem import PreGeneratedProblem
from method.NAUTILUS import NAUTILUS, printCurrentIteration
from preference.PreferenceInformation import DirectSpecification, RelativeRanking
from optimization.OptimizationMethod import SciPy, SciPyDE,PointSearch



if __name__ == '__main__':
    #method = NAUTILUS(NaurulaWeistroffer(), SciPy)
    method = NAUTILUS(PreGeneratedProblem("AuxiliaryServices.csv"), PointSearch)

    method.user_iters = 5
    printCurrentIteration(method)

    # solution, distance = method.nextIteration(DirectSpecification([-5, -3, -3, 5]))
    solution, distance = method.nextIteration(RelativeRanking([2, 2, 1]))
    printCurrentIteration(method)

    while (method.current_iter > 0):
        solution, distance = method.nextIteration()
        printCurrentIteration(method)

    # print transfer_point

    # For Narula-Weistroffoer generate set of alternatives with e.g. Steurs method
    # By changing weight vectors for the ref_point
    # Getting PO set for problem, how to generate the weights Interactive WASGFA


    # check several pareto points here between the current bounds
    # e_nautilus = ENAUTILUS(NaurulaWeistroffer(), OptimalSearch, starting_point=transfer_point)
    # print e_nautilus.iterationPoint(DirectSpecification([-5, -3, -3, 5]))

