"""
This module contains simple "toy" problems suitable for demonstrating different
interactive multi-objective optimization methods.
"""

from .cylinder import CylinderProblem
from .river_pollution import RiverPollution

__all__ = ["RiverPollution", "CylinderProblem"]
