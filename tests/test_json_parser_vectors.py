"""Tests for the Extract and Exclude MathJSON operators across parser backends."""

import cvxpy as cp
import numpy as np
import numpy.testing as npt
import polars as pl
import pyomo.environ as pyomo
import pytest

from desdeo.problem.json_parser import FormatEnum, MathParser

# 5-element test vector used across backends
V = np.array([10.0, 20.0, 30.0, 40.0, 50.0])


# ── Gurobipy ─────────────────────────────────────────────────────────────────


@pytest.mark.json
@pytest.mark.gurobipy
class TestGurobipyExtract:
    """Extract with the gurobipy backend using a numpy array constant."""

    def setup_method(self):
        self.parser = MathParser(to_format=FormatEnum.gurobipy)

        def callback(name):
            if name == "v":
                return V.copy()
            raise KeyError(name)

        self.callback = callback

    def _eval(self, expr) -> np.ndarray:
        return np.array(self.parser.parse(expr, self.callback))

    def test_single_index(self):
        npt.assert_array_equal(self._eval(["Extract", "v", 2]), [20.0])

    def test_multiple_indices(self):
        npt.assert_array_equal(self._eval(["Extract", "v", 1, 4]), [10.0, 40.0])

    def test_negative_index(self):
        npt.assert_array_equal(self._eval(["Extract", "v", -1]), [50.0])

    def test_range(self):
        npt.assert_array_equal(self._eval(["Extract", "v", ["Tuple", 2, 4]]), [20.0, 30.0, 40.0])

    def test_range_with_step(self):
        npt.assert_array_equal(self._eval(["Extract", "v", ["Tuple", 1, 5, 2]]), [10.0, 30.0, 50.0])

    def test_all_indices(self):
        npt.assert_array_equal(self._eval(["Extract", "v", ["Tuple", 1, 5]]), V)


@pytest.mark.json
@pytest.mark.gurobipy
class TestGurobipyExclude:
    """Exclude with the gurobipy backend using a numpy array constant."""

    def setup_method(self):
        self.parser = MathParser(to_format=FormatEnum.gurobipy)

        def callback(name):
            if name == "v":
                return V.copy()
            raise KeyError(name)

        self.callback = callback

    def _eval(self, expr) -> np.ndarray:
        return np.array(self.parser.parse(expr, self.callback))

    def test_single_index(self):
        npt.assert_array_equal(self._eval(["Exclude", "v", 3]), [10.0, 20.0, 40.0, 50.0])

    def test_multiple_indices(self):
        npt.assert_array_equal(self._eval(["Exclude", "v", 2, 3, 5]), [10.0, 40.0])

    def test_negative_index(self):
        npt.assert_array_equal(self._eval(["Exclude", "v", -1]), [10.0, 20.0, 30.0, 40.0])

    def test_range(self):
        npt.assert_array_equal(self._eval(["Exclude", "v", ["Tuple", 2, 4]]), [10.0, 50.0])

    def test_range_with_step(self):
        # Exclude odd-positioned elements (1, 3, 5) → keep 2nd and 4th
        npt.assert_array_equal(self._eval(["Exclude", "v", ["Tuple", 1, 5, 2]]), [20.0, 40.0])


# ── Polars ────────────────────────────────────────────────────────────────────


@pytest.mark.json
@pytest.mark.polars
class TestPolarsExtract:
    """Extract with the Polars backend — two-row DataFrame, each row a 5-element vector."""

    def setup_method(self):
        arr = np.array([V, V * 0.1])  # row 0: [10,20,30,40,50], row 1: [1,2,3,4,5]
        self.data = pl.DataFrame({"v": arr})
        self.parser = MathParser(to_format=FormatEnum.polars)

    def _eval(self, expr) -> np.ndarray:
        return np.array(self.data.select(self.parser.parse(expr)).to_series().to_list())

    def test_single_index(self):
        npt.assert_allclose(self._eval(["Extract", "v", 2]), [[20.0], [2.0]])

    def test_multiple_indices(self):
        npt.assert_allclose(self._eval(["Extract", "v", 1, 4]), [[10.0, 40.0], [1.0, 4.0]])

    def test_negative_index(self):
        npt.assert_allclose(self._eval(["Extract", "v", -1]), [[50.0], [5.0]])

    def test_range(self):
        npt.assert_allclose(self._eval(["Extract", "v", ["Tuple", 2, 4]]), [[20.0, 30.0, 40.0], [2.0, 3.0, 4.0]])

    def test_range_with_step(self):
        npt.assert_allclose(self._eval(["Extract", "v", ["Tuple", 1, 5, 2]]), [[10.0, 30.0, 50.0], [1.0, 3.0, 5.0]])

    def test_all_indices(self):
        npt.assert_allclose(self._eval(["Extract", "v", ["Tuple", 1, 5]]), [V, V * 0.1])


