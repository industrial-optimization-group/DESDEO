# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
Problems provided by  Narula and Weistroffer


* River pollution problem

"""
from desdeo.method import NIMBUS, NAUTILUSv1
from desdeo.optimization import SciPyDE
from desdeo.preference import NIMBUSClassification
from desdeo.problem.toy import RiverPollution
from desdeo.utils import tui

if __name__ == "__main__":
    # Solve River Pollution problem using NAUTILUS
    # Using tui
    print("Solve with NAUTILUS method")
    natmeth = NAUTILUSv1(RiverPollution(), SciPyDE)
    NAUTILUS_solution = tui.iter_nautilus(natmeth)
    print("NAUTILUS solution")
    print(NAUTILUS_solution)
    # Output:
    # [-6.2927077117830965, -3.4038593790999485,
    #   -7.401394350956817, 1.6201876469013787]

    # Continue solving  River Pollution problem
    # From NAUTILUS solution

    nimmeth = NIMBUS(RiverPollution(), SciPyDE)
    nimmeth.init_iteration()
    print("Solving with NIMBUS method")
    class1 = NIMBUSClassification(
        nimmeth, [(">=", -5.5), (">=", -3.0), ("<=", -6.5), ("<=", -2.0)]
    )
    iter1 = nimmeth.next_iteration(preference=class1)
    print("NIMBUS solutions")
    print(iter1)
    # Output
    # [[-5.685179670183404, -2.845500670078188, -6.9936653595242255, -0.07781863514782916],
    #  [-6.104997526730949, -2.8792454934814242, -5.730370900831871, 0.03584500974406313]]
