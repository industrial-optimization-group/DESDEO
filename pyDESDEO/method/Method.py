# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
Module description
'''

from abc import ABCMeta, abstractmethod
import numpy as np
import logging
class Method(object):
    '''
    Abstract base class for interactive multiobjective methods


    Attributes
    ----------
    attr : type
        Descrption

    Methods
    -------
    method(c='rgb')
        Brief description, methods only for larger classes
    '''
    __metaclass__ = ABCMeta


    def __init__(self, params):
        '''
        Constructor
        '''
    def distance(self,where=None,target=None):
        if where is None:
            where=self.zh
        if target is None:
            target=self.fh

        u = np.linalg.norm(np.array(where) - np.array(self.problem.nadir))
        l = np.linalg.norm(np.array(target) - np.array(self.problem.nadir))

        logging.debug("NADIR: %s"%self.problem.nadir)
        logging.debug("zh: %s:",where)
        logging.debug("PO: %s",target)
        
        return (u / l) * 100
