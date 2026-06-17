"""Test some of the test problems found in DESDEO."""

import numpy as np
import numpy.testing as npt
import pytest

from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import PolarsEvaluator, PyomoEvaluator
from desdeo.problem.testproblems import (
    binh_and_korn,
    dtlz2,
    dtlz4,
    forest_problem,
    lame_superspheres,
    mcwb_equilateral_tbeam_problem,
    mcwb_hollow_rectangular_problem,
    mcwb_ragsdell1976_problem,
    mcwb_solid_rectangular_problem,
    mcwb_square_channel_problem,
    mcwb_tapered_channel_problem,
    re21,
    re22,
    re23,
    re24,
    river_pollution_problem,
    river_pollution_scenario,
    spanish_sustainability_problem,
    zdt1,
    zdt2,
    zdt3,
    zdt4,
    zdt6,
)
from desdeo.tools import GurobipySolver, payoff_table_method


@pytest.mark.testproblem
def test_dtlz2():
    """Test that the DTLZ2 problem initializes and evaluates correctly."""
    test_variables = [3, 5, 10, 50]
    test_objectives = [2, 4, 5, 7]

    for n_variables, n_objectives in zip(test_variables, test_objectives, strict=True):
        problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)

        assert len(problem.variables) == n_variables
        assert len(problem.objectives) == n_objectives

        xs = {f"{var.symbol}": [0.5] for var in problem.variables}

        evaluator = PolarsEvaluator(problem)

        res = evaluator.evaluate(xs)

        assert np.isclose(sum(res[obj.symbol][0] ** 2 for obj in problem.objectives), 1.0)

    problem = dtlz2(n_variables=5, n_objectives=3)

    xs = {f"{var.symbol}": [0.55] for var in problem.variables}

    evaluator = PolarsEvaluator(problem)

    res = evaluator.evaluate(xs)

    assert sum(res[obj.symbol][0] ** 2 for obj in problem.objectives) != 1.0


@pytest.mark.testproblem
def test_dtlz4():
    """Test that the DTLZ4 problem initializes and evaluates correctly."""
    test_variables = [3, 5, 10, 50]
    test_objectives = [2, 4, 5, 7]

    for n_variables, n_objectives in zip(test_variables, test_objectives, strict=True):
        problem = dtlz4(n_variables=n_variables, n_objectives=n_objectives)

        assert len(problem.variables) == n_variables
        assert len(problem.objectives) == n_objectives

        xs = {f"{var.symbol}": [0.5] for var in problem.variables}

        evaluator = PolarsEvaluator(problem)

        res = evaluator.evaluate(xs)

        assert np.isclose(sum(res[obj.symbol][0] ** 2 for obj in problem.objectives), 1.0)

    n_variables = 5
    n_objectives = 3
    problem = dtlz4(n_variables, n_objectives)

    xs = {f"{var.symbol}": [0.55] for var in problem.variables}

    evaluator = PolarsEvaluator(problem)

    res = evaluator.evaluate(xs)

    f1 = res["f_1"]
    assert np.isclose(f1, 1.0075)


@pytest.mark.testproblem
@pytest.mark.parametrize("gamma", [0.5, 1.0, 2.0, 3.0])
@pytest.mark.parametrize(("n_variables", "n_objectives"), [(2, 2), (5, 3), (7, 4)])
def test_lame_superspheres(gamma, n_variables, n_objectives):
    """Test that the Lamé superspheres problem matches the supersphere geometry.

    For any decision vector, the objectives must lie on a Lamé supersphere of
    radius (1 + g(x)), i.e. sum_i f_i**gamma == (1 + g(x))**gamma (Emmerich &
    Deutz, 2007, Eqs. 8 and 13). The Pareto front is the g(x) == 0 case.
    """
    problem = lame_superspheres(
        n_variables=n_variables,
        n_objectives=n_objectives,
        gamma=gamma,
    )

    assert len(problem.variables) == n_variables
    assert len(problem.objectives) == n_objectives

    rng = np.random.default_rng(42)
    n_samples = 16
    xs = {f"x_{i}": rng.random(n_samples).tolist() for i in range(1, n_variables + 1)}

    evaluator = PolarsEvaluator(problem)
    res = evaluator.evaluate(xs)

    objs = np.array([res[f"f_{m}"].to_numpy() for m in range(1, n_objectives + 1)])
    g = res["g"].to_numpy()

    assert np.all(np.isfinite(objs))

    # Every evaluated point must lie on the supersphere of radius (1 + g(x)).
    lhs = np.sum(objs**gamma, axis=0)
    rhs = (1.0 + g) ** gamma
    assert np.allclose(lhs, rhs)


