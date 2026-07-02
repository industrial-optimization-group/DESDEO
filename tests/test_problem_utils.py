"""Tests various utils found in the desdeo.problem package."""

import numpy.testing as npt
import polars as pl
import pytest

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    Problem,
    Variable,
    VariableTypeEnum,
    add_soft_constraint,
    flatten_variable_dict,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
    tensor_constant_from_dataframe,
    unflatten_variable_array,
)
from desdeo.problem.testproblems import mixed_variable_dimensions_problem, river_pollution_problem
from desdeo.problem.utils import ProblemUtilsError


@pytest.fixture
def simple_problem() -> Problem:
    """A minimal two-variable, one-objective problem for soft-constraint tests."""
    return Problem(
        name="soft constraint test problem",
        description="Used in add_soft_constraint tests",
        variables=[
            Variable(name="x1", symbol="x1", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=10),
            Variable(name="x2", symbol="x2", variable_type=VariableTypeEnum.real, lowerbound=0, upperbound=10),
        ],
        objectives=[
            Objective(name="f1", symbol="f1", func=["Add", "x1", "x2"], maximize=False),
        ],
    )


@pytest.mark.utils
def test_add_soft_constraint_lte(simple_problem):
    """A LTE soft constraint adds one slack variable and a violation objective."""
    constraint = Constraint(
        name="upper bound on x1",
        symbol="g1",
        cons_type=ConstraintTypeEnum.LTE,
        func=["Subtract", "x1", 3],
    )

    new_problem, sym = add_soft_constraint(simple_problem, constraint)

    # Return value is the violation objective symbol
    assert sym == "constraint_violation"

    # Exactly one slack variable added, with correct attributes
    new_var_symbols = [v.symbol for v in new_problem.variables]
    assert "_g1_lte_violation" in new_var_symbols
    assert "_g1_gte_violation" not in new_var_symbols
    lte_var = next(v for v in new_problem.variables if v.symbol == "_g1_lte_violation")
    assert lte_var.variable_type == VariableTypeEnum.real
    assert lte_var.lowerbound == 0
    assert lte_var.upperbound is None

    # Modified constraint subtracts the slack variable from the original func
    assert len(new_problem.constraints) == 1
    modified_con = new_problem.constraints[0]
    assert modified_con.symbol == "g1"
    assert modified_con.cons_type == ConstraintTypeEnum.LTE
    assert modified_con.func == ["Subtract", ["Subtract", "x1", 3], "_g1_lte_violation"]

    # Violation objective is created as a minimization objective
    vio_obj = next(o for o in new_problem.objectives if o.symbol == sym)
    assert vio_obj.maximize is False
    assert "_g1_lte_violation" in str(vio_obj.func)

    # Original problem is unchanged
    assert len(simple_problem.variables) == 2
    assert simple_problem.constraints is None


@pytest.mark.utils
def test_add_soft_constraint_eq(simple_problem):
    """An EQ soft constraint adds two slack variables and a violation objective."""
    constraint = Constraint(
        name="x2 fixed",
        symbol="g2",
        cons_type=ConstraintTypeEnum.EQ,
        func=["Subtract", "x2", 5],
    )

    new_problem, sym = add_soft_constraint(simple_problem, constraint)

    new_var_symbols = [v.symbol for v in new_problem.variables]
    assert "_g2_lte_violation" in new_var_symbols
    assert "_g2_gte_violation" in new_var_symbols

    for var_sym in ("_g2_lte_violation", "_g2_gte_violation"):
        var = next(v for v in new_problem.variables if v.symbol == var_sym)
        assert var.variable_type == VariableTypeEnum.real
        assert var.lowerbound == 0
        assert var.upperbound is None

    # Modified constraint: g(x) - lte + gte = 0
    modified_con = new_problem.constraints[0]
    assert modified_con.cons_type == ConstraintTypeEnum.EQ
    assert modified_con.func == [
        "Add",
        ["Subtract", ["Subtract", "x2", 5], "_g2_lte_violation"],
        "_g2_gte_violation",
    ]

    vio_obj = next(o for o in new_problem.objectives if o.symbol == sym)
    assert "_g2_lte_violation" in str(vio_obj.func)
    assert "_g2_gte_violation" in str(vio_obj.func)


