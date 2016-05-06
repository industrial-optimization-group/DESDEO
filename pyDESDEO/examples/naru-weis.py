# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
River pollution problem by Narula and Weistroffer [1]



References
----------

[1] Narula, S. & Weistroffer, 
    H. A flexible method for nonlinear multicriteria decision-making problems Systems, 
    Man and Cybernetics, IEEE Transactions on, 1989 , 19 , 883-887.

'''

from problem import Problem
class NaurulaWeistroffer(Problem):
    '''
    Brief Description


    
    Attributes
    ----------
    attr : type
        Descrption

    Methods
    -------
    method(c='rgb')
        Brief description, methods only for larger classes
    '''


    def __init__(self, params):
        '''
        Constructor
        '''
        