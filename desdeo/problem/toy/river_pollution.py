from desdeo.problem.porcelain import Objective, PorcelainProblem, Variable


class RiverPollution(PorcelainProblem):
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

    bod_fishery = Variable(0.0, 1.0, 0.5, "BOD Fishery")
    bod_city = Variable(0.0, 1.0, 0.5, "BOD City")

    @Objective("Water Quality Fishery", maximized=True)
    def wq_fishery(bod_fishery, bod_city):
        return -1.0 * (4.07 + 2.27 * bod_fishery)

    @Objective("Water Quality City", maximized=True)
    def wq_city(bod_fishery, bod_city):
        return (
            2.6
            + 0.03
            * bod_fishery
            + 0.02
            * bod_city
            + 0.01
            / (1.39 - bod_fishery ** 2)
            + 0.3
            / (1.39 - bod_city ** 2)
        )

    @Objective("Fishery ROI", maximized=True)
    def fishery_roi(bod_fishery, bod_city):
        return 8.21 - 0.71 / (1.09 - bod_fishery ** 2)

    @Objective("City Tax Increase", maximized=False)
    def city_tax(bod_fishery, bod_city):
        return 0.96 * (1 / (1.09 - bod_city ** 2) - 1)

    class Meta:
        name = "River pollution method"
