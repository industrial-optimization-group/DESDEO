"""Test some of the test problems found in DESDEO."""

import joblib
import numpy as np
import numpy.testing as npt
import pytest

from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import PolarsEvaluator, PyomoEvaluator, SimulatorEvaluator
from desdeo.problem.testproblems import (
    binh_and_korn,
    car_side_impact,
    ctp1,
    ctp2,
    ctp3,
    ctp4,
    ctp5,
    ctp6,
    ctp7,
    ctp8,
    dtlz1,
    dtlz2,
    dtlz4,
    forest_problem,
    gaa,
    lame_superspheres,
    mcwb_equilateral_tbeam_problem,
    mcwb_hollow_rectangular_problem,
    mcwb_ragsdell1976_problem,
    mcwb_solid_rectangular_problem,
    mcwb_square_channel_problem,
    mcwb_tapered_channel_problem,
    metallurgical_application,
    re21,
    re22,
    re23,
    re24,
    re31,
    re32,
    re33,
    re42,
    river_pollution_problem,
    river_pollution_scenario,
    spanish_sustainability_problem,
    water_management,
    zdt1,
    zdt2,
    zdt3,
    zdt4,
    zdt6,
)
from desdeo.problem.testproblems import metallurgical_application_problem as metall
from desdeo.tools import GurobipySolver, payoff_table_method


@pytest.mark.testproblem
def test_dtlz1():
    """Test that the DTLZ1 problem initializes and evaluates correcly."""
    test_variables = [3, 5, 10, 50]
    test_objectives = [2, 4, 5, 7]

    for n_variables, n_objectives in zip(test_variables, test_objectives, strict=True):
        problem = dtlz1(n_variables, n_objectives)

        assert len(problem.variables) == n_variables
        assert len(problem.objectives) == n_objectives

        xs = {f"{var.symbol}": [0.5] for var in problem.variables}

        evaluator = PolarsEvaluator(problem)

        res = evaluator.evaluate(xs)

        assert np.isclose(sum(res[obj.symbol][0] for obj in problem.objectives), 0.5)


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


def _assert_re_problem(problem, n_variables: int, n_objectives: int, xs: dict, expected: np.ndarray):
    """Assert the shape and the evaluated objective values of a bound-constrained RE problem.

    The RE problems fold their original constraints into the last objective, so a correct
    implementation carries no constraints at all -- that is asserted here rather than left implicit,
    because a stray constraint would silently change which selection path an EMO run takes.

    The expected values were produced by transcribing the equations of the suite's supplementary file
    into numpy independently of the DESDEO expressions, so this catches a typo in either one. Several
    of the rows additionally coincide with the components of the ideal and nadir points published with
    the suite, which is noted at each call site; those rows check the transcription itself, not just
    its restatement.
    """
    assert len(problem.variables) == n_variables
    assert len(problem.objectives) == n_objectives
    assert problem.constraints is None

    res = PolarsEvaluator(problem).evaluate(xs)
    for i in range(len(res)):
        objective_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        npt.assert_allclose(objective_values, expected[i], rtol=1e-10)


@pytest.mark.testproblem
def test_re31():
    """Test that the two bar truss design problem evaluates correctly."""
    # Row 0 is the corner attaining the published ideal f_1 (5.53731918799e-05) and the published
    # nadir f_2 (8246211.25124) and f_3 (19359919.7502); row 2 attains the published ideal f_2 (1/3).
    _assert_re_problem(
        re31(),
        n_variables=3,
        n_objectives=3,
        xs={"x_1": [1e-5, 50.0, 100.0], "x_2": [1e-5, 50.0, 0.5], "x_3": [1.0, 2.0, 3.0]},
        expected=np.array(
            [
                [5.537319187991e-05, 8.246211251235e06, 1.935991975022e07],
                [3.354101966250e02, 8.944271909999e-01, 3.353101966250e02],
                [5.015811388301e02, 3.333333333333e-01, 5.014811388301e02],
            ]
        ),
    )


