"""Test for adding and utilizing scalarization functions."""

from desdeo.problem import river_pollution_problem
from desdeo.tools.scalarization import create_asf, add_scalarization_function


def test_add_asf():
    problem = river_pollution_problem()

    asf = create_asf(problem, [0, 0, 0, 0, 0])
    problem, symbol = add_scalarization_function(
        problem, asf, symbol="ASF", name="The achievement scalarizing function", description="Added to test"
    )

    scal_funcs = problem.scalarizations_funcs

    assert False  # not testing anything right now
