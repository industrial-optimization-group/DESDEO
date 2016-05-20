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
import logging
example_path=os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(example_path,".."))

if not "--no-tui" in sys.argv:
    from prompt_toolkit import prompt
    tui=True
else:
    tui=False

import preference
from utils.tui import *
from preference.PreferenceInformation import DirectSpecification
from problem.Problem import PreGeneratedProblem
from method.NAUTILUS import NAUTILUSv1,ENAUTILUS, printCurrentIteration
from preference.PreferenceInformation import DirectSpecification, RelativeRanking
from optimization.OptimizationMethod import SciPy, SciPyDE,PointSearch


def select_iter(method,default=1):
    method.printCurrentIteration()
    try:
        text = prompt(u'Select iteration point Ns: ',validator=IterValidator(method))
    except TypeError:
        text=str(default)
    if text=="q":
        sys.exit("User Exit")
    elif text=="c":
        return None
    return method.zhs[int(text)-1],method.zh_los[int(text)-1]

if __name__ == '__main__':
    if "--debug" in sys.argv:
        FORMAT = "%(message)s"
        logging.basicConfig(format=FORMAT,level=logging.DEBUG)

    
    method = ENAUTILUS(PreGeneratedProblem(os.path.join(example_path,"AuxiliaryServices.csv")), PointSearch)
    print "Nadir: ", method.problem.nadir
    print "Ideal: ",method.problem.ideal
    
    if tui:
        method.user_iters=method.current_iter=int(prompt(u'Ni: ',default=u"5",validator=NumberValidator()))
        method.Ns=int(prompt(u'Ns: ',default=u"5",validator=NumberValidator()))
        method.nextIteration()
    else:
        points=None
    
    while method.current_iter:
        if tui:
            pref=select_iter(method,1)
            if pref is None:
                break
            
            points=method.nextIteration(pref)
        else:
            points=method.nextIteration(points)
            for ri,r in enumerate(method.zh_reach):
                if r:
                    points=points[ri]
                    break
                            
            method.printCurrentIteration()
    if method.current_iter:          
        method_v1 = NAUTILUSv1(PreGeneratedProblem(os.path.join(example_path,"AuxiliaryServices.csv")), PointSearch)
        method_v1.zh=method.zh
        method_v1.zh_prev=method.zh_prev
        method_v1.current_iter=method.current_iter
        method_v1.user_iters=method.user_iters
        method_v1.printCurrentIteration()
        pref=RelativeRanking([2, 2, 1])
    
        while method_v1.current_iter:
            if tui:
                rank=prompt(u'Ranking: ',default=u",".join(map(str,pref.ranking)),validator=VectorValidator(method))
                if rank=="s":
                    break
                pref=RelativeRanking(map(float,rank.split(",")))
    
            solution, distance = method_v1.nextIteration(pref)
            method_v1.printCurrentIteration()
    else:
        method.printCurrentIteration()

    
    #printCurrentIteration(method)

    # solution, distance = method.nextIteration(DirectSpecification([-5, -3, -3, 5]))
    #solution, distance = method.nextIteration(RelativeRanking([2, 2, 1]))
    #printCurrentIteration(method)

    #while (method.current_iter > 0):
        #solution, distance = method.nextIteration()
        #printCurrentIteration(method)

    # print transfer_point

    # For Narula-Weistroffoer generate set of alternatives with e.g. Steurs method
    # By changing weight vectors for the ref_point
    # Getting PO set for problem, how to generate the weights Interactive WASGFA


    # check several pareto points here between the current bounds
    # e_nautilus = ENAUTILUS(NaurulaWeistroffer(), OptimalSearch, starting_point=transfer_point)
    # print e_nautilus.iterationPoint(DirectSpecification([-5, -3, -3, 5]))