@pytest.mark.testproblem
def test_re32():
    """Test that the welded beam design problem evaluates correctly."""
    # Row 0 is the corner attaining the published ideal f_1 (0.010205496875) and the published nadir
    # f_2 (17561.6) and f_3 (425062976.628); row 2 attains the published ideal f_2 (0.00043904).
    _assert_re_problem(
        re32(),
        n_variables=4,
        n_objectives=3,
        xs={
            "x_1": [0.125, 1.0, 5.0],
            "x_2": [0.1, 5.0, 10.0],
            "x_3": [0.1, 5.0, 10.0],
            "x_4": [0.125, 1.0, 5.0],
        },
        expected=np.array(
            [
                [1.020549687500e-02, 1.756160000000e04, 4.250629766275e08],
                [1.009400000000e01, 1.756160000000e-02, 0.0],
                [3.339095000000e02, 4.390400000000e-04, 0.0],
            ]
        ),
    )


@pytest.mark.testproblem
def test_re33():
    """Test that the disc brake design problem evaluates correctly."""
    # Row 0 is the corner attaining the published ideal f_1 (-0.721525) and the published nadir
    # f_3 (25.0). Note that it has x_2 < x_1, an inverted disc that only the violation objective
    # penalises -- the RE bounds allow it, so it must evaluate rather than raise.
    _assert_re_problem(
        re33(),
        n_variables=4,
        n_objectives=3,
        xs={
            "x_1": [80.0, 60.0, 55.0],
            "x_2": [75.0, 90.0, 110.0],
            "x_3": [1000.0, 2000.0, 3000.0],
            "x_4": [20.0, 15.0, 11.0],
        },
        expected=np.array(
            [
                [-0.721525, 4.222191400832, 25.0],
                [3.087, 2.871345029240, 0.0],
                [4.44675, 2.318772136954, 0.0],
            ]
        ),
    )


@pytest.mark.testproblem
def test_re42():
    """Test that the conceptual marine design problem evaluates correctly."""
    # Row 1 is the lower corner of the box, and it attains three published extreme values at once:
    # the nadir f_1 (-1010.5229595) and f_3 (2611.9668107), and the ideal f_2 (3962.5578432). Those
    # come from the suite's approximated front, so they agree with an exact evaluation of the corner
    # to about eight significant figures rather than exactly.
    _assert_re_problem(
        re42(),
        n_variables=6,
        n_objectives=4,
        xs={
            "x_1": [212.16, 150.0, 274.32],
            "x_2": [26.155, 20.0, 32.31],
            "x_3": [19.0, 13.0, 25.0],
            "x_4": [10.855, 10.0, 11.71],
            "x_5": [16.0, 14.0, 18.0],
            "x_6": [0.69, 0.63, 0.75],
        },
        expected=np.array(
            [
                [-5.691666596609e02, 9.869900828051e03, 9.182958350611e03, 2.328562286631e00],
                [-1.010522955311e03, 3.962557772617e03, 2.611966792840e03, 1.845063160099e00],
                [-3.789122000992e02, 2.002660694716e04, 2.577957489282e04, 7.141587967549e00],
            ]
        ),
    )


@pytest.mark.testproblem
def test_re42_matches_the_published_extreme_points():
    """The RE42 sea-days equation is easy to "fix" into a different problem, so pin it down.

    The suite defines the number of sea days as (round trip miles / 24) * speed. Dividing by the speed
    instead is the dimensionally sensible reading and gives an f_3 that is wrong by a factor of about
    400, which no unit test on a single evaluation would obviously catch. The lower corner of the box
    happens to sit on three components of the published ideal and nadir points at once, so comparing
    against them detects the substitution directly.
    """
    problem = re42()
    corner = {var.symbol: [var.lowerbound] for var in problem.variables}

    res = PolarsEvaluator(problem).evaluate(corner)
    values = np.array([res[obj.symbol][0] for obj in problem.objectives])

    published_nadir_f1 = -1010.5229595219643
    published_ideal_f2 = 3962.557843228888
    published_nadir_f3 = 2611.9668107424536
    npt.assert_allclose(values[[0, 1, 2]], [published_nadir_f1, published_ideal_f2, published_nadir_f3], rtol=1e-7)


