# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
""" Text based user interafaces for using NIMBUS and NAUTILUS methods

If console is not available, it is possible to iterate non-interactively
by piping preferences from a file

Exceptions
----------

TUIError
   TUI base error

TUIConsoleError
  Console is used but not available

"""

import sys

import numpy as np
from prompt_toolkit import prompt
from prompt_toolkit.validation import ValidationError, Validator

from desdeo.preference.PreferenceInformation import (
    DirectSpecification,
    PercentageSpecifictation,
    RelativeRanking,
)

from .exceptions import DESDEOException

# check if we are piping to stdin
if sys.stdin.isatty():
    HAS_INPUT = True
else:
    HAS_INPUT = False

if sys.stdout.isatty():
    HAS_OUTPUT = True
else:
    HAS_OUTPUT = False


COMMANDS = ["c", "C", "q", "s"]


class TUIError(DESDEOException):
    pass


class TUIConsoleError(TUIError):
    pass


def _check_cmd(text):
    return set(COMMANDS).intersection(set(text))


def ingore_cmd(fkt):

    def wrap(*args):
        if not _check_cmd(args[1].text):
            return fkt(*args)

    return wrap


class IterValidator(Validator):

    def __init__(self, method):
        super().__init__()
        self.range = list(map(str, range(1, len(method.zhs) + 1))) + ["q"]

    @ingore_cmd
    def validate(self, document):
        text = document.text
        if text not in self.range + COMMANDS:
            raise ValidationError(
                message="Ns %s is not valid iteration point" % text, cursor_position=0
            )


class VectorValidator(Validator):

    def __init__(self, method, preference=None):
        super().__init__()
        self.nfun = len(method.problem.nadir)
        self.preference = preference
        self.method = method

    @ingore_cmd
    def validate(self, document):
        values = document.text.split(",")
        if len(values) != self.nfun:
            raise ValidationError(
                message="Problem requires %i items in the vector" % self.nfun,
                cursor_position=0,
            )
        if self.preference:
            err = self.preference.check_input(values)
            if err:
                raise ValidationError(message=err, cursor_position=0)


class NumberValidator(Validator):

    def __init__(self, ranges=None):
        super().__init__()
        if ranges:
            self.ranges = ranges
        else:
            self.ranges = [1, None]

    @ingore_cmd
    def validate(self, document):
        text = document.text
        i = 0
        if text and not text.isdigit():
            # Get index of fist non numeric character.
            # We want to move the cursor here.
            for i, c in enumerate(text):
                if not c.isdigit():
                    break

            raise ValidationError(
                message="This input contains non-numeric characters", cursor_position=i
            )
        v = int(text)
        if self.ranges[0] and v < self.ranges[0]:
            raise ValidationError(
                message="The number must be greater than %i" % self.ranges[0],
                cursor_position=0,
            )

        if self.ranges[1] and v > self.ranges[1]:
            raise ValidationError(
                message="The number must be smaller than %i" % self.ranges[1],
                cursor_position=0,
            )


def _prompt_wrapper(message, default=None, validator=None):
    """ Handle references piped from file
    """

    class MockDocument:

        def __init__(self, text):
            self.text = text

    if HAS_INPUT:
        ret = prompt(message, default=default, validator=validator)
    else:
        ret = sys.stdin.readline().strip()
        print(message, ret)
        if validator:
            validator.validate(MockDocument(ret))
    if "q" in ret:
        if not HAS_OUTPUT:
            print("User exit")
        sys.exit("User exit")
    return ret


def select_iter(method, default=1, no_print=False):
    if not no_print:
        method.print_current_iteration()

    text = _prompt_wrapper(
        "Select iteration point Ns: "  # , validator=IterValidator(method)
    )
    # text = prompt("Select iteration point Ns: ")
    print(text)
    if text in COMMANDS:
        return text
    print("Selected iteration point: %s" % method.zhs[int(text) - 1])
    # This is available only for problems wiht pregenerated solutions
    if method.zh_reach:
        print("Reachable points: %s" % method.zh_reach[int(text) - 1])
    return method.zhs[int(text) - 1], method.zh_los[int(text) - 1]


def init_nautilus(method):
    """Initialize nautilus method

    Parameters
    ----------

    method
        Interactive method used for the process

    Returns
    -------

    PreferenceInformation subclass to be initialized
    """

    print("Preference elicitation options:")
    print("\t1 - Percentages")
    print("\t2 - Relative ranks")
    print("\t3 - Direct")

    PREFCLASSES = [PercentageSpecifictation, RelativeRanking, DirectSpecification]

    pref_sel = int(
        _prompt_wrapper(
            "Reference elicitation ",
            default=u"%s" % (1),
            validator=NumberValidator([1, 3]),
        )
    )

    preference_class = PREFCLASSES[pref_sel - 1]

    print("Nadir: %s" % method.problem.nadir)
    print("Ideal: %s" % method.problem.ideal)

    if method.current_iter - method.user_iters:
        finished_iter = method.user_iters - method.current_iter
    else:
        finished_iter = 0
    new_iters = int(
        _prompt_wrapper(
            u"Ni: ", default=u"%s" % (method.current_iter), validator=NumberValidator()
        )
    )
    method.current_iter = new_iters
    method.user_iters = finished_iter + new_iters

    return preference_class


def iter_nautilus(method):
    """ Iterate NAUTILUS method either interactively, or using given preferences if given

    Parameters
    ----------

    method : instance of NAUTILUS subclass
       Fully initialized NAUTILUS method instance

    """
    solution = None
    while method.current_iter:
        preference_class = init_nautilus(method)
        pref = preference_class(method, None)
        default = ",".join(map(str, pref.default_input()))
        while method.current_iter:
            method.print_current_iteration()

            pref_input = _prompt_wrapper(
                u"Preferences: ",
                default=default,
                validator=VectorValidator(method, pref),
            )

            cmd = _check_cmd(pref_input)
            if cmd:
                solution = method.zh
                break
            pref = preference_class(
                method, np.fromstring(pref_input, dtype=np.float, sep=",")
            )
            default = ",".join(map(str, pref.pref_input))
            solution, _ = method.next_iteration(pref)
        if cmd and list(cmd)[0] == "c":
            break
    return solution


def iter_enautilus(method, initial_iterpoint=None, initial_bound=None, weights=None):
    method.user_iters = method.current_iter = int(
        _prompt_wrapper(
            u"Ni: ", default=u"%i" % method.current_iter, validator=NumberValidator()
        )
    )
    # ), validator=NumberValidator()))
    txt = _prompt_wrapper(u"Ns: ", default=u"5")
    if txt[0] in COMMANDS:
        return txt
    method.Ns = int(txt)
    print("Nadir: %s" % method.problem.nadir)
    print("Ideal: %s" % method.problem.ideal)

    method.next_iteration(preference=(initial_iterpoint, initial_bound))
    # points = None

    while method.current_iter:
        pref = select_iter(method, 1)
        if pref in COMMANDS:
            return pref

        text = _prompt_wrapper(
            u"Ns: ", default=u"%s" % (method.Ns), validator=NumberValidator()
        )

        if text[0] in COMMANDS:
            return text

        method.Ns = int(txt)

    if not method.current_iter:
        method.zh_prev = select_iter(method, 1)[0]
        method.current_iter -= 1
    return None
