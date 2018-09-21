from typing import Dict, Tuple

import numpy as np

from desdeo.method.base import InteractiveMethod
from .base import ReferencePoint


class NIMBUSClassification(ReferencePoint):
    """
    Preferences by NIMBUS classification

    Attributes
    ----------
    _classification: Dict (objn_n, (class,value))
        NIMBUSClassification information pairing  objective n to  a classification
        with value if needed

    _maxmap: NIMBUSClassification (default:None)
        Minimization - maximiation mapping of classification symbols

    """
    _maxmap = {">": "<", ">=": "<=", "<": ">", "<=": ">=", "=": "="}

    def __init__(self, method: InteractiveMethod, functions, **kwargs) -> None:
        """ Initialize the classification information

        Parameters
        ----------
        functions: list ((class,value)
            Function classification information
        """
        super().__init__(method, **kwargs)
        self._classification: Dict[int, Tuple[str, float]] = {}
        for f_id, v in enumerate(functions):
            # This is classification
            try:
                iter(v)
                self._classification[f_id] = v
            # This is reference point
            except TypeError:
                if np.isclose(v, self._method.problem.ideal[f_id]):
                    self._classification[f_id] = (
                        "<", self._method.problem.selected[f_id]
                    )
                elif np.isclose(v, self._method.problem.nadir[f_id]):
                    self._classification[f_id] = (
                        "<>", self._method.problem.selected[f_id]
                    )
                elif np.isclose(v, self._method.problem.selected[f_id]):
                    self._classification[f_id] = (
                        "=", self._method.problem.selected[f_id]
                    )
                elif (
                    v
                    < self._method.problem.as_minimized(self._method.problem.selected)[
                        f_id
                    ]
                ):
                    self._classification[f_id] = ("<=", v)
                else:
                    self._classification[f_id] = (">=", v)
            else:
                self._classification[f_id] = v

        self._reference_point = self._as_reference_point()
        self._preference = self._classification

    def __getitem__(self, key):
        """Shortcut to query a classification."""
        return self._classification[key]

    def __setitem__(self, key, value):
        """Shortcut to manipulate a single classification."""
        self._classification[key] = value

    def with_class(self, cls):
        """ Return functions with the class
        """
        rcls = []
        for key, value in self._classification.items():
            if value[0] == cls:
                rcls.append(key)
        return rcls

    def _as_reference_point(self) -> np.ndarray:
        """ Return classification information as reference point
        """
        ref_val = []
        for fn, f in self._classification.items():
            if f[0] == "<":
                ref_val.append(self._method.problem.ideal[fn])
            elif f[0] == "<>":
                ref_val.append(self._method.problem.nadir[fn])
            else:
                ref_val.append(f[1])

        return np.array(ref_val)