@pytest.mark.testproblem
def test_lame_superspheres_invalid_arguments():
    """Test that invalid objective/variable counts are rejected."""
    with pytest.raises(ValueError, match="n_objectives must be at least 2"):
        lame_superspheres(n_variables=2, n_objectives=1)

    with pytest.raises(ValueError, match="n_variables must be greater than or equal"):
        lame_superspheres(n_variables=2, n_objectives=3)


@pytest.mark.testproblem
def test_re21():
    """Test that the four bar truss design problem evaluates correctly."""
    problem = re21()

    evaluator = PolarsEvaluator(problem)

    xs = {f"{var.symbol}": [2] for var in problem.variables}

    res = evaluator.evaluate(xs)
    obj_symbols = [obj.symbol for obj in problem.objectives]

    objective_values = res[obj_symbols].to_numpy()[0]
    assert np.allclose(objective_values, np.array([2048.528137, 0.02]))


@pytest.mark.testproblem
def test_re22():
    """Test that the reinforced concrete beam design problem evaluates correctly."""
    problem = re22()

    evaluator = PolarsEvaluator(problem)

    xs = {"x_2": [10], "x_3": [20]}
    for i in range(len(problem.variables) - 2):
        if i == 68:
            xs[f"x_1_{i}"] = [1.0]
        else:
            xs[f"x_1_{i}"] = [0.0]

    res = evaluator.evaluate(xs)

    obj_values = [res[obj.symbol][0] for obj in problem.objectives]
    assert np.allclose(obj_values, np.array([421.938, 2]))


@pytest.mark.testproblem
def test_re23():
    """Test that the pressure vessel design problem evaluates correctly."""
    problem = re23()

    evaluator = PolarsEvaluator(problem)

    xs = {"x_1": [50, 11], "x_2": [50, 63], "x_3": [10, 78], "x_4": [10, 187]}
    expected_result = np.array([[2996.845703, 5.9616], [49848.35467, 4266017.057]])

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i])


@pytest.mark.testproblem
def test_re24():
    """Test that the hatch cover design problem evaluates correctly."""
    problem = re24()

    evaluator = PolarsEvaluator(problem)

    xs = {"x_1": [2, 3.3], "x_2": [20, 41.7]}
    expected_result = np.array([[2402, 0], [5007.3, 0]])

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i])


@pytest.mark.testproblem
@pytest.mark.forest_problem
@pytest.mark.gurobipy
def test_forest_problem():
    """Test the forest problem implementation."""
    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=1,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 45654.952)
    assert np.isclose(res.optimal_objectives["f_2"], 1043.729)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 45654.952)
    assert np.isclose(res.optimal_objectives["f_2"], 1043.729)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 29722.469)
    assert np.isclose(res.optimal_objectives["f_2"], 259.236)
    assert np.isclose(res.optimal_objectives["f_3"], 36780.631)

    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=2,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 42937.004)
    assert np.isclose(res.optimal_objectives["f_2"], 1275.250)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 42937.004)
    assert np.isclose(res.optimal_objectives["f_2"], 1275.250)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 17555.857)
    assert np.isclose(res.optimal_objectives["f_2"], -169.233)
    assert np.isclose(res.optimal_objectives["f_3"], 53632.887)

    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=3,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 82195.014)
    assert np.isclose(res.optimal_objectives["f_2"], 994.578)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 82195.014)
    assert np.isclose(res.optimal_objectives["f_2"], 994.578)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 18207.905)
    assert np.isclose(res.optimal_objectives["f_2"], -2014.855)
    assert np.isclose(res.optimal_objectives["f_3"], 152149.555)

    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=4,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 70547.896)
    assert np.isclose(res.optimal_objectives["f_2"], 1120.833)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 70547.896)
    assert np.isclose(res.optimal_objectives["f_2"], 1120.833)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 17379.117)
    assert np.isclose(res.optimal_objectives["f_2"], -1467.016)
    assert np.isclose(res.optimal_objectives["f_3"], 122271.740)

    problem = forest_problem(
        simulation_results="./tests/data/alternatives_290124.csv",
        treatment_key="./tests/data/alternatives_key_290124.csv",
        holding=5,
        comparing=True,
    )
    solver = GurobipySolver(problem)

    res = solver.solve("f_1_min")
    assert np.isclose(res.optimal_objectives["f_1"], 78183.469)
    assert np.isclose(res.optimal_objectives["f_2"], 961.411)
    assert np.isclose(res.optimal_objectives["f_3"], 100.783)

    res = solver.solve("f_2_min")
    assert np.isclose(res.optimal_objectives["f_1"], 75793.429)
    assert np.isclose(res.optimal_objectives["f_2"], 994.566)
    assert np.isclose(res.optimal_objectives["f_3"], 0.0)

    res = solver.solve("f_3_min")
    assert np.isclose(res.optimal_objectives["f_1"], 10885.988)
    assert np.isclose(res.optimal_objectives["f_2"], -2202.283)
    assert np.isclose(res.optimal_objectives["f_3"], 154240.330)