# The corners of the GAA design box, with the ten objective values and the constraint value that the
# MOEA Framework's own GAATest asserts for them. Every aircraft in the family sits at the same corner,
# which is why the product family penalty function is zero (to rounding) in the first case.
_GAA_LOWER_CORNER = [0.24, 7.0, 0.0, 5.5, 19.0, 85.0, 14.0, 3.0, 0.46] * 3
_GAA_UPPER_CORNER = [0.48, 11.0, 6.0, 5.968, 25.0, 110.0, 20.0, 3.75, 1.0] * 3
_GAA_EXPECTED = np.array(
    [
        [
            73.239998, 1880.3199970000003, 62.38500200000003, 2.1867999999999994, 480.173996,
            41699.24730800003, 3032.0586889999995, 15.726500000000003, 189.25630300000014,
            1.9229626863835638e-16,
        ],
        [
            75.19549799999994, 2097.8436029999993, 95.00900000000001, 2.078, 291.2477919999998,
            47369.88729400002, 891.8127029999995, 17.929600000000004, 198.903706, 0.0,
        ],
    ]
)  # fmt: skip
_GAA_EXPECTED_VIOLATION = np.array([0.33805332444444436, 2.3017063231666643])


@pytest.mark.testproblem
def test_gaa():
    """Test that the general aviation aircraft problem reproduces its reference implementation.

    The response surfaces are 27 fitted polynomials with about fifty coefficients each, so a
    transcription error would be easy to make and invisible in the objective values on their own. The
    two corners below are the ones the reference implementation's own test pins, which checks all 1424
    non-zero coefficients at once against a source outside this repository.
    """
    problem = gaa()

    assert len(problem.variables) == 27
    assert len(problem.objectives) == 10
    assert len(problem.constraints) == 1
    # Range, maximum lift-to-drag and maximum cruise speed are maximised; the other seven are not.
    assert [objective.maximize for objective in problem.objectives] == [False] * 6 + [True] * 3 + [False]

    xs = {f"x_{i + 1}": [_GAA_LOWER_CORNER[i], _GAA_UPPER_CORNER[i]] for i in range(27)}
    res = PolarsEvaluator(problem).evaluate(xs)

    for row in range(2):
        objective_values = np.array([res[obj.symbol][row] for obj in problem.objectives])
        npt.assert_allclose(objective_values, _GAA_EXPECTED[row], rtol=1e-12, atol=1e-15)
        npt.assert_allclose(res["g_1"][row], _GAA_EXPECTED_VIOLATION[row], rtol=1e-12)


@pytest.mark.testproblem
def test_gaa_folded_constraint():
    """The folded variant must move the violation into an eleventh objective and drop the constraint.

    This is the form the RE suite uses, and the form an unconstrained study needs, so the two have to
    agree on the value -- otherwise the constrained and bound-constrained runs are different problems.
    """
    folded = gaa(fold_constraint=True)

    assert len(folded.objectives) == 11
    assert folded.constraints is None

    xs = {f"x_{i + 1}": [_GAA_LOWER_CORNER[i], _GAA_UPPER_CORNER[i]] for i in range(27)}
    res = PolarsEvaluator(folded).evaluate(xs)

    npt.assert_allclose([res["f_11"][0], res["f_11"][1]], _GAA_EXPECTED_VIOLATION, rtol=1e-12)
    for row in range(2):
        npt.assert_allclose(
            np.array([res[f"f_{i}"][row] for i in range(1, 11)]), _GAA_EXPECTED[row], rtol=1e-12, atol=1e-15
        )


@pytest.fixture(scope="module")
def metall_cache(tmp_path_factory):
    """A scratch cache for the metallurgical problem, so the tests never touch the user's real one.

    Module scoped because the surrogates are trained on first use; sharing the directory means they
    are trained once for the whole file rather than once per test.
    """
    return tmp_path_factory.mktemp("metall_cache")


@pytest.mark.testproblem
@pytest.mark.simulator_support
def test_metallurgical_application(metall_cache):
    """Test that the microalloyed steel design problem builds and evaluates."""
    problem = metallurgical_application(cache_dir=metall_cache)

    assert len(problem.variables) == 17
    # The default is the paper's MOP-II, which is MOP-I without the Charpy objective.
    assert [objective.symbol for objective in problem.objectives] == list(metall.MOP_II)
    # The measured properties are maximised; the carbon equivalent and the cost are minimised.
    assert [objective.maximize for objective in problem.objectives] == [True, True, True, False, False]
    assert all(variable.lowerbound < variable.upperbound for variable in problem.variables)

    xs = {variable.symbol: [variable.lowerbound, variable.upperbound] for variable in problem.variables}
    res = SimulatorEvaluator(problem).evaluate(xs)

    values = np.array([[res[objective.symbol][row] for objective in problem.objectives] for row in range(2)])
    assert np.isfinite(values).all()

    # Both analytical objectives can be checked exactly, at the upper bound of every element.
    upper = {variable.symbol: variable.upperbound for variable in problem.variables}
    # Equation (2) of the paper. The silicon term is the one the how-to guide leaves out.
    expected_ce = (
        upper["C"]
        + (upper["Mn"] + upper["Si"]) / 6
        + (upper["Cr"] + upper["Mo"] + upper["V"]) / 5
        + (upper["Cu"] + upper["Ni"]) / 15
    )
    npt.assert_allclose(res["CE"][1], expected_ce)

    expected_cost = sum(cost * upper[element] for element, cost in metall._ELEMENT_COSTS.items())
    npt.assert_allclose(res["COST"][1], expected_cost)


