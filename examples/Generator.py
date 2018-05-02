# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
'''

'''
import sys, os


example_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(example_path, ".."))

import desdeo
from desdeo.utils import tui

from method import NAUTILUSv1, ENAUTILUS

from desdeo.optimization.method import PointSearch
from desdeo.problem.problem import PreGeneratedProblem


if __name__ == '__main__':
    # SciPy breaks box constraints
    method = ENAUTILUS(PreGeneratedProblem(filename = os.path.join(example_path, "AuxiliaryServices.csv")), PointSearch)
    zh = tui.iter_enautilus(method)
    ci = method.current_iter

    if ci > 0:
        if zh is None:
            fh = zh = method.problem.nadir
            fh_lo = method.problem.ideal

        else:
            zh = method.zh_prev
            fh_lo = method.fh_lo_prev
            fh = method.nsPoint_prev
        method = NAUTILUSv1(PreGeneratedProblem(filename = os.path.join(example_path, "AuxiliaryServices.csv")), PointSearch)
        method.current_iter = ci + 1
        method.zh_prev = method.zh = zh
        method.fh = fh
        method.fh_lo = fh_lo
        # method.fh_lo=list(method.bounds_factory.result(method.zh_prev))

        solution = tui.iter_nautilus(method)
    method.printCurrentIteration()
    try:
        from prompt_toolkit import prompt
        a = prompt(u'Press ENTER to exit')
    except:
        pass