@pytest.mark.testproblem
def test_evaluate_spanish_sustainability():
    """Test the Spanish sustainability problem."""
    problem = spanish_sustainability_problem()

    polars_evaluator = PolarsEvaluator(problem)
    pyomo_evaluator = PyomoEvaluator(problem)

    # row 44 from excel
    input_1 = {
        "X": [
            [6.4399, 89.666, 16.517, 2.0723, 1.0, 1.9469, 17.206, 13.326, 70.0, 102.49, 120.0],
        ]
    }
    expected_1 = {"f1": 1.1573, "f2": 0.7149, "f3": 2.8989}

    result_1_polars = polars_evaluator.evaluate(input_1)
    result_1_pyomo = pyomo_evaluator.evaluate(input_1)

    npt.assert_allclose(result_1_polars["f1"], result_1_pyomo["f1"])
    npt.assert_allclose(result_1_polars["f2"], result_1_pyomo["f2"])
    npt.assert_allclose(result_1_polars["f3"], result_1_pyomo["f3"])

    npt.assert_allclose(result_1_polars["f1"], expected_1["f1"], atol=1e-2)
    npt.assert_allclose(result_1_polars["f2"], expected_1["f2"], atol=1e-2)
    npt.assert_allclose(result_1_polars["f3"], expected_1["f3"], atol=1e-2)

    for con in problem.constraints:
        npt.assert_array_less(result_1_polars[con.symbol], 0.0)

    # rows 102-108
    input_2 = {
        "X": [
            [6.4344, 90.0, 16.514, 2.0723, 1.0, 1.9443, 17.37, 13.348, 70.0, 104.99, 82.935],
            [6.4344, 90.0, 16.515, 2.0723, 1.0, 1.9443, 17.249, 13.348, 70.0, 105.0, 80.177],
            [6.4344, 90.0, 16.515, 2.0723, 1.0, 1.9443, 17.229, 13.348, 70.0, 105.0, 80.0],
            [6.4344, 90.0, 16.516, 2.0723, 1.0, 1.9443, 17.352, 13.347, 70.0, 104.82, 80.0],
            [6.4344, 90.0, 16.514, 2.0723, 1.0, 1.9443, 18.465, 13.347, 70.0, 104.99, 82.337],
            [6.4918, 89.999, 16.51, 2.0723, 1.0, 1.9639, 18.124, 13.348, 70.0, 104.79, 80.372],
            [6.4344, 90.0, 16.514, 2.0723, 1.0, 1.9443, 18.168, 13.348, 70.0, 104.98, 80.181],
        ]
    }

    expected_2 = {
        "f1": [
            1.1653,
            1.1653,
            1.1653,
            1.1653,
            1.1653,
            1.1647,
            1.1653,
        ],
        "f2": [
            0.82477,
            0.8327,
            0.8331,
            0.83341,
            0.8357,
            0.8382,
            0.8402,
        ],
        "f3": [
            2.8042,
            2.7998,
            2.7996,
            2.7988,
            2.7934,
            2.7928,
            2.7918,
        ],
    }

    result_2_polars = polars_evaluator.evaluate(input_2)
    result_2_pyomo = pyomo_evaluator.evaluate(input_2)

    for i in range(7):
        npt.assert_allclose(result_2_polars["f1"][i], result_2_pyomo[i]["f1"])
        npt.assert_allclose(result_2_polars["f2"][i], result_2_pyomo[i]["f2"])
        npt.assert_allclose(result_2_polars["f3"][i], result_2_pyomo[i]["f3"])

        npt.assert_allclose(result_2_polars["f1"][i], expected_2["f1"][i], atol=1e-2)
        npt.assert_allclose(result_2_polars["f2"][i], expected_2["f2"][i], atol=1e-2)
        npt.assert_allclose(result_2_polars["f3"][i], expected_2["f3"][i], atol=1e-2)

        for con in problem.constraints:
            npt.assert_array_less(result_2_polars[con.symbol][i], 0.0)


