# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
""" Text based user interafaces for using NIMBUS and NAUTILUS methods

If console is not available, it is possible to iterate in non-interactively with predefined preference

Exceptions
------

TUIError
   TUI base error

TUIConsoleError 
  Console is used but not available

"""
# TODO: Use given preferences as default values if HAS_TUI

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

if sys.stdout.isatty():
    HAS_TUI = True
else:
    HAS_TUI = False

COMMANDS = ["c", "C", "q"]


class TUIError(DESDEOException):
    pass


class TUIConsoleError(TUIError):
    pass


class IterValidator(Validator):
    def __init__(self, method):
        super().__init__()
        self.range = map(str, range(1, len(method.zhs) + 1)) + ["q"]

    def validate(self, document):
        text = document.text
        if text not in self.range + COMMANDS:
            raise ValidationError(
                message="Ns %s is not valid iteration point" % text,
                cursor_position=0)


class VectorValidator(Validator):
    def __init__(self, method, preference=None):
        super().__init__()
        self.nfun = len(method.problem.nadir)
        self.preference = preference
        self.method = method

    def validate(self, document):
        for c in COMMANDS:
            if c in document.text:
                if c == "q":
                    sys.exit("User exit")
                return
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
                message="This input contains non-numeric characters",
                cursor_position=i)
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


def select_iter(method, default=1, no_print=False):
    if not no_print:
        method.print_current_iteration()
    if HAS_TUI:
        text = prompt(
            u"Select iteration point Ns: ", validator=IterValidator(method))
    else:
        text = str(default)
        # We do not have console, so go to next
        if method.current_iter == 3:
            text = "c"

    if "q" in text:
        sys.exit("User exit")
    elif text in COMMANDS:
        return text
    print("Selected iteration point: %s" % method.zhs[int(text) - 1])
    print("Reachable points: %s" % method.zh_reach[int(text) - 1])
    return method.zhs[int(text) - 1], method.zh_los[int(text) - 1]


def ask_pref(method, prev_pref):
    rank = prompt(
        u"Ranking: ",
        default=u",".join(map(str, prev_pref)),
        validator=VectorValidator(method),
    )
    if rank == "e":
        return rank
    pref = RelativeRanking(map(float, rank.split(",")))
    method.next_iteration(pref)
    method.print_current_iteration()


def iter_nautilus(method, preferences=None):
    """ Iterate NAUTILUS method either interactively, or using given preferences if given

    Paremters
    ---------

    method : instance of NAUTILUS subclass
       Fully initialized NAUTILUS method instance

    preferences 
       Predefined preferences to be used, if given


    """
    solution = None
    if preferences:
        pref_sel = preferences[0]

    elif HAS_TUI:
        print("Preference elicitation options:")
        print("\t1 - Percentages")
        print("\t2 - Relative ranks")
        # TODO Check what Direct actually means here
        # print("\t3 - Direct")

        pref_sel = int(
            prompt(
                u"Reference elicitation ",
                default=u"%s" % (1),
                validator=NumberValidator([1, 3]),
            ))

    else:
        raise TUIConsoleError("Console is not available")

    PREFCLASSES = [
        PercentageSpecifictation, RelativeRanking, DirectSpecification
    ]
    preference_class = PREFCLASSES[pref_sel - 1]

    print("Nadir: %s" % method.problem.nadir)
    print("Ideal: %s" % method.problem.ideal)

    if preferences:
        method.current_iter = method.user_iters = len(preferences[1])
    else:
        method.user_iters = method.current_iter = int(
            prompt(
                u"Ni: ",
                default=u"%s" % (method.current_iter),
                validator=NumberValidator(),
            ))

    print("Ni:", method.user_iters)
    pref = preference_class(method, None)
    default = u",".join(map(str, pref.default_input()))
    pref = preference_class(method, pref.default_input())

    mi = 0
    while method.current_iter:

        method.print_current_iteration()
        default = u",".join(map(str, pref.pref_input))

        if preferences:
            pref_input = ",".join(map(str, preferences[1][mi]))
            # pref_input = default
            # if method.current_iter == 5:
            #    pref_input = "c"
        else:
            pref_input = prompt(
                u"Preferences: ",
                default=default,
                validator=VectorValidator(method, pref),
            )
        brk = False
        for c in COMMANDS:
            if c in pref_input:
                brk = True
        if brk:
            solution = method.zh
            break
        pref = preference_class(method,
                                np.fromstring(
                                    pref_input, dtype=np.float, sep=","))
        solution, _ = method.next_iteration(pref)
        mi += 1
    return solution


def iter_enautilus(method):
    if HAS_TUI:
        method.user_iters = method.current_iter = int(
            prompt(
                u"Ni: ",
                default=u"%i" % method.current_iter,
                validator=NumberValidator(),
            ))
        method.Ns = int(
            prompt(u"Ns: ", default=u"5", validator=NumberValidator()))
    else:
        method.user_iters = 5
        method.Ns = 5
    print("Nadir: %s" % method.problem.nadir)
    print("Ideal: %s" % method.problem.ideal)

    method.next_iteration()
    points = None

    while method.current_iter:
        # method.print_current_iteration()
        pref = select_iter(method, 1)
        if pref in COMMANDS:
            break
        if HAS_TUI:
            method.Ns = int(
                prompt(
                    u"Ns: ",
                    default=u"%s" % (method.Ns),
                    validator=NumberValidator()))
        else:
            pass
        points = method.next_iteration(pref)

    if not method.current_iter:
        method.zh_prev = select_iter(method, 1)[0]
        method.current_iter -= 1
    return points
