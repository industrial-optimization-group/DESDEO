# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Copyright (c) 2016  Vesa Ojalehto

"""
This package contains methods for interactively solving multi-objective
optimisation problems. Currently this includes the NIMBUS methods and several
variants of the NAUTILUS method.
"""

__all__ = ["NAUTILUSv1", "ENAUTILUS", "NNAUTILUS", "NIMBUS"]

from .NAUTILUS import ENAUTILUS, NNAUTILUS, NAUTILUSv1
from .NIMBUS import NIMBUS
