# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
'''
import os
import sys
import time

from preference.PreferenceInformation import DirectSpecification

class Logger(object):
    def __init__(self,filename):
        self.terminal = sys.stdout 
        username=os.getenv('username')
        self.log = open("%s_%s_%s.log"%(filename,username,time.strftime("%Y%m%d-%H%M%S")), "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass    


def new_points(factory,solution,weights):
    points=[]
    for pref in map(DirectSpecification,weights):
        points.append(factory.result(pref,solution))
    return points
