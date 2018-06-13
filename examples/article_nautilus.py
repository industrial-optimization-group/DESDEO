# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2018  Vesa Ojalehto
"""
Script to generate results in [1]

Here, the DM solved the River pollution problem by Narula
and Weistroffer[1], with four objectives and two variables. The problem
describes a (hypothetical) pollution problem of a river, where a
fishery and a city are polluting water. For more information see
:class:`NarulaWeistroffer.RiverPollution`


Usage
-----

Instead of providing the preferences interactively, they can
be piped to the script. For example

python article_nautilus.py < preferences.txt

References
----------

[1] *to be published*

[2] Narula, S. & Weistroffer,
    H. A flexible method for nonlinear multicriteria decision-making problems Systems,
    Man and Cybernetics, IEEE Transactions on, 1989 , 19 , 883-887.

"""
# TODO: Add tui docstrings here (must be first written)
#: Predefined weights for E-NAUTILUS
# TODO: Give weights in an input file

import argparse
import os

from prompt_toolkit.validation import ValidationError, Validator

from desdeo.core.ResultFactory import IterationPointFactory
from desdeo.method.NAUTILUS import ENAUTILUS, NAUTILUSv1
from desdeo.optimization.OptimizationMethod import PointSearch, SciPyDE
from desdeo.optimization.OptimizationProblem import NautilusAchievementProblem
from desdeo.problem.Problem import PreGeneratedProblem
from desdeo.utils import misc, tui
from desdeo.utils.misc import Tee
from desdeo.utils.tui import _prompt_wrapper
from desdeo.problem.toy import RiverPollution

WEIGHTS = {
    "20": [
        [0.1, 0.1, 0.1, 0.7],
        [0.1, 0.1, 0.366667, 0.433333],
        [0.1, 0.1, 0.633333, 0.166667],
        [0.1, 0.1, 0.7, 0.1],
        [0.1, 0.366667, 0.1, 0.433333],
        [0.1, 0.366667, 0.366667, 0.166667],
        [0.1, 0.366667, 0.433333, 0.1],
        [0.1, 0.633333, 0.1, 0.166667],
        [0.1, 0.633333, 0.166667, 0.1],
        [0.1, 0.7, 0.1, 0.1],
        [0.366667, 0.1, 0.1, 0.433333],
        [0.366667, 0.1, 0.366667, 0.166667],
        [0.366667, 0.1, 0.433333, 0.1],
        [0.366667, 0.366667, 0.1, 0.166667],
        [0.366667, 0.366667, 0.166667, 0.1],
        [0.366667, 0.433333, 0.1, 0.1],
        [0.633333, 0.1, 0.1, 0.166667],
        [0.633333, 0.1, 0.166667, 0.1],
        [0.633333, 0.166667, 0.1, 0.1],
        [0.7, 0.1, 0.1, 0.1],
    ],
    "10": [
        [0.1, 0.1, 0.1, 0.7],
        [0.1, 0.1, 0.5, 0.3],
        [0.1, 0.1, 0.7, 0.1],
        [0.1, 0.5, 0.1, 0.3],
        [0.1, 0.5, 0.3, 0.1],
        [0.1, 0.7, 0.1, 0.1],
        [0.5, 0.1, 0.1, 0.3],
        [0.5, 0.1, 0.3, 0.1],
        [0.5, 0.3, 0.1, 0.1],
        [0.7, 0.1, 0.1, 0.1],
    ],
}


def main(logfile=False):
    """ Solve River Pollution problem with NAUTILUS V1 and E-NAUTILUS Methods
    """
    # Duplicate output to log file

    class NAUTILUSOptionValidator(Validator):

        def validate(self, document):
            if document.text not in "ao":
                raise ValidationError(
                    message="Please select a for apriori or o for optimization option",
                    cursor_position=0,
                )

    if logfile:
        Tee(logfile)
    first = True
    current_iter = 0
    while first or current_iter:
        # SciPy breaks box constraints

        nautilus_v1 = NAUTILUSv1(RiverPollution(), SciPyDE)
        if not first:
            nautilus_v1.current_iter = current_iter
        first = False
        nadir = nautilus_v1.problem.nadir
        ideal = nautilus_v1.problem.ideal

        solution = tui.iter_nautilus(nautilus_v1)

        current_iter = nautilus_v1.current_iter

        # TODO: Move to tui module
        method_e = None
        if current_iter > 0:
            option = _prompt_wrapper(
                "select a for apriori or o for optimization option: ",
                default="o",
                validator=NAUTILUSOptionValidator(),
            )
            if option.lower() == "a":
                wi = _prompt_wrapper(
                    "Number of PO solutions (10 or 20): ",
                    default="20",
                    validator=tui.NumberValidator(),
                )
                weights = WEIGHTS[wi]

                factory = IterationPointFactory(
                    SciPyDE(NautilusAchievementProblem(RiverPollution()))
                )
                points = misc.new_points(factory, solution, weights=weights)

                method_e = ENAUTILUS(PreGeneratedProblem(points=points), PointSearch)
                method_e.zh_prev = solution

            else:
                method_e = ENAUTILUS(RiverPollution(), SciPyDE)

            # method_e.zh = solution
            method_e.current_iter = nautilus_v1.current_iter
            method_e.user_iters = nautilus_v1.user_iters

            print(
                "E-NAUTILUS\nselected iteration point: %s:"
                % ",".join(map(str, solution))
            )

            while method_e and method_e.current_iter > 0:
                if solution is None:
                    solution = method_e.problem.nadir

                method_e.problem.nadir = nadir
                method_e.problem.ideal = ideal
                cmd = tui.iter_enautilus(
                    method_e, initial_iterpoint=solution, initial_bound=method_e.fh_lo
                )
                if cmd:
                    print(method_e.current_iter)
                    current_iter = method_e.current_iter
                    break
    if tui.HAS_INPUT:
        input("Press ENTER to exit")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    logfile = f"{os.path.splitext(os.path.basename(__file__))[0]}.log"
    parser.add_argument(
        "--logfile",
        "-l",
        action="store",
        nargs="?",
        const=logfile,
        default=False,
        help=f"Store intarctions to {logfile} or user specified LOGFILE",
    )
    main(**(vars(parser.parse_args())))
