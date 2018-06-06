# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
"""

from typing import List, Optional, Tuple

import numpy as np


class ResultSet(object):
    """
    Class to store sets of results.
    """

    def __init__(
        self, data: Optional[List[Tuple[np.ndarray, List[float]]]] = None, meta=None
    ) -> None:
        """
        Construct a Result from data, such as a list of (decision, objective) pairs.
        """
        if data is None:
            self._data = []  # type: List[Tuple[np.ndarray, List[float]]]
        else:
            self._data = data

        self._meta = meta

    @property
    def decision_vars(self):
        return [decis for decis, _ in self._data]

    @property
    def objective_vars(self):
        return [obj for _, obj in self._data]

    @property
    def meta(self):
        return self._meta

    @property
    def items(self):
        return self._data

    def __repr__(self):
        return "ResultSet({!r}, {!r})".format(self.items, self.meta)
