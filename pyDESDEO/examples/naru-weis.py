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

from core.ResultFactory import IterationPointFactory
from method.NAUTILUS import NAUTILUSv1,ENAUTILUS
from method.NAUTILUS import NAUTILUSv1,ENAUTILUS, NAUTILUS
from optimization.OptimizationMethod import SciPyDE, PointSearch
from optimization.OptimizationProblem import AchievementProblem
from preference.PreferenceInformation import DirectSpecification, RelativeRanking
from problem.Problem import PreGeneratedProblem
from utils import misc, tui
try:
    from NarulaWeistroffer import NaurulaWeistroffer,WEIGHTS
except ImportError:
    from examples.NarulaWeistroffer import NaurulaWeistroffer,WEIGHTS


from utils.misc import Logger 
sys.stdout = Logger(os.path.splitext(os.path.basename(__file__))[0])


if __name__ == '__main__':
    
    # SciPy breaks box constraints
    method = NAUTILUSv1(NaurulaWeistroffer(), SciPyDE)
    nadir = method.problem.nadir
    ideal = method.problem.ideal

    solution = tui.iter_nautilus(method)
    
    if method.current_iter>0:
        try:
            from prompt_toolkit import prompt
            weights=prompt(u'Weights (10 or 20): ',default=u"20",validator=tui.NumberValidator())
        except:
            weights="20"
            
    while method.current_iter>0:
        if solution is None:
            solution = method.problem.nadir
            # Generate new points
        #print solution

        print("E-NAUTILUS\nselected iteration point: %s:"%",".join(map(str,solution)))
        factory=IterationPointFactory(SciPyDE(AchievementProblem(NaurulaWeistroffer())))
        points=misc.new_points(factory,solution,WEIGHTS[weights])
        
        method=ENAUTILUS(PreGeneratedProblem(points=points), PointSearch)
        method.problem.nadir=nadir
        method.problem.ideal=ideal
        tui.iter_enautilus(method)
        solution=method.zh_prev  
    method.printCurrentIteration()
    try:
        from prompt_toolkit import prompt
        a=prompt(u'Press ENTER to exit')
    except:
        pass
