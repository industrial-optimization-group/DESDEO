import math

from desdeo.optimization import SciPyDE
from desdeo.problem import PythonProblem, Variable
from desdeo.problem.RangeEstimators import default_estimate


class CylinderProblem(PythonProblem):
    """
    In this problem consider a cell shaped like a cylinder with a circular
    cross-section.

    The shape of the cell is here determined by two quantities, its radius `r`
    and its height `h`. We want to maximize the volume of the cylinder and
    minimize the surface area. In addition to this, cylinder's height should be
    close to 15 units, i.e. we minimize the absolute difference between the
    height and 15.

    Finally the cylinder's height must be greater or equal to its width. Thus
    there are 2 decision variables, 3 objectives and 1 constraint in this
    problem.
    """

    def __init__(self):
        super().__init__(
            nobj=3,
            nconst=1,
            maximized=[True, False],
            objectives=["Volume", "Surface Area", "Height Difference"],
            name="Cylinder problem",
        )
        self.add_variables(Variable([5, 15], starting_point=10, name="Radius"))
        self.add_variables(Variable([5, 25], starting_point=10, name="Height"))
        ideal, nadir = default_estimate(SciPyDE, self)
        self.ideal = ideal
        self.nadir = nadir

    def evaluate(self, population):
        objectives = []

        for values in population:
            r, h = values

            objectives.append(
                [
                    -(math.pi * r ** 2 * h),
                    2 * math.pi * r ** 2 + 2 * math.pi * r * h,
                    abs(h - 15.0),
                ]
            )

        return objectives
