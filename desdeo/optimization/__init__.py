"""
This package contains methods for solving single-objective optimisation
problems. These are contained in `OptimizationMethod`. It also contains
scalarisation functions, used for converting multi-objective problems into
single-objective fucntions. These are contained in `OptimizationProblem`. Both
are used as primitives by the methods defined in `desdeo.method`.
"""

from .OptimizationMethod import PointSearch, SciPy, SciPyDE

__all__ = ["PointSearch", "SciPyDE", "SciPy"]
