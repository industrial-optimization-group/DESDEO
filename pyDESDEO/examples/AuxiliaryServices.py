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

from utils import tui

from method.NAUTILUS import NAUTILUSv1,ENAUTILUS

from optimization.OptimizationMethod import PointSearch
from problem.Problem import PreGeneratedProblem

from utils.misc import Logger 
sys.stdout = Logger(os.path.splitext(os.path.basename(__file__))[0])

if __name__ == '__main__':
    # SciPy breaks box constraints
    method = ENAUTILUS(PreGeneratedProblem(filename=os.path.join(example_path,"AuxiliaryServices.csv")), PointSearch)
    zh=tui.iter_enautilus(method)
    ci=method.current_iter
   
    if ci:
        if zh is None:
            fh=zh = method.problem.nadir
            fh_lo = method.problem.ideal

        else:      
            zh=method.zh_prev  
            fh_lo=method.fh_lo
            fh=method.nsPoint_prev

        method = NAUTILUSv1(PreGeneratedProblem(filename=os.path.join(example_path,"AuxiliaryServices.csv")), PointSearch)
        method.current_iter=ci+1
        method.zh_prev=method.zh=zh
        method.fh=fh
        method.fh_lo=fh_lo
        #method.fh_lo=list(method.bounds_factory.result(method.zh_prev))

        solution = tui.iter_nautilus(method)
    method.printCurrentIteration()
    try:
        from prompt_toolkit import prompt
        a=prompt(u'Press ENTER to exit')
    except:
        pass