@pytest.mark.testproblem
def test_solve_spanish_sustainability_problem():
    """Test the Spanish sustainability problem."""
    problem = spanish_sustainability_problem()

    # ideal = {"f1": 1.17, "f2": 1.98, "f3": 2.93}
    # nadir = {"f1": 1.15, "f2": 0.63, "f3": 1.52}

    ref_point = {"f1": 1.162, "f2": 0.69, "f3": 2.91}

    res = rpm_solve_solutions(problem, ref_point)

    assert len(res) == 4

    for i in range(len(res)):
        assert res[i].success
        for con in problem.constraints:
            npt.assert_array_less(res[i].constraint_values[con.symbol], 1e-5)


@pytest.mark.testproblem
def test_river_scenario():
    """Test that the scenario-based river pollution problem works."""
    model = river_pollution_scenario()

    assert len(model.scenario_tree["ROOT"]) == 6

    for i in range(6):
        problem_scenario = model.get_scenario_problem(f"scenario_{i + 1}")
        problem_scenario = model.get_scenario_problem(f"scenario_{i + 1}")
        assert len(problem_scenario.objectives) == 4

    problem_scenario_2 = model.get_scenario_problem("scenario_2")

    ideal_2, nadir_2 = payoff_table_method(problem_scenario_2)

    assert len(ideal_2) == 4
    assert len(nadir_2) == 4


@pytest.mark.testproblem
def test_mcwb_solid_rectangular_problem():
    """Test that the MCWB problem initializes and evaluates correctly."""
    problem = mcwb_solid_rectangular_problem()
    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [0.5] for var in problem.variables}
    res = evaluator.evaluate(xs)

    f1 = res["f_1"][0]
    f2 = res["f_2"][0]

    # these are the values we are getting now, are they even correct
    assert np.isclose(f1, 27573.75)
    assert np.isclose(f2, 0.0000012)


@pytest.mark.testproblem
def test_mcwb_hollow_rectangular_problem():
    """Test that the MCWB problem initializes and evaluates correctly."""
    problem = mcwb_hollow_rectangular_problem()
    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [0.5] for var in problem.variables}
    res = evaluator.evaluate(xs)

    f1 = res["f_1"][0]
    f2 = res["f_2"][0]

    # these are the values we are getting now, are they even correct?
    assert np.isclose(f1, 26200.0)
    assert np.isclose(f2, float("inf"))


@pytest.mark.testproblem
def test_mcwb_equilateral_tbeam_problem():
    """Test that the MCWB problem initializes and evaluates correctly."""
    problem = mcwb_equilateral_tbeam_problem()
    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [0.5] for var in problem.variables}
    res = evaluator.evaluate(xs)

    f1 = res["f_1"][0]
    f2 = res["f_2"][0]

    # these are the values we are getting now, are they even correct?
    assert np.isclose(f1, 27573.75)
    assert np.isclose(f2, 1.2e-6, rtol=1e-9)


@pytest.mark.testproblem
def test_mcwb_square_channel_problem():
    """Test that the MCWB problem initializes and evaluates correctly."""
    problem = mcwb_square_channel_problem()
    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [0.5] for var in problem.variables}
    res = evaluator.evaluate(xs)

    f1 = res["f_1"][0]
    f2 = res["f_2"][0]

    # these are the values we are getting now, are they even correct?
    assert np.isclose(f1, 27573.75)
    assert np.isclose(f2, 1.2e-6, rtol=1e-9)


@pytest.mark.testproblem
def test_mcwb_tapered_channel_problem():
    """Test that the MCWB problem initializes and evaluates correctly."""
    problem = mcwb_tapered_channel_problem()
    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [0.5] for var in problem.variables}
    res = evaluator.evaluate(xs)

    f1 = res["f_1"][0]
    f2 = res["f_2"][0]

    # these are the values we are getting now, are they even correct?
    assert np.isclose(f1, 27573.75)
    assert np.isnan(f2)