@pytest.mark.testproblem
@pytest.mark.simulator_support
def test_metallurgical_application_objective_subsets(metall_cache):
    """Any subset of the objectives can be requested, and the box follows the datasets that are used.

    The paper derives the bounds from "the intersection of the datasets used for all four surrogate
    models", so dropping a property widens the box. That is exactly the difference between its MOP-I
    and MOP-II, and it means the subsets are different problems rather than the same problem with
    fewer objectives.
    """
    for subset in (["CE"], ["YS", "CE"], ["ELON", "UTS"], ["COST", "CHARPY"], list(metall.MOP_I)):
        problem = metallurgical_application(subset, cache_dir=metall_cache)
        # The order asked for is the order given back.
        assert [objective.symbol for objective in problem.objectives] == subset
        assert len(problem.variables) == 17

    mop_i = metallurgical_application(metall.MOP_I, cache_dir=metall_cache)
    mop_ii = metallurgical_application(metall.MOP_II, cache_dir=metall_cache)

    # Dropping Charpy widens the box, and never narrows it: MOP-I's box sits inside MOP-II's.
    for narrow, wide in zip(mop_i.variables, mop_ii.variables, strict=True):
        assert narrow.symbol == wide.symbol
        assert wide.lowerbound <= narrow.lowerbound
        assert narrow.upperbound <= wide.upperbound
    # And it is strictly wider somewhere, or the two formulations would be the same problem.
    assert any(
        narrow.upperbound < wide.upperbound or wide.lowerbound < narrow.lowerbound
        for narrow, wide in zip(mop_i.variables, mop_ii.variables, strict=True)
    )

    with pytest.raises(ValueError, match="At least one objective"):
        metallurgical_application([], cache_dir=metall_cache)

    with pytest.raises(ValueError, match="Unknown objective"):
        metallurgical_application(["YS", "TOUGHNESS"], cache_dir=metall_cache)

    with pytest.raises(ValueError, match="repeats an objective"):
        metallurgical_application(["YS", "YS"], cache_dir=metall_cache)


@pytest.mark.testproblem
@pytest.mark.simulator_support
def test_metallurgical_application_matches_the_papers_model_choices(metall_cache):
    """Pin the regressors and the excluded elements to the tables of the paper.

    Table 1 gives the regressor chosen for each property by cross-validation, and Table 2 the
    elements it found no effect for, which "were not considered for the model". Neither is visible in
    the objective values, so a wrong choice here would go unnoticed: the Charpy energy in particular
    scores a median cross-validated R^2 of 0.44 with gradient boosting and 0.17 with extra trees, and
    both produce a problem that evaluates perfectly happily.
    """
    assert {target: spec.regressor for target, spec in metall._SURROGATE_SPEC.items()} == {
        "YS": "ExtraTreesRegressor",
        # The paper picks XGBoost here, by 0.8440 against 0.8437; see the note in the docstring.
        "UTS": "GradientBoostingRegressor",
        "ELON": "ExtraTreesRegressor",
        "CHARPY": "GradientBoostingRegressor",
    }
    assert {target: spec.excluded for target, spec in metall._SURROGATE_SPEC.items()} == {
        "YS": ("N", "B"),
        "UTS": ("N", "B"),
        "ELON": ("Ce",),
        "CHARPY": ("Si", "B", "Ce", "Cu", "Zr"),
    }
    assert metall._SURROGATE_SPEC["CHARPY"].needs_temperature
    assert metall.DEFAULT_CHARPY_TEMPERATURE == -80.0

    # The wrapper must hand each model exactly the columns it was fitted on, in _ELEMENTS order.
    problem = metallurgical_application(["CHARPY"], cache_dir=metall_cache)
    wrapper = joblib.load(problem.objectives[0].surrogates[0])
    assert [metall._ELEMENTS[i] for i in wrapper.indices] == list(metall._SURROGATE_SPEC["CHARPY"].inputs())
    assert wrapper.temperature == metall.DEFAULT_CHARPY_TEMPERATURE


