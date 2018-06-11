# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto

"""
This package contains various classes acting as containers for preference
information given by a decision maker about which objectives they are concerned
with and to what degree. It is sued by the methods defined in `desdeo.method`.
"""

__all__ = ["NIMBUSClassification"]
from .PreferenceInformation import NIMBUSClassification