@pytest.mark.utils
def test_add_soft_constraint_updates_existing_violation_objective(simple_problem):
    """A second soft constraint extends the existing violation objective's func."""
    lte_con = Constraint(name="lte con", symbol="g1", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x1", 3])
    eq_con = Constraint(name="eq con", symbol="g2", cons_type=ConstraintTypeEnum.EQ, func=["Subtract", "x2", 5])

    p2, _ = add_soft_constraint(simple_problem, lte_con)
    p3, sym = add_soft_constraint(p2, eq_con)

    # Only one violation objective should exist
    vio_objs = [o for o in p3.objectives if o.symbol == sym]
    assert len(vio_objs) == 1

    vio_func = vio_objs[0].func
    func_str = str(vio_func)
    assert "_g1_lte_violation" in func_str
    assert "_g2_lte_violation" in func_str
    assert "_g2_gte_violation" in func_str

    # Both modified constraints present
    con_symbols = [c.symbol for c in p3.constraints]
    assert "g1" in con_symbols
    assert "g2" in con_symbols


@pytest.mark.utils
def test_add_soft_constraint_custom_symbols(simple_problem):
    """Custom violation symbol names are used when provided."""
    constraint = Constraint(name="lte con", symbol="g1", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x1", 3])

    new_problem, _ = add_soft_constraint(
        simple_problem,
        constraint,
        lte_violation_symbol="my_lte_slack",
    )

    var_symbols = [v.symbol for v in new_problem.variables]
    assert "my_lte_slack" in var_symbols
    assert "_g1_lte_violation" not in var_symbols
    assert new_problem.constraints[0].func == ["Subtract", ["Subtract", "x1", 3], "my_lte_slack"]


@pytest.mark.utils
def test_add_soft_constraint_custom_violation_objective_symbol(simple_problem):
    """A custom violation objective symbol is used when provided."""
    constraint = Constraint(name="lte con", symbol="g1", cons_type=ConstraintTypeEnum.LTE, func=["Subtract", "x1", 3])

    new_problem, sym = add_soft_constraint(simple_problem, constraint, symbol="my_violation")

    assert sym == "my_violation"
    obj_symbols = [o.symbol for o in new_problem.objectives]
    assert "my_violation" in obj_symbols
    assert "constraint_violation" not in obj_symbols


@pytest.mark.utils
def test_add_soft_constraint_raises_on_none_func(simple_problem):
    """ProblemUtilsError is raised when the constraint has no func."""
    # Build a constraint without func by bypassing validation via model_construct
    bad_constraint = Constraint.model_construct(name="bad", symbol="g_bad", cons_type=ConstraintTypeEnum.LTE, func=None)

    with pytest.raises(ProblemUtilsError):
        add_soft_constraint(simple_problem, bad_constraint)


@pytest.mark.utils
def test_add_soft_constraint_raises_on_duplicate_constraint_symbol(simple_problem):
    """ProblemUtilsError is raised when a constraint with the same symbol already exists.

    Softening pre-existing constraint reuses the original constraint's symbol and appends the result, so
    allowing a duplicate symbol would produce an invalid Problem with two
    constraints named 'g1' (the original hard constraint and the softened copy).
    """
    constraint = Constraint(
        name="upper bound on x1",
        symbol="g1",
        cons_type=ConstraintTypeEnum.LTE,
        func=["Subtract", "x1", 3],
    )
    # The constraint is already part of the problem as a hard constraint.
    problem_with_hard = simple_problem.model_copy(update={"constraints": [constraint]})

    with pytest.raises(ProblemUtilsError):
        add_soft_constraint(problem_with_hard, constraint)


@pytest.mark.utils
def test_objective_dict_to_numpy_array_and_back():
    """Tests the conversion from an objective dict to a numpy array."""
    problem = river_pollution_problem()

    objective_dict = {objective.symbol: i for i, objective in enumerate(problem.objectives)}

    objective_array = objective_dict_to_numpy_array(problem, objective_dict)

    objective_dict_again = numpy_array_to_objective_dict(problem, objective_array)

    assert all(
        objective_dict[objective.symbol] == objective_dict_again[objective.symbol] for objective in problem.objectives
    )


@pytest.mark.utils
def test_flatten_unflatten_variable_dict():
    """Test that variable dictionaries are flattened correctly, and that variable array are unflattened correctly."""
    problem = mixed_variable_dimensions_problem()

    flat_values = [1.0, 1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 7, 7, 7, 7, 1, 4, 9, 4, 7, 8, 9, 7]

    var_dict = {
        "x": 1.0,
        "Y": [1, 2, 3, 4, 5],
        "Z": [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]],
        "A": [[[7, 7], [7, 7], [1, 4]], [[9, 4], [7, 8], [9, 7]]],
    }

    # flatten
    res = flatten_variable_dict(problem, var_dict)
    npt.assert_almost_equal(res, flat_values)

    # unflatten
    res_unflatten = unflatten_variable_array(problem, res)
    assert res_unflatten == var_dict

    var_dict_all_flat = {
        "x": 1.0,
        "Y_1": 1,
        "Y_2": 2,
        "Y_3": 3,
        "Y_4": 4,
        "Y_5": 5,
        "Z_1_1": 1,
        "Z_1_2": 2,
        "Z_2_1": 3,
        "Z_2_2": 4,
        "Z_3_1": 5,
        "Z_3_2": 6,
        "Z_4_1": 7,
        "Z_4_2": 8,
        "Z_5_1": 9,
        "Z_5_2": 10,
        "A_1_1_1": 7,
        "A_1_1_2": 7,
        "A_1_2_1": 7,
        "A_1_2_2": 7,
        "A_1_3_1": 1,
        "A_1_3_2": 4,
        "A_2_1_1": 9,
        "A_2_1_2": 4,
        "A_2_2_1": 7,
        "A_2_2_2": 8,
        "A_2_3_1": 9,
        "A_2_3_2": 7,
    }

    # flatten
    res_flat = flatten_variable_dict(problem, var_dict_all_flat)
    npt.assert_almost_equal(res_flat, flat_values)

    # unflatten
    res_flat_unflatten = unflatten_variable_array(problem, res_flat)
    assert res_flat_unflatten == var_dict

    var_dict_mix = {
        "x": 1.0,
        "Y": [1, 2, 3, 4, 5],
        "Z_1_1": 1,
        "Z_1_2": 2,
        "Z_2_1": 3,
        "Z_2_2": 4,
        "Z_3_1": 5,
        "Z_3_2": 6,
        "Z_4_1": 7,
        "Z_4_2": 8,
        "Z_5_1": 9,
        "Z_5_2": 10,
        "A": [[[7, 7], [7, 7], [1, 4]], [[9, 4], [7, 8], [9, 7]]],
    }

    # flatten
    res_mix = flatten_variable_dict(problem, var_dict_mix)
    npt.assert_almost_equal(res_mix, flat_values)

    # unflatten
    res_mix_unflatten = unflatten_variable_array(problem, res_mix)
    assert res_mix_unflatten == var_dict


@pytest.mark.utils
def test_tensor_constant_from_dataframe():
    """Test that a TensorConstant is created properly from a dataframe."""
    df = pl.DataFrame({"A": [1, 2, 3, 4, 5], "B": [10, 20, 30, 40, 50], "C": [100, 200, 300, 400, 500]})

    selected_columns = ["A", "C"]
    n_rows = 3

    tensor = tensor_constant_from_dataframe(df, "test", "T", n_rows, selected_columns)

    assert tensor.name == "test"
    assert tensor.symbol == "T"
    assert tensor.shape == [n_rows, len(selected_columns)]
    assert tensor.get_values() == [df["A"][0:n_rows].to_list(), df["C"][0:n_rows].to_list()]

    selected_columns = ["B", "A"]
    n_rows = 5

    tensor = tensor_constant_from_dataframe(df, "test", "T", n_rows, selected_columns)

    assert tensor.name == "test"
    assert tensor.symbol == "T"
    assert tensor.shape == [n_rows, len(selected_columns)]
    assert tensor.get_values() == [df["B"][0:n_rows].to_list(), df["A"][0:n_rows].to_list()]

    selected_columns = ["A", "B", "C"]
    n_rows = 2

    tensor = tensor_constant_from_dataframe(df, "test", "T", n_rows, selected_columns)

    assert tensor.name == "test"
    assert tensor.symbol == "T"
    assert tensor.shape == [n_rows, len(selected_columns)]
    assert tensor.get_values() == [
        df["A"][0:n_rows].to_list(),
        df["B"][0:n_rows].to_list(),
        df["C"][0:n_rows].to_list(),
    ]

    selected_columns = ["C"]
    n_rows = 3

    tensor = tensor_constant_from_dataframe(df, "test", "T", n_rows, selected_columns)

    assert tensor.name == "test"
    assert tensor.symbol == "T"
    assert tensor.shape == [n_rows, len(selected_columns)]
    assert tensor.get_values() == [
        df["C"][0:n_rows].to_list(),
    ]
