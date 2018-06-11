"""
This package contains methods for solving single-objective optimisation
problems. They are used as primitives by the methods defined in
`desdeo.method`.
"""

from .OptimizationMethod import PointSearch
from .OptimizationMethod import SciPyDE
from .OptimizationMethod import SciPy

__all__ = ["PointSearch", "SciPyDE", "SciPy"]
