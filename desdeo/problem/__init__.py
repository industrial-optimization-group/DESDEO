"""
This package contains tools for modelling multi-objective optimisation
problems.
"""

from .Problem import PreGeneratedProblem, PythonProblem, Variable

__all__ = ["PythonProblem", "PreGeneratedProblem", "Variable"]
