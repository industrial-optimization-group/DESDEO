"""Test for adding and utilizing scalarization functions."""
import pytest

from desdeo.problem import GenericEvaluator, river_pollution_problem, simple_test_problem
from desdeo.tools.scalarization import add_scalarization_function, create_asf, create_weighted_sums


@pytest.fixture
def river_w_ideal_and_nadir():
    """Adds an ideal and nadir point to the river pollution problem for testing purposes."""
    problem = river_pollution_problem()
    return problem.model_copy(
        update={
            "objectives": [
                objective.model_copy(update={"ideal": 0.5, "nadir": 5.5}) for objective in problem.objectives
            ]
        }
    )


def test_create_asf(river_w_ideal_and_nadir):
    """Tests that the achievement scalarization function is created correctly."""
    problem = river_w_ideal_and_nadir

    asf = create_asf(problem, [1, 2, 3, 2, 1], delta=0.1, rho=2.2)

    assert asf == (
        "Max((f_1_min - 1) / (5.5 - (0.5 - 0.1)), (f_2_min - 2) / (5.5 - (0.5 - 0.1)), "
        "(f_3_min - 3) / (-5.5 - (-0.5 - 0.1)), (f_4_min - 2) / (-5.5 - (-0.5 - 0.1)), "
        "(f_5_min - 1) / (5.5 - (0.5 - 0.1))) + 2.2 * (f_1_min / (5.5 - (0.5 - 0.1)) + f_2_min / (5.5 - (0.5 - 0.1)) "
        "+ f_3_min / (-5.5 - (-0.5 - 0.1)) + f_4_min / (-5.5 - (-0.5 - 0.1)) + f_5_min / (5.5 - (0.5 - 0.1)))"
    )


def test_create_ws():
    """Tests that the weighted sum scalarization is added correctly."""
    problem = simple_test_problem()
    ws = [1, 2, 1, 3, 7.2]

    sf = create_weighted_sums(problem, ws)

    assert sf == "(1 * f_1_min) + (2 * f_2_min) + (1 * f_3_min) + (3 * f_4_min) + (7.2 * f_5_min)"


def test_add_scalarization_function(river_w_ideal_and_nadir):
    """Tests that scalarization functions are added correctly."""
    problem = river_w_ideal_and_nadir

    ws = [1, 2, 3, 4, 5]
    wsf = create_weighted_sums(problem, ws)

    ref_point = [1, 2, 3, 4, 5]
    asf = create_asf(problem, ref_point)

    problem, symbol_ws = add_scalarization_function(problem, ws, "WS", name="Weighted sums")
    problem, symbol_asf = add_scalarization_function(problem, asf, "ASF", name="Achievement scalarizing function")

    assert len(problem.scalarizations_funcs) == 2  # there should be two scalarization functions now
    assert problem.scalarizations_funcs[0].name == "Weighted sums"
    assert problem.scalarizations_funcs[1].name == "Achievement scalarizing function"
    assert problem.scalarizations_funcs[0].symbol == symbol_ws
    assert problem.scalarizations_funcs[1].symbol == symbol_asf
