from desdeo.adm import BaseADM
from desdeo.problem.schema import Problem

"""ADMChen.py
This module implements the ADM proposed by Chen et al.

References:
Chen, L., Miettinen, K., Xin, B., & Ojalehto, V. (2023). Comparing reference point based interactive multiobjective optimization methods without a human decision maker.
"""


class ADMChen(BaseADM):
    def __init__(
        self,
        problem: Problem,
        it_learning_phase: int,
        it_decision_phase: int,
        lattice_resolution: int = None,
        number_of_vectors: int = None,
    ):
        super().__init__(problem, it_learning_phase, it_decision_phase)
