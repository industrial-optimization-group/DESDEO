from desdeo.problem import (
    Problem,
    Constant,
    Constraint,
    Objective,
    PyomoEvaluator,
    simple_knapsack_vectors,
    TensorConstant,
    TensorVariable,
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
