# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
'''
import sys
try:
    from prompt_toolkit import prompt
    tui=True
except:
    tui=False

from prompt_toolkit.validation import Validator, ValidationError

from method.NAUTILUS import ENAUTILUS, NAUTILUSv1
from preference.PreferenceInformation import RelativeRanking

COMMANDS=["c","C","q"]



class IterValidator(Validator):
    def __init__(self,method):
        super(IterValidator,self).__init__()
        self.range=map(str, range(1,len(method.zhs)+1))+["q"]
         
    def validate(self, document):
        text = document.text
        if text not in self.range+COMMANDS:
            raise ValidationError(message='Ns %s is not valid iteration point'%text,
                                  cursor_position=0)

class VectorValidator(Validator):
    def __init__(self,method):
        super(VectorValidator,self).__init__()
        self.nfun=len(method.problem.nadir)
         
    def validate(self, document):
        for c in COMMANDS:
            if c in document.text:
                if c == "q":
                    sys.exit("User exit")
                return
        values = document.text.split(",")
        if len(values) != self.nfun:
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



def select_iter(method,default=1,no_print=False):
    if not no_print:
        method.printCurrentIteration()
    try:
        text = prompt(u'Select iteration point Ns: ',validator=IterValidator(method))
    except:
        text=str(default)
        # This is not a tui, so go to next
        if method.current_iter==3:
            text="c"
        
    if  "q" in text:
        sys.exit("User exit")
    elif text in COMMANDS:
        return text
    return method.zhs[int(text)-1],method.zh_los[int(text)-1]

def ask_pref(method,prev_pref):
    rank=prompt(u'Ranking: ',default=u",".join(map(str,prev_pref)),validator=VectorValidator(method))
    if rank=="e":
        return rank
    pref=RelativeRanking(map(float,rank.split(",")))
    method.nextIteration(pref)
    method.printCurrentIteration()
    


def iter_nautilus(method):
    solution=None
    pref=RelativeRanking([1.0]*len(method.problem.nadir))
    try:
        method.current_iter=method.user_iters=method.current_iter=int(prompt(u'Ni: ',default=u"%s"%(method.current_iter),validator=NumberValidator()))
    except:
        method.current_iter=method.user_iters=5

    print("Nadir: %s"%method.problem.nadir)
    print("Ideal: %s"%method.problem.ideal)

    while(method.current_iter):
        method.printCurrentIteration()
        default=u",".join(map(str,pref.pref_input))
        try:
            pref_input=prompt(u'Ranking: ',default=default,validator=VectorValidator(method))
        except:
            # This is not a tui, so go to next
            pref_input=default
            if method.current_iter==3:
                pref_input="c"
        brk=False
        for c in COMMANDS:
            if c in pref_input:
                brk = True
        if brk:
            solution = method.zh
            break
        pref=RelativeRanking(map(float,pref_input.split(",")))
        solution, distance = method.nextIteration(pref)
        
    return solution

def iter_enautilus(method):
    try:
        method.user_iters=method.current_iter=int(prompt(u'Ni: ',default=u"5",validator=NumberValidator()))
        method.Ns=int(prompt(u'Ns: ',default=u"5",validator=NumberValidator()))
    except:
        method.user_iters=5
        method.Ns=5
    print("Nadir: %s"%method.problem.nadir)
    print("Ideal: %s"%method.problem.ideal)

    method.nextIteration()
    points = None
    
    while method.current_iter:
        #method.printCurrentIteration()
        pref=select_iter(method,1)
        if pref  in COMMANDS:
            break
        points=method.nextIteration(pref)
    if not method.current_iter:
        method.zh_prev=select_iter(method,1)[0]
        method.current_iter-=1
    return points 


    
    
