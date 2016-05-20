# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
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

import sys,os
example_path=os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(example_path,".."))
from prompt_toolkit import prompt

if not "--no-tui" in sys.argv:
    tui=True
else:
    tui=False
import math

from utils.tui import *
from preference.PreferenceInformation import DirectSpecification

from problem.Problem import Problem
from method.NAUTILUS import NAUTILUSv1,ENAUTILUS
from preference.PreferenceInformation import DirectSpecification, RelativeRanking
from optimization.OptimizationMethod import SciPy, SciPyDE

from AuxiliaryServices import select_iter

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
    # SciPy breaks box constraints
    #method = NAUTILUS(NaurulaWeistroffer(), SciPy)
    
    method = NAUTILUSv1(NaurulaWeistroffer(), SciPyDE)

    if tui:
        method.current_iter=method.user_iters=int(prompt(u'Ni: ',default=u"5",validator=NumberValidator()))

    method.printCurrentIteration()
    
    pref=RelativeRanking([2, 2, 1, 1])
    #solution, distance = method.nextIteration()
    #printCurrentIteration(method)

    while(method.current_iter):
        rank=prompt(u'Ranking: ',default=u",".join(map(str,pref.ranking)),validator=VectorValidator(method))
        if rank=="c":
            break
        pref=RelativeRanking(map(float,rank.split(",")))
        solution, distance = method.nextIteration(pref)
        method.printCurrentIteration()

    if method.current_iter:          
        emethod = NAUTILUSv1(PreGeneratedProblem(os.path.join(example_path,"naru-weis.txt"),delimieter=" "), PointSearch)
        


