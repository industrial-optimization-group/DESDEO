# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto


class DESDEOException(Exception):
    pass


""" Base DESDEO excpetion, should not be directly raised"""


class OptimizationProblemError(DESDEOException):
    pass


class ProblemDefinitionError(DESDEOException):
    pass


class PreferenceUndefinedError(DESDEOException):
    pass