@pytest.mark.json
@pytest.mark.polars
class TestPolarsExclude:
    """Exclude with the Polars backend — two-row DataFrame, each row a 5-element vector."""

    def setup_method(self):
        arr = np.array([V, V * 0.1])
        self.data = pl.DataFrame({"v": arr})
        self.parser = MathParser(to_format=FormatEnum.polars)

    def _eval(self, expr) -> np.ndarray:
        return np.array(self.data.select(self.parser.parse(expr)).to_series().to_list())

    def test_single_index(self):
        npt.assert_allclose(self._eval(["Exclude", "v", 3]), [[10.0, 20.0, 40.0, 50.0], [1.0, 2.0, 4.0, 5.0]])

    def test_multiple_indices(self):
        npt.assert_allclose(self._eval(["Exclude", "v", 2, 3, 5]), [[10.0, 40.0], [1.0, 4.0]])

    def test_negative_index(self):
        npt.assert_allclose(self._eval(["Exclude", "v", -1]), [[10.0, 20.0, 30.0, 40.0], [1.0, 2.0, 3.0, 4.0]])

    def test_range(self):
        npt.assert_allclose(self._eval(["Exclude", "v", ["Tuple", 2, 4]]), [[10.0, 50.0], [1.0, 5.0]])

    def test_range_with_step(self):
        npt.assert_allclose(self._eval(["Exclude", "v", ["Tuple", 1, 5, 2]]), [[20.0, 40.0], [2.0, 4.0]])


# ── CVXPY ─────────────────────────────────────────────────────────────────────


@pytest.mark.json
@pytest.mark.cvxpy
class TestCvxpyExtract:
    """Extract with the CVXPY backend."""

    def setup_method(self):
        self.x = cp.Variable(5, name="x")
        self.parser = MathParser(to_format=FormatEnum.cvxpy)

        def callback(name):
            if name == "x":
                return self.x
            raise KeyError(name)

        self.callback = callback

    def test_shape_single(self):
        result = self.parser.parse(["Extract", "x", 2], self.callback)
        assert result.shape == (1,)

    def test_shape_multiple(self):
        result = self.parser.parse(["Extract", "x", 1, 4], self.callback)
        assert result.shape == (2,)

    def test_shape_range(self):
        result = self.parser.parse(["Extract", "x", ["Tuple", 2, 4]], self.callback)
        assert result.shape == (3,)

    def test_solve(self):
        """Extracted elements can be pinned in constraints and solved."""
        sub = self.parser.parse(["Extract", "x", 1, 3], self.callback)
        prob = cp.Problem(cp.Minimize(cp.sum(self.x)), [sub == np.array([5.0, 7.0]), self.x >= 0])
        prob.solve()
        assert prob.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]
        npt.assert_allclose(self.x.value[0], 5.0, atol=1e-4)
        npt.assert_allclose(self.x.value[2], 7.0, atol=1e-4)


@pytest.mark.json
@pytest.mark.cvxpy
class TestCvxpyExclude:
    """Exclude with the CVXPY backend."""

    def setup_method(self):
        self.x = cp.Variable(5, name="x")
        self.parser = MathParser(to_format=FormatEnum.cvxpy)

        def callback(name):
            if name == "x":
                return self.x
            raise KeyError(name)

        self.callback = callback

    def test_shape_single(self):
        result = self.parser.parse(["Exclude", "x", 3], self.callback)
        assert result.shape == (4,)

    def test_shape_multiple(self):
        result = self.parser.parse(["Exclude", "x", 2, 3, 5], self.callback)
        assert result.shape == (2,)

    def test_shape_range(self):
        result = self.parser.parse(["Exclude", "x", ["Tuple", 2, 4]], self.callback)
        assert result.shape == (2,)

    def test_solve(self):
        """Elements outside the excluded index can be constrained and solved."""
        sub = self.parser.parse(["Exclude", "x", 3], self.callback)
        prob = cp.Problem(cp.Minimize(cp.sum(self.x)), [sub >= 10.0, self.x >= 0])
        prob.solve()
        assert prob.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]
        for i in [0, 1, 3, 4]:
            assert self.x.value[i] >= 10.0 - 1e-4, f"x[{i}] = {self.x.value[i]} < 10"


