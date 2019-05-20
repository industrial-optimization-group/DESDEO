#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 18 10:13:46 2019

@author: yuezhou
An example: how to use DESDEO to solve multiobjective optimization problems
 with decision uncertainty.
Decision uncertainty: the realization of x is subject to perturbation in the
 neighborhood. Due to this, the objective function values can be very different
 from the computed ones.
Here, we use a robustness measure to quantify the change in the objective
 functions and use this information to help the decision maker in making
 informed decisions.
We use the river pollution toy problem(see desdeo documentation about this problem)
 to construct the example: we extend the river pollution problem with the
 robustness measure as an additonal objective- RiverPollutionRobust.
The solution method demonstrated here is published in
Zhou-Kangas, Y., Miettinen, K., & Sindhya, K. (2019).
Solving multiobjective optimization problems with decision uncertainty : an interactive approach.
Journal of Business Economics, 89 (1), 25-51. doi:10.1007/s11573-018-0900-1
"""

import numpy as np

from desdeo.method.NIMBUS import NIMBUS
from desdeo.optimization import SciPyDE
from desdeo.problem.toy import RiverPollutionRobust

if __name__ == "__main__":
    problem = RiverPollutionRobust()

    method = NIMBUS(problem, SciPyDE)
    # the method takes problem and optimization method as input
    results = method.init_iteration()
    obj_fn = results.objective_vars[0]
    obj_fn[0:3] = np.multiply(obj_fn[0:3], -1)
    print(obj_fn)