@pytest.mark.testproblem
@pytest.mark.simulator_support
def test_metallurgical_application_surrogate_columns_are_aligned(metall_cache):
    """The surrogates must receive the elements in the order they were trained on.

    The surrogate evaluator builds each model's input from the decision variable dictionary in
    insertion order and never looks at column names, so a mismatch between the declared variable
    order and the training column order is silent: the problem still evaluates, and every value is
    wrong. Predicting each model's own training data catches it, since a scrambled composition
    destroys the fit. Charpy is left out because the problem pins one test temperature while its data
    was measured across a range of them.
    """
    problem = metallurgical_application(["YS", "UTS", "ELON"], cache_dir=metall_cache)
    evaluator = SimulatorEvaluator(problem)

    def unexplained_variance(target: str, order) -> float:
        data = metall._read_dataset(target, None, metall_cache, download=False)
        predicted = evaluator.evaluate({element: data[element].to_list() for element in order})[target].to_numpy()
        measured = data[target].to_numpy()
        return float(np.sum((measured - predicted) ** 2) / np.sum((measured - measured.mean()) ** 2))

    for target in ("YS", "UTS", "ELON"):
        r_squared = 1 - unexplained_variance(target, metall._ELEMENTS)
        # An R^2 of 1 is unreachable: the data holds repeated compositions with different measured
        # values, because the same alloy behaves differently after different processing.
        assert r_squared > 0.85, f"{target} fits its own training data poorly: R2 = {r_squared}"

    # The same check with the elements reversed must fail badly, or it is not testing anything.
    assert 1 - unexplained_variance("YS", tuple(reversed(metall._ELEMENTS))) < 0.5


@pytest.mark.testproblem
@pytest.mark.simulator_support
def test_metallurgical_application_charpy(metall_cache):
    """The Charpy objective is optional, and its test temperature is a parameter of the problem."""
    assert "CHARPY" not in metallurgical_application(cache_dir=metall_cache).objectives[0].symbol
    assert "CHARPY" not in metall.MOP_II
    assert "CHARPY" in metall.MOP_I

    problem = metallurgical_application(metall.MOP_I, cache_dir=metall_cache)
    charpy = next(objective for objective in problem.objectives if objective.symbol == "CHARPY")
    assert charpy.maximize

    midpoint = {v.symbol: [(v.lowerbound + v.upperbound) / 2] for v in problem.variables}

    def energy_at(temperature: float) -> float:
        at = metallurgical_application(["CHARPY"], charpy_temperature=temperature, cache_dir=metall_cache)
        # The box of a Charpy-only problem is the Charpy dataset's own range, so evaluate the
        # midpoint of the six-objective problem, which lies inside it.
        return SimulatorEvaluator(at).evaluate(midpoint)["CHARPY"][0]

    warm, cold = energy_at(20.0), energy_at(-120.0)
    assert np.isfinite(warm) and np.isfinite(cold)
    # Steel absorbs less energy before fracturing when it is cold: the ductile-to-brittle transition,
    # which the paper describes as the Charpy energy decreasing "at lower temperatures as ductile
    # materials (such as steels) start showing brittle behaviour". It is the one property of the
    # fitted model that physics pins down, so it is worth asserting.
    assert warm > cold


@pytest.mark.testproblem
@pytest.mark.simulator_support
def test_metallurgical_application_finds_data_without_downloading(metall_cache, monkeypatch, tmp_path):
    """The datasets are found in the repository checkout, and only fetched when they are nowhere.

    The first half must hold for the tests to run offline at all. The second half checks that a
    missing dataset is reported clearly rather than silently downloaded when `download` is False.
    """
    assert metall._repository_data_dir() is not None
    metallurgical_application(["CE"], cache_dir=metall_cache, download=False)

    # With no repository and an empty cache there is nothing left to find.
    monkeypatch.setattr(metall, "_repository_data_dir", lambda: None)
    with pytest.raises(FileNotFoundError, match="not found locally"):
        metallurgical_application(["CE"], cache_dir=tmp_path / "empty", download=False)


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