# ── Pyomo ─────────────────────────────────────────────────────────────────────


@pytest.mark.json
@pytest.mark.pyomo
class TestPyomoExtract:
    """Extract with the Pyomo backend — 1-based indexed Var of length 5."""

    def setup_method(self):
        self.model = pyomo.ConcreteModel()
        self.model.x = pyomo.Var(pyomo.RangeSet(1, 5), domain=pyomo.Reals, initialize=lambda _, i: float(i * 10))
        self.parser = MathParser(to_format=FormatEnum.pyomo)

    def _eval(self, expr) -> list[float]:
        result = self.parser.parse(expr, self.model)
        return [pyomo.value(result[i]) for i in result.index_set()]

    def test_single_index(self):
        assert self._eval(["Extract", "x", 2]) == pytest.approx([20.0])

    def test_multiple_indices(self):
        assert self._eval(["Extract", "x", 1, 4]) == pytest.approx([10.0, 40.0])

    def test_negative_index(self):
        assert self._eval(["Extract", "x", -1]) == pytest.approx([50.0])

    def test_range(self):
        assert self._eval(["Extract", "x", ["Tuple", 2, 4]]) == pytest.approx([20.0, 30.0, 40.0])

    def test_range_with_step(self):
        assert self._eval(["Extract", "x", ["Tuple", 1, 5, 2]]) == pytest.approx([10.0, 30.0, 50.0])

    def test_all_indices(self):
        assert self._eval(["Extract", "x", ["Tuple", 1, 5]]) == pytest.approx([10.0, 20.0, 30.0, 40.0, 50.0])


@pytest.mark.json
@pytest.mark.pyomo
class TestPyomoExclude:
    """Exclude with the Pyomo backend — 1-based indexed Var of length 5."""

    def setup_method(self):
        self.model = pyomo.ConcreteModel()
        self.model.x = pyomo.Var(pyomo.RangeSet(1, 5), domain=pyomo.Reals, initialize=lambda _, i: float(i * 10))
        self.parser = MathParser(to_format=FormatEnum.pyomo)

    def _eval(self, expr) -> list[float]:
        result = self.parser.parse(expr, self.model)
        return [pyomo.value(result[i]) for i in result.index_set()]

    def test_single_index(self):
        assert self._eval(["Exclude", "x", 3]) == pytest.approx([10.0, 20.0, 40.0, 50.0])

    def test_multiple_indices(self):
        assert self._eval(["Exclude", "x", 2, 3, 5]) == pytest.approx([10.0, 40.0])

    def test_negative_index(self):
        assert self._eval(["Exclude", "x", -1]) == pytest.approx([10.0, 20.0, 30.0, 40.0])

    def test_range(self):
        assert self._eval(["Exclude", "x", ["Tuple", 2, 4]]) == pytest.approx([10.0, 50.0])

    def test_range_with_step(self):
        assert self._eval(["Exclude", "x", ["Tuple", 1, 5, 2]]) == pytest.approx([20.0, 40.0])


# ── NotImplementedError for Sympy ─────────────────────────────────────────────


@pytest.mark.json
@pytest.mark.sympy
def test_extract_not_implemented_sympy():
    parser = MathParser(to_format=FormatEnum.sympy)
    with pytest.raises(NotImplementedError):
        parser.parse(["Extract", "v", 1])


@pytest.mark.json
@pytest.mark.sympy
def test_exclude_not_implemented_sympy():
    parser = MathParser(to_format=FormatEnum.sympy)
    with pytest.raises(NotImplementedError):
        parser.parse(["Exclude", "v", 1])
