"""Tests related to tensor constants and variables."""

import numpy as np

from desdeo.problem import (
    TensorConstant,
    TensorVariable,
    VariableTypeEnum,
    simple_knapsack_vectors,
)


def test_tensor_variable_init():
    """Tests that tensor variables are created and represented correctly in the MathJSON format."""
    # Test 1D
    xs = TensorVariable(
        name="A",
        symbol="A",
        variable_type="integer",
        shape=[3],
        lowerbounds=[1, 2, 3],
        upperbounds=[10, 20, 30],
        initial_values=[1, 1, 1],
    )

    assert xs.name == "A"
    assert xs.symbol == "A"
    assert xs.shape[0] == 3
    assert xs.lowerbounds == ["List", 1, 2, 3]
    assert xs.upperbounds == ["List", 10, 20, 30]
    assert xs.initial_values == ["List", 1, 1, 1]

    # Test 2D
    xs = TensorVariable(
        name="X",
        symbol="X",
        variable_type="integer",
        shape=[2, 3],
        lowerbounds=[[1, 2, 3], [4, 5, 6]],
        upperbounds=[[10, 20, 30], [40, 50, 60]],
        initial_values=[[1, 1, 1], [2, 2, 2]],
    )

    assert xs.name == "X"
    assert xs.symbol == "X"
    assert xs.shape[0] == 2
    assert xs.shape[1] == 3
    assert xs.lowerbounds == ["List", ["List", 1, 2, 3], ["List", 4, 5, 6]]
    assert xs.upperbounds == ["List", ["List", 10, 20, 30], ["List", 40, 50, 60]]
    assert xs.initial_values == ["List", ["List", 1, 1, 1], ["List", 2, 2, 2]]

    # Test 3D
    xs = TensorVariable(
        name="B",
        symbol="B",
        variable_type="integer",
        shape=[2, 3, 4],
        lowerbounds=[
            [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],
            [[13, 14, 15, 16], [17, 18, 19, 20], [21, 22, 23, 24]],
        ],
        upperbounds=[
            [[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]],
            [[130, 140, 150, 160], [170, 180, 190, 200], [210, 220, 230, 240]],
        ],
        initial_values=[[[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3]], [[4, 4, 4, 4], [5, 5, 5, 5], [6, 6, 6, 6]]],
    )

    assert xs.name == "B"
    assert xs.symbol == "B"
    assert xs.shape[0] == 2
    assert xs.shape[1] == 3
    assert xs.shape[2] == 4
    assert xs.lowerbounds == [
        "List",
        ["List", ["List", 1, 2, 3, 4], ["List", 5, 6, 7, 8], ["List", 9, 10, 11, 12]],
        ["List", ["List", 13, 14, 15, 16], ["List", 17, 18, 19, 20], ["List", 21, 22, 23, 24]],
    ]
    assert xs.upperbounds == [
        "List",
        ["List", ["List", 10, 20, 30, 40], ["List", 50, 60, 70, 80], ["List", 90, 100, 110, 120]],
        ["List", ["List", 130, 140, 150, 160], ["List", 170, 180, 190, 200], ["List", 210, 220, 230, 240]],
    ]
    assert xs.initial_values == [
        "List",
        ["List", ["List", 1, 1, 1, 1], ["List", 2, 2, 2, 2], ["List", 3, 3, 3, 3]],
        ["List", ["List", 4, 4, 4, 4], ["List", 5, 5, 5, 5], ["List", 6, 6, 6, 6]],
    ]

    # by """induction""", other dimensions should work juuust fine!