@pytest.mark.testproblem
def test_water_management():
    """Test that water management problem evaluates correctly."""
    problem = water_management()
    evaluator = PolarsEvaluator(problem)

    # Representative solutions from Table III of Ray, Tai & Seow (2001). The table values are
    # rounded to 5-6 significant figures, so a loose relative tolerance is used. The table also
    # contains scattered obvious factor of 10 typos in the f_3 and f_4 columns. These entries have been
    # multiplied by 10 here to match the published formulae (see this row's f_3/f_4 noted below).
    expected_result = np.array(
        [
            [75550.6, 393.59, 2688570, 297434, 5188.67],  # f_3 x10
            [66203.1, 1099.03, 797974, 3354890, 3141.07],  # f_4 x10
            [66465.1, 1333.30, 474106, 6039030, 6159.86],  # f_4 x10
            [70633.7, 1349.74, 1960570, 669173, 965.80],  # f_3 x10
        ]
    )

    xs = {
        "x_1": [0.1312, 0.3663, 0.4444, 0.4499],
        "x_2": [0.0942, 0.0280, 0.0166, 0.0687],
        "x_3": [0.0354, 0.0142, 0.0280, 0.0149],
    }

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i], rtol=2e-2)


@pytest.mark.testproblem
def test_car_side_impact():
    """Test that car side impact problem evaluates correctly."""
    a = False

    problem = car_side_impact(a)
    evaluator = PolarsEvaluator(problem)

    xs = {
        "x_1": [0.5, 1.0, 1.5],
        "x_2": [0.45, 0.95, 1.35],
        "x_3": [0.5, 1.0, 1.5],
        "x_4": [0.5, 1.0, 1.5],
        "x_5": [0.875, 1.75, 2.625],
        "x_6": [0.4, 0.8, 1.2],
        "x_7": [0.4, 0.8, 1.2],
    }

    expected_result = np.array(
        [
            [15.576004, 4.42725, 13.091381250000001, 9.4940193],
            [29.505508, 4.0395, 12.08959375, 0.5440],
            [42.768012, 3.58525, 10.61064375, 0.0],
        ]
    )

    res = evaluator.evaluate(xs)

    for i in range(len(res)):
        obj_values = np.array([res[obj.symbol][i] for obj in problem.objectives])
        assert np.allclose(obj_values, expected_result[i])


@pytest.mark.testproblem
def test_ctp1():
    """Test that CTP1 problem evaluates correctly."""
    n = 3
    val = 0.5
    problem = ctp1(n)

    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [val] for var in problem.variables}

    res = evaluator.evaluate(xs)
    f1 = res["f_1"][0]
    f2 = res["f_2"][0]
    g1 = res["g_1"][0]
    g2 = res["g_2"][0]

    assert np.isclose(f1, 0.5)
    assert np.isclose(f2, 5.108953223270181)
    assert np.isclose(g1, -4.454301025073424)
    assert np.isclose(g2, -4.4807893681722195)


@pytest.mark.testproblem
@pytest.mark.parametrize(
    ("problem_func", "expected_f2", "expected_constraints"),
    [
        (ctp2, 5.0, (-3.3365765309197597,)),
        (ctp3, 5.0, (-3.430240537273866,)),
        (ctp4, 5.0, (-2.7820601058548213,)),
        (ctp5, 5.0, (-3.472729748823802,)),
        (ctp6, 5.0, (21.935713778922732,)),
        (ctp7, 5.0, (31.125778196131336,)),
        (ctp8, 5.0, (21.935713778922732, 28.53828532201262)),
    ],
)
def test_ctp2_to_ctp8(problem_func, expected_f2, expected_constraints):
    """Test that the generated CTP2-CTP8 problems evaluate correctly."""
    n = 3
    val = 0.5
    problem = problem_func(n)

    # CTP8 has two constraints, the rest have one
    assert len(problem.constraints) == len(expected_constraints)

    evaluator = PolarsEvaluator(problem)
    xs = {f"{var.symbol}": [val] for var in problem.variables}

    res = evaluator.evaluate(xs)

    assert np.isclose(res["f_1"][0], val)
    assert np.isclose(res["f_2"][0], expected_f2)
    for idx, expected in enumerate(expected_constraints, start=1):
        assert np.isclose(res[f"g_{idx}"][0], expected)
