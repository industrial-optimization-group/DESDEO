"""
This module contains simple "toy" problems suitable for demonstrating different
interactive multi-objective optimization methods.
"""

from .river_pollution import RiverPollution
from .cylinder import CylinderProblem

__all__ = ["RiverPollution", "CylinderProblem"]
