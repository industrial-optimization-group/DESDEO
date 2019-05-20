#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 18 10:23:15 2019

@author: yuezhou
"""

from desdeo.problem.porcelain import Objective, PorcelainProblem, Variable


class RiverPollutionRobust(PorcelainProblem):
    bod_fishery = Variable(0.0, 1.0, 0.5, "BOD Fishery")
    bod_city = Variable(0.0, 1.0, 0.5, "BOD City")

    # the question is how to define the function first, then say that it is a function.
    # then you can reuse it.
    @Objective("Water Quality Fishery", maximized=True)
    def wq_fishery(bod_fishery, bod_city):  # need a wrapper here
        return 1.0 * (4.07 + 2.27 * bod_fishery)

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

    # here is the robustness measure using the approach of dicretizing the uncertainty interval
    @Objective("Robustness", maximized=False)
    def robustness(bod_fishery, bod_city):
        ideal_n = [-6.34, -3.45, -7.56, -0.08]  # nominal ideal point
        nadir_n = [-4.07, -2.84, -0.32, 9.71]  # nominal nadir point

        # problem_n = RiverPollution() #we need the nominal problem to calculate the bounds
        def wq_fishery(bod_fishery, bod_city):
            return 1.0 * (4.07 + 2.27 * bod_fishery)

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

        def fishery_roi(bod_fishery, bod_city):
            return 8.21 - 0.71 / (1.09 - bod_fishery ** 2)

        def city_tax(bod_fishery, bod_city):
            return 0.96 * (1 / (1.09 - bod_city ** 2) - 1)

        per = 0.1  # this can be used as a list if decision variables have different ranges.
        fishery_interval = [bod_fishery - per, bod_fishery + per]
        city_interval = [bod_city - per, bod_city - per]
        # discretizing
        num_com = 10
        wq_fishery_list = []
        wq_city_list = []
        fishery_roi_list = []
        city_tax_list = []
        for i in range(0, num_com):
            # evaluating all discretized values
            wq_fishery_list.append(
                wq_fishery(
                    fishery_interval[0] + per / num_com * i,
                    city_interval[0] + per / num_com * i,
                )
            )
            wq_city_list.append(
                wq_city(
                    fishery_interval[0] + per / num_com * i,
                    city_interval[0] + per / num_com * i,
                )
            )
            fishery_roi_list.append(
                fishery_roi(
                    fishery_interval[0] + per / num_com * i,
                    city_interval[0] + per / num_com * i,
                )
            )
            city_tax_list.append(
                city_tax(
                    fishery_interval[0] + per / num_com * i,
                    city_interval[0] + per / num_com * i,
                )
            )

        # taking max and min for each
        upper = [
            max(wq_fishery_list),
            max(wq_city_list),
            max(fishery_roi_list),
            max(city_tax_list),
        ]
        lower = [
            min(wq_fishery_list),
            min(wq_city_list),
            min(fishery_roi_list),
            min(city_tax_list),
        ]
        diff = []

        for j in range(0, 4):
            diff.append((upper[j] - lower[j]) / (nadir_n[j] - ideal_n[j]))
        # print (diff)
        return max(diff)

    class Meta:
        name = "River pollution robust"
