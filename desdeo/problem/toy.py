"""
This module contains simple "toy" problems suitable for demonstrating different
interactive multi-objective optimization methods.
"""

import math

from desdeo.optimization import SciPyDE
from desdeo.problem import PythonProblem, Variable
from desdeo.problem.RangeEstimators import default_estimate


class RiverPollution(PythonProblem):
    """
    River pollution problem by Narula and Weistroffer [1]

    The problem has four objectives and two variables

    The problem describes a (hypothetical) pollution problem
    of a river, where a fishery and a city are polluting
    water. The decision variables represent the proportional
    amounts of biochemical oxygen demanding material removed
    from water in two treatment plants located after the
    fishery and after the city.

    The first and second objective functions describe the
    quality of water after the fishery and after the city,
    respectively, while objective functions three and four
    represent the percent return on investment at the fishery
    and the addition to the tax rate in the
    city. respectively.


    References
    ----------

    [1] Narula, S. & Weistroffer, H. A flexible method for
      nonlinear multicriteria decision-making problems
      Systems, IEEE Transactions on Man and Cybernetics,
      1989, 19, 883-887.
"""

    def __init__(self):
        super().__init__(
            nobj=4,
            nconst=0,  # Optional
            maximized=[True, True, True, False],  # Optional
            objectives=[
                "Water Quality Fishery",  # Optional
                "Water Quality City",
                "Fishery ROI",
                "City Tax Increase",
            ],
            name="River pollution method",  # Optional
        )
        self.add_variables(
            Variable([0.0, 1.0], starting_point=0.5, name="BOD City")  # Optional
        )  # Optional
        self.add_variables(
            Variable([0.0, 1.0], starting_point=0.5, name="BOD City")  # Optional
        )  # Optional
        ideal, nadir = default_estimate(SciPyDE, self)
        self.ideal = ideal
        self.nadir = nadir

    def evaluate(self, population):
        objectives = []

        for values in population:
            res = []
            x0_2 = math.pow(values[0], 2)
            x1_2 = math.pow(values[1], 2)

            res.append(-1.0 * (4.07 + 2.27 * values[0]))

            res.append(
                -1.0
                * (
                    2.6
                    + 0.03
                    * values[0]
                    + 0.02
                    * values[1]
                    + 0.01
                    / (1.39 - x1_2)
                    + 0.3
                    / (1.39 - x1_2)
                )
            )

            res.append(-1.0 * (8.21 - 0.71 / (1.09 - x0_2)))

            res.append(-1.0 * (0.96 - 0.96 / (1.09 - x1_2)))

            objectives.append(res)

        return objectives
