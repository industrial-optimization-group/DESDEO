"""Pre-defined multiobjective optimization problems.

Pre-defined problems for, e.g.,
testing and illustration purposed are defined here.
"""

from .binh_and_korn_problem import binh_and_korn
from .dtlz2_problem import dtlz2
from .forest_problem import forest_problem, forest_problem_discrete
from .knapsack_problem import simple_knapsack, simple_knapsack_vectors
from .momip_problem import momip_ti2, momip_ti7
from .nimbus_problem import nimbus_test_problem
from .pareto_navigator_problem import pareto_navigator_test_problem
from .re_problem import re21, re22, re23, re24
from .river_pollution_problem import river_pollution_problem, river_pollution_problem_discrete, river_pollution_scenario
from .simple_problem import (simple_test_problem, simple_integer_test_problem,
                            simple_data_problem, simple_linear_test_problem, simple_scenario_test_problem)
from .simulator_problem import simulator_problem
from .spanish_sustainability_problem import spanish_sustainability_problem, spanish_sustainability_problem_discrete
from .zdt_problem import zdt1, zdt2, zdt3
from.rocket_injector_design_problem import rocket_injector_design