@pytest.mark.testproblem
def test_mcwb_ragsdell1976_problem():
    """Test that the MCWB problem initializes and evaluates correctly."""
    problem = mcwb_ragsdell1976_problem()
    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [0.5] for var in problem.variables}
    res = evaluator.evaluate(xs)

    f1 = res["f_1"][0]
    f2 = res["f_2"][0]

    # these are the values we are getting now, are they even correct?
    assert np.isclose(f1, 0.02511625)
    assert np.isclose(f2, 1.2e-06, rtol=1e-3, atol=1e-9)


@pytest.mark.testproblem
def test_zdt4():
    """Test that ZDT4 problem evaluates correctly."""
    n = 4
    val = [0.5, 0, 0, 0]
    problem = zdt4(n)

    evaluator = PolarsEvaluator(problem)
    xs = {f"{problem.variables[i].symbol}": [val[i]] for i in range(n)}

    res = evaluator.evaluate(xs)
    f1 = res["f_1"][0]
    f2 = res["f_2"][0]
    g = res["g"][0]
    h = res["h"][0]

    assert np.allclose(f1, 0.5)
    assert np.allclose(f2, 0.292893218)
    assert np.allclose(g, 1.0)
    assert np.allclose(h, 0.292893218)


@pytest.mark.testproblem
def test_river_pollution_problem():
    """Test that the river pollution problem initializes and evaluates correctly."""
    problem = river_pollution_problem()
    evaluator = PolarsEvaluator(problem)
    xs = {"x_1": [0.3, 0.4, 1], "x_2": [0.3, 0.5, 1]}
    expected_result = np.array(
        [
            [4.751, 2.853461, 7.5, 0, 0.35],
            [4.978, 2.893287, 7.446559, -0.182857, 0.25],
            [6.34, 3.444871, 0.321111, -9.70, 0.35],
        ]
    )

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i], rtol=1e-3, atol=1e-6)


@pytest.mark.testproblem
def test_zdt1():
    """Test that ZDT1 problem evaluates correctly."""
    n = 3
    val = 0.5
    problem = zdt1(n)

    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [val] for var in problem.variables}

    res = evaluator.evaluate(xs)
    f1 = res["f_1"][0]
    f2 = res["f_2"][0]
    g = res["g"][0]
    h = res["h"][0]

    assert np.isclose(f1, 0.5)
    assert np.isclose(f2, 3.8416876048223)
    assert np.isclose(g, 5.5)
    assert np.isclose(h, 0.6984886554222364)


@pytest.mark.testproblem
def test_binh_and_korn_problem():
    """Test that the Binh and Korn problem initializes and evaluates correctly."""
    problem = binh_and_korn()
    evaluator = PolarsEvaluator(problem)

    xs = {"x_1": [0, 2.5, 5], "x_2": [0, 1.5, 3]}
    expected_result = np.array([[0, 50], [34, 18.5], [136, 4]])

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i])


@pytest.mark.testproblem
def test_zdt2():
    """Test that ZDT2 problem evaluates correctly."""
    n = 3
    val = 0.5
    problem = zdt2(n)

    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [val] for var in problem.variables}

    res = evaluator.evaluate(xs)
    f1 = res["f_1"][0]
    f2 = res["f_2"][0]
    g = res["g"][0]
    h = res["h"][0]

    assert np.isclose(f1, 0.5)
    assert np.isclose(f2, 5.454545454545455)
    assert np.isclose(g, 5.5)
    assert np.isclose(h, 0.9917355371900827)


@pytest.mark.testproblem
def test_zdt3():
    """Test that ZDT3 problem evaluates correctly."""
    n = 2
    val = 0.5
    problem = zdt3(n)

    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [val] for var in problem.variables}

    res = evaluator.evaluate(xs)
    f1 = res["f_1"][0]
    f2 = res["f_2"][0]
    g = res["g"][0]
    h = res["h"][0]

    assert np.isclose(f1, 0.5)
    assert np.isclose(f2, 3.8416876048223)
    assert np.isclose(g, 5.5)
    assert np.isclose(h, 0.6984886554222363)


@pytest.mark.testproblem
def test_zdt6():
    """Test that ZDT6 problem evaluates correctly."""
    n = 5
    val = 0.5
    problem = zdt6(n)

    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [val] for var in problem.variables}

    res = evaluator.evaluate(xs)
    f1 = res["f_1"][0]
    f2 = res["f_2"][0]
    g = res["g"][0]

    assert np.isclose(f1, 1.0)
    assert np.isclose(f2, 8.45135530798638410874)
    assert np.isclose(g, 8.568067737283432)