def test_get_values_list():
    """Test that values can be get correctly from a TensorVariable."""
    # Test 1D
    xs = TensorVariable(
        name="A",
        symbol="A",
        variable_type="integer",
        shape=[3],
        lowerbounds=[1, 2, 3],
        upperbounds=[10, 20, 30],
        initial_values=[1, 1, 1],
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initial_values = xs.get_initial_values()

    assert lowerbounds == [1, 2, 3]
    assert upperbounds == [10, 20, 30]
    assert initial_values == [1, 1, 1]

    # Test 2D
    xs = TensorVariable(
        name="X",
        symbol="X",
        variable_type="integer",
        shape=[2, 3],
        lowerbounds=[[1, 2, 3], [4, 5, 6]],
        upperbounds=[[10, 20, 30], [40, 50, 60]],
        initial_values=[[1, 1, 1], [2, 2, 2]],
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initial_values = xs.get_initial_values()

    assert lowerbounds == [[1, 2, 3], [4, 5, 6]]
    assert upperbounds == [[10, 20, 30], [40, 50, 60]]
    assert initial_values == [[1, 1, 1], [2, 2, 2]]

    # Test 3D
    xs = TensorVariable(
        name="B",
        symbol="B",
        variable_type="integer",
        shape=[2, 3, 4],
        lowerbounds=[
            [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],
            [[13, 14, 15, 16], [17, 18, 19, 20], [21, 22, 23, 24]],
        ],
        upperbounds=[
            [[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]],
            [[130, 140, 150, 160], [170, 180, 190, 200], [210, 220, 230, 240]],
        ],
        initial_values=[[[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3]], [[4, 4, 4, 4], [5, 5, 5, 5], [6, 6, 6, 6]]],
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initial_values = xs.get_initial_values()

    assert lowerbounds == [
        [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],
        [[13, 14, 15, 16], [17, 18, 19, 20], [21, 22, 23, 24]],
    ]
    assert upperbounds == [
        [[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]],
        [[130, 140, 150, 160], [170, 180, 190, 200], [210, 220, 230, 240]],
    ]
    assert initial_values == [[[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3]], [[4, 4, 4, 4], [5, 5, 5, 5], [6, 6, 6, 6]]]

    # test for constraint as well
    xs = TensorConstant(
        name="C",
        symbol="C",
        shape=[2, 2, 2],
        values=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
    )

    values = xs.get_values()

    assert values == [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]


def test_tensor_constant_init():
    """Tests that tensor constants are created and represented correctly in the MathJSON format."""
    # Test 1D
    xs = TensorConstant(
        name="A",
        symbol="A",
        shape=[3],
        values=[1, 2, 3],
    )

    assert xs.name == "A"
    assert xs.symbol == "A"
    assert xs.shape[0] == 3
    assert xs.values == ["List", 1, 2, 3]

    # Test 2D
    xs = TensorConstant(
        name="B",
        symbol="B",
        shape=[2, 2],
        values=[[1, 2], [3, 4]],
    )

    assert xs.name == "B"
    assert xs.symbol == "B"
    assert xs.shape[0] == 2
    assert xs.shape[1] == 2
    assert xs.values == ["List", ["List", 1, 2], ["List", 3, 4]]

    # Test 3D
    xs = TensorConstant(
        name="C",
        symbol="C",
        shape=[2, 2, 2],
        values=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
    )

    assert xs.name == "C"
    assert xs.symbol == "C"
    assert xs.shape[0] == 2
    assert xs.shape[1] == 2
    assert xs.shape[2] == 2
    assert xs.values == ["List", ["List", ["List", 1, 2], ["List", 3, 4]], ["List", ["List", 5, 6], ["List", 7, 8]]]


def test_tensor_problem_definition():
    """Test defining a problem with TensorVariable and TensorConstant."""
    problem = simple_knapsack_vectors()  # noqa: F841


def test_get_values_list_single():
    """Test that values can be get correctly from a TensorVariable.

    Test that values can be get correctly from a TensorVariable when the
    initial value and bounds have been defined using just a single value.
    """
    # Test 1D
    xs = TensorVariable(
        name="A",
        symbol="A",
        variable_type="integer",
        shape=[3],
        lowerbounds=4,
        upperbounds=22,
        initial_values=8,
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initial_values = xs.get_initial_values()

    assert lowerbounds == [4, 4, 4]
    assert upperbounds == [22, 22, 22]
    assert initial_values == [8, 8, 8]

    # Test 2D
    xs = TensorVariable(
        name="X",
        symbol="X",
        variable_type="integer",
        shape=[2, 3],
        lowerbounds=4,
        upperbounds=6,
        initial_values=5,
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initial_values = xs.get_initial_values()

    assert lowerbounds == np.full([2, 3], 4).tolist()
    assert upperbounds == np.full([2, 3], 6).tolist()
    assert initial_values == np.full([2, 3], 5).tolist()

    # Test 3D
    xs = TensorVariable(
        name="B",
        symbol="B",
        variable_type="integer",
        shape=[2, 3, 4],
        lowerbounds=-10,
        upperbounds=24,
        initial_values=12,
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initial_values = xs.get_initial_values()

    assert lowerbounds == np.full([2, 3, 4], -10).tolist()
    assert upperbounds == np.full([2, 3, 4], 24).tolist()
    assert initial_values == np.full([2, 3, 4], 12).tolist()

    # test for constraint as well
    xs = TensorConstant(
        name="C",
        symbol="C",
        shape=[2, 2, 2],
        values=42,
    )

    values = xs.get_values()

    assert values == np.full([2, 2, 2], 42).tolist()


def test_getitem_tensor_constant():
    """Test the __getitem__ method for TensorConstant."""
    # Test 1D
    x_name = "Acid"
    x_symbol = "A"
    x_values = [1, 2, 3, 4, 5]
    x_shape = [5]
    x = TensorConstant(name=x_name, symbol=x_symbol, shape=x_shape, values=x_values)

    constant_1 = x[1]
    constant_3 = x[3]
    constant_5 = x[5]

    assert constant_1.value == x_values[1 - 1]
    assert constant_1.name == f"{x_name} at position [{1}]"
    assert constant_1.symbol == f"{x_symbol}_{1}"

    assert constant_3.value == x_values[3 - 1]
    assert constant_3.name == f"{x_name} at position [{3}]"
    assert constant_3.symbol == f"{x_symbol}_{3}"

    assert constant_5.value == x_values[5 - 1]
    assert constant_5.name == f"{x_name} at position [{5}]"
    assert constant_5.symbol == f"{x_symbol}_{5}"

    # Test 2D
    y_name = "Tension"
    y_symbol = "Y"
    y_values = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    y_shape = [3, 4]
    y = TensorConstant(name=y_name, symbol=y_symbol, shape=y_shape, values=y_values)

    constant_2_3 = y[2, 3]

    assert constant_2_3.value == y_values[2 - 1][3 - 1]
    assert constant_2_3.name == f"{y_name} at position {[2, 3]}"
    assert constant_2_3.symbol == f"{y_symbol}_2_3"


def test_getitem_tensor_variable():
    """Test the __getitem__ method for TensorVariable."""
    # Test 1D
    x_name = "Potato"
    x_symbol = "P"
    x_shape = [3]
    x_type = VariableTypeEnum.integer
    x_initial_values = [2, 4, 6]
    x_lowerbounds = [0, 0, 1]
    x_upperbounds = [10, 10, 20]

    x = TensorVariable(
        name=x_name,
        symbol=x_symbol,
        shape=x_shape,
        variable_type=x_type,
        initial_values=x_initial_values,
        lowerbounds=x_lowerbounds,
        upperbounds=x_upperbounds,
    )

    x_1 = x[1]
    x_2 = x[2]
    x_3 = x[3]

    assert x_1.name == f"{x_name} at position {[1]}"
    assert x_1.symbol == f"{x_symbol}_{1}"
    assert x_1.variable_type == x_type
    assert x_1.initial_value == x_initial_values[1 - 1]
    assert x_1.lowerbound == x_lowerbounds[1 - 1]
    assert x_1.upperbound == x_upperbounds[1 - 1]

    assert x_2.name == f"{x_name} at position {[2]}"
    assert x_2.symbol == f"{x_symbol}_{2}"
    assert x_2.variable_type == x_type
    assert x_2.initial_value == x_initial_values[2 - 1]
    assert x_2.lowerbound == x_lowerbounds[2 - 1]
    assert x_2.upperbound == x_upperbounds[2 - 1]

    assert x_3.name == f"{x_name} at position {[3]}"
    assert x_3.symbol == f"{x_symbol}_{3}"
    assert x_3.variable_type == x_type
    assert x_3.initial_value == x_initial_values[3 - 1]
    assert x_3.lowerbound == x_lowerbounds[3 - 1]
    assert x_3.upperbound == x_upperbounds[3 - 1]

    # test 2D
    y_name = "Carrot"
    y_symbol = "C"
    y_shape = [2, 3]
    y_type = VariableTypeEnum.integer
    y_initial_values = [[0, -1, 1], [9, 8, 7]]
    y_lowerbounds = [[-10, -20, -30], [1, 2, 3]]
    y_upperbounds = [[10, 20, 30], [11, 22, 33]]

    y = TensorVariable(
        name=y_name,
        symbol=y_symbol,
        shape=y_shape,
        variable_type=y_type,
        initial_values=y_initial_values,
        lowerbounds=y_lowerbounds,
        upperbounds=y_upperbounds,
    )

    y_2_1 = y[2, 1]

    assert y_2_1.name == f"{y_name} at position {[2, 1]}"
    assert y_2_1.symbol == f"{y_symbol}_2_1"
    assert y_2_1.variable_type == y_type
    assert y_2_1.initial_value == y_initial_values[2 - 1][1 - 1]
    assert y_2_1.lowerbound == y_lowerbounds[2 - 1][1 - 1]
    assert y_2_1.upperbound == y_upperbounds[2 - 1][1 - 1]

    # Test when None values
    z_name = "None"
    z_symbol = "Z"
    z_shape = [2, 2]
    z_type = VariableTypeEnum.integer
    z_initial_values = None
    z_lowerbounds = [[None, None], [1, 2]]
    z_upperbounds = [[10, None], [None, 20]]

    z = TensorVariable(
        name=z_name,
        symbol=z_symbol,
        shape=z_shape,
        variable_type=z_type,
        initial_values=z_initial_values,
        lowerbounds=z_lowerbounds,
        upperbounds=z_upperbounds,
    )

    z_1_1 = z[1, 1]
    z_2_2 = z[2, 2]

    assert z_1_1.name == f"{z_name} at position {[1, 1]}"
    assert z_1_1.symbol == f"{z_symbol}_1_1"
    assert z_1_1.variable_type == z_type
    assert z_1_1.initial_value is None
    assert z_1_1.lowerbound == z_lowerbounds[1 - 1][1 - 1]
    assert z_1_1.upperbound == z_upperbounds[1 - 1][1 - 1]

    assert z_2_2.name == f"{z_name} at position {[2, 2]}"
    assert z_2_2.symbol == f"{z_symbol}_2_2"
    assert z_2_2.variable_type == z_type
    assert z_2_2.initial_value is None
    assert z_2_2.lowerbound == z_lowerbounds[2 - 1][2 - 1]
    assert z_2_2.upperbound == z_upperbounds[2 - 1][2 - 1]


def test_to_constants():
    """Test the to_constants method of TensorConstant."""
    # Test 1D
    x_name = "Acid"
    x_symbol = "A"
    x_values = [1, 2, 3, 4, 5]
    x_shape = [5]
    x = TensorConstant(name=x_name, symbol=x_symbol, shape=x_shape, values=x_values)

    xs = x.to_constants()

    assert len(xs) == x_shape[0]

    xs_values = [xs_.value for xs_ in xs]
    for v in x_values:
        assert v in xs_values

    xs_symbols = [xs_.symbol for xs_ in xs]
    for i in range(1, x_shape[0] + 1):
        assert f"{x_symbol}_{i}" in xs_symbols

    xs_names = [xs_.name for xs_ in xs]
    for i in range(1, x_shape[0] + 1):
        assert f"{x_name} at position {[i]}" in xs_names

    # Test 2D
    y_name = "Tension"
    y_symbol = "Y"
    y_values = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    y_shape = [3, 3]
    y = TensorConstant(name=y_name, symbol=y_symbol, shape=y_shape, values=y_values)
    ys = y.to_constants()

    assert len(ys) == y_shape[0] * y_shape[1]

    ys_values = [ys_.value for ys_ in ys]
    for row in y_values:
        for v in row:
            assert v in ys_values

    ys_symbols = [ys_.symbol for ys_ in ys]
    for i in range(1, y_shape[0] + 1):
        for j in range(1, y_shape[1] + 1):
            assert f"{y_symbol}_{i}_{j}" in ys_symbols

    ys_names = [ys_.name for ys_ in ys]
    for i in range(1, y_shape[0] + 1):
        for j in range(1, y_shape[1] + 1):
            assert f"{y_name} at position [{i}, {j}]" in ys_names


def test_to_variables():
    """Test the to_variables method of TensorVariable."""
    # Test 1D
    x_name = "Potato"
    x_symbol = "P"
    x_shape = [3]
    x_type = VariableTypeEnum.integer
    x_initial_values = [2, 4, 6]
    x_lowerbounds = [0, 0, 1]
    x_upperbounds = [10, 10, 20]
    x = TensorVariable(
        name=x_name,
        symbol=x_symbol,
        shape=x_shape,
        variable_type=x_type,
        initial_values=x_initial_values,
        lowerbounds=x_lowerbounds,
        upperbounds=x_upperbounds,
    )
    x_vars = x.to_variables()

    assert len(x_vars) == x_shape[0]
    for i, var in enumerate(x_vars, start=1):
        assert var.name == f"{x_name} at position [{i}]"
        assert var.symbol == f"{x_symbol}_{i}"
        assert var.variable_type == x_type
        assert var.initial_value == x_initial_values[i - 1]
        assert var.lowerbound == x_lowerbounds[i - 1]
        assert var.upperbound == x_upperbounds[i - 1]

    # Test 2D
    y_name = "Carrot"
    y_symbol = "C"
    y_shape = [2, 3]
    y_type = VariableTypeEnum.integer
    y_initial_values = [[0, -1, 1], [9, 8, 7]]
    y_lowerbounds = [[-10, -20, -30], [1, 2, 3]]
    y_upperbounds = [[10, 20, 30], [11, 22, 33]]
    y = TensorVariable(
        name=y_name,
        symbol=y_symbol,
        shape=y_shape,
        variable_type=y_type,
        initial_values=y_initial_values,
        lowerbounds=y_lowerbounds,
        upperbounds=y_upperbounds,
    )
    y_vars = y.to_variables()

    assert len(y_vars) == y_shape[0] * y_shape[1]
    for i in range(1, y_shape[0] + 1):
        for j in range(1, y_shape[1] + 1):
            var = y_vars[(i - 1) * y_shape[1] + (j - 1)]
            assert var.name == f"{y_name} at position [{i}, {j}]"
            assert var.symbol == f"{y_symbol}_{i}_{j}"
            assert var.variable_type == y_type
            assert var.initial_value == y_initial_values[i - 1][j - 1]
            assert var.lowerbound == y_lowerbounds[i - 1][j - 1]
            assert var.upperbound == y_upperbounds[i - 1][j - 1]

    # Test when None values
    z_name = "None"
    z_symbol = "Z"
    z_shape = [2, 2]
    z_type = VariableTypeEnum.integer
    z_initial_values = None
    z_lowerbounds = [[None, None], [1, 2]]
    z_upperbounds = [[10, None], [None, 20]]
    z = TensorVariable(
        name=z_name,
        symbol=z_symbol,
        shape=z_shape,
        variable_type=z_type,
        initial_values=z_initial_values,
        lowerbounds=z_lowerbounds,
        upperbounds=z_upperbounds,
    )
    z_vars = z.to_variables()

    assert len(z_vars) == z_shape[0] * z_shape[1]
    for i in range(1, z_shape[0] + 1):
        for j in range(1, z_shape[1] + 1):
            var = z_vars[(i - 1) * z_shape[1] + (j - 1)]
            assert var.name == f"{z_name} at position [{i}, {j}]"
            assert var.symbol == f"{z_symbol}_{i}_{j}"
            assert var.variable_type == z_type
            assert var.initial_value is None
            assert var.lowerbound == z_lowerbounds[i - 1][j - 1]
            assert var.upperbound == z_upperbounds[i - 1][j - 1]
