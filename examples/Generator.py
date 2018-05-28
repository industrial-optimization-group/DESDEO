# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""

"""
import os

from desdeo.method import ENAUTILUS, NAUTILUSv1
from desdeo.optimization import PointSearch
from desdeo.problem import PreGeneratedProblem
from desdeo.utils import tui

example_path = os.path.dirname(os.path.realpath(__file__))


if __name__ == "__main__":
    # SciPy breaks box constraints
    method_e = ENAUTILUS(
        PreGeneratedProblem(
            filename=os.path.join(example_path, "AuxiliaryServices.csv")
        ),
        PointSearch,
    )
    zh = tui.iter_enautilus(method_e)
    ci = method_e.current_iter

    if ci > 0:
        if zh is None:
            fh = zh = method_e.problem.nadir
            fh_lo = method_e.problem.ideal

        else:
            zh = method_e.zh_prev
            fh_lo = method_e.fh_lo_prev
            fh = method_e.nsPoint_prev
        method_n = NAUTILUSv1(
            PreGeneratedProblem(
                filename=os.path.join(example_path, "AuxiliaryServices.csv")
            ),
            PointSearch,
        )
        method_n.current_iter = ci + 1
        method_n.zh_prev = method_n.zh = zh
        method_n.fh = fh
        method_n.fh_lo = fh_lo
        # method.fh_lo=list(method.bounds_factory.result(method.zh_prev))

        solution = tui.iter_nautilus(method_n)
    method_n.print_current_iteration()
    try:
        from prompt_toolkit import prompt

        a = prompt(u"Press ENTER to exit")
    except ImportError:
        pass
