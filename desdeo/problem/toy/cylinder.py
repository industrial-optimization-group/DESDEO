import math

from desdeo.problem.porcelain import Objective, PorcelainProblem, Variable


class CylinderProblem(PorcelainProblem):
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

    r = Variable(5, 15, 10, "Radius")
    h = Variable(5, 25, 10, "Height")

    @Objective("Volume", maximized=True)
    def volume(r, h):
        return math.pi * r ** 2 * h

    @Objective("Surface Area", maximized=False)
    def surface_area(r, h):
        return 2 * math.pi * r ** 2 + 2 * math.pi * r * h

    @Objective("Height Difference", maximized=False)
    def height_diff(r, h):
        return abs(h - 15.0)

    # TODO
    # @Constraint("Height greater than width")
    # def h_gt_w(r, h):
    # return 2 * r <= h

    class Meta:
        name = "Cylinder Problem"
