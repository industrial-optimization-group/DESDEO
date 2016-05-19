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

from problem.Problem import Problem
from method.NAUTILUS import NAUTILUS, printCurrentIteration
from preference.PreferenceInformation import DirectSpecification, RelativeRanking
from optimization.OptimizationMethod import SciPy, SciPyDE

class NaurulaWeistroffer(Problem):
    def __init__(self):
        '''
        Constructor
        '''
        self.ideal = [-6.34, -3.44, -7.5, 0.0]
        self.nadir = [-4.07, -2.83, -0.32, 9.71]
    def evaluate(self, population):
        objectives = []

        for values in population:
            res = []
            x0_2 = math.pow(values[0], 2)
            x1_2 = math.pow(values[1], 2)

            res.append(-1.0 * (4.07 + 2.27 * values[0]))

            res.append(-1.0 * (2.6 + 0.03 * values[0] + 0.02 * values[1] + 0.01 / (1.39 - x1_2) + 0.3 / (1.39 - x1_2)))

            res.append(-1.0 * (8.21 - 0.71 / (1.09 - x0_2)))

            res.append(-1.0 * (0.96 - 0.96 / (1.09 - x1_2)))

            objectives.append(res)

        return objectives

    def starting_point(self):
        return [0.65, 0.65]

    def bounds(self):
        return ([0.3, 1.0], [0.3, 1.0])




if __name__ == '__main__':
    # method = NAUTILUS(NaurulaWeistroffer(), SciPy)
    method = NAUTILUS(NaurulaWeistroffer(), SciPyDE)

    method.user_iters = 5
    printCurrentIteration(method)
    # preference = DirectSpecification([-5, -3, -3, 5])



    # solution, distance = method.nextIteration(DirectSpecification([-5, -3, -3, 5]))
    solution, distance = method.nextIteration(RelativeRanking([2, 2, 1, 1]))
    printCurrentIteration(method)

    for i in range(method.user_iters - 1):
        solution, distance = method.nextIteration()
        printCurrentIteration(method)

    # print transfer_point

    # For Narula-Weistroffoer generate set of alternatives with e.g. Steurs method
    # By changing weight vectors for the ref_point
    # Getting PO set for problem, how to generate the weights Interactive WASGFA


    # check several pareto points here between the current bounds
    # e_nautilus = ENAUTILUS(NaurulaWeistroffer(), OptimalSearch, starting_point=transfer_point)
    # print e_nautilus.iterationPoint(DirectSpecification([-5, -3, -3, 5]))

