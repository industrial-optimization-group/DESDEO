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

if "--tui" in sys.argv:
    from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError

import preference
from preference.PreferenceInformation import DirectSpecification
from problem.Problem import PreGeneratedProblem
from method.NAUTILUS import NAUTILUSv1,ENAUTILUS, printCurrentIteration
from preference.PreferenceInformation import DirectSpecification, RelativeRanking
from optimization.OptimizationMethod import SciPy, SciPyDE,PointSearch

class IterValidator(Validator):
    def __init__(self,method):
        super(IterValidator,self).__init__()
        self.range=map(str, range(1,len(method.zhs)+1))+["q"]
         
    def validate(self, document):
        text = document.text
        if text not in self.range:
            raise ValidationError(message='Ns %s is not valid iteration point'%text,
                                  cursor_position=0)

class VectorValidator(Validator):
    def __init__(self,method):
        super(IterValidator,self).__init__()
        self.nfun=len(method.nadir)
         
    def validate(self, document):
        values = document.text.split(",")
        if len(values) not in self.nfun:
            raise ValidationError(message='Problem requires %i items in the vector'%self.nfun,
                                  cursor_position=0)

class NumberValidator(Validator):
    def validate(self, document):
        text = document.text

        if text and not text.isdigit():
            i = 0

            # Get index of fist non numeric character.
            # We want to move the cursor here.
            for i, c in enumerate(text):
                if not c.isdigit():
                    break

            raise ValidationError(message='This input contains non-numeric characters',
                                  cursor_position=i)

def select_iter(method,default=1):
    method.printCurrentIteration()
    try:
        text = prompt(u'next Ns: ',validator=IterValidator(method))
    except TypeError:
        text=str(default)
    if text=="q":
        sys.exit("User Exit")
    return method.zhs[int(text)-1]

if __name__ == '__main__':
    if "--tui" in sys.argv:
        tui=True
    else:
        tui=False
    method = ENAUTILUS(PreGeneratedProblem(os.path.join(example_path,"AuxiliaryServices.csv")), PointSearch)
    print "Nadir: ", method.problem.nadir
    print "Ideal: ",method.problem.ideal
    
    if tui:
        method.user_iter=int(prompt(u'Ni: ',default=u"5",validator=NumberValidator()))
        method.Ns=int(prompt(u'Ns: ',default=u"5",validator=NumberValidator()))
        method.nextIteration()
    else:
        points=None
    
    while method.current_iter:
        if tui:
            method.nextIteration(select_iter(method,1))
        else:
            points=method.nextIteration(points)[0]        
            method.printCurrentIteration()
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

