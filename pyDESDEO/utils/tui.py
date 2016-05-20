# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
'''
from prompt_toolkit.validation import Validator, ValidationError

class IterValidator(Validator):
    def __init__(self,method):
        super(IterValidator,self).__init__()
        self.range=map(str, range(1,len(method.zhs)+1))+["q"]
         
    def validate(self, document):
        text = document.text
        if text not in self.range+["q","c"]:
            raise ValidationError(message='Ns %s is not valid iteration point'%text,
                                  cursor_position=0)

class VectorValidator(Validator):
    def __init__(self,method):
        super(VectorValidator,self).__init__()
        self.nfun=len(method.problem.nadir)
         
    def validate(self, document):
        if document.text=="s":
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
