from desdeo.problem import (
    Problem,
    Constant,
    Constraint,
    Objective,
    PyomoEvaluator,
    TensorConstant,
    TensorVariable,
    MathParser,
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
        initialvalues=[1, 1, 1],
    )

    assert xs.name == "A"
    assert xs.symbol == "A"
    assert xs.shape[0] == 3
    assert xs.lowerbounds == ["List", 1, 2, 3]
    assert xs.upperbounds == ["List", 10, 20, 30]
    assert xs.initialvalues == ["List", 1, 1, 1]

    # Test 2D
    xs = TensorVariable(
        name="X",
        symbol="X",
        variable_type="integer",
        shape=[2, 3],
        lowerbounds=[[1, 2, 3], [4, 5, 6]],
        upperbounds=[[10, 20, 30], [40, 50, 60]],
        initialvalues=[[1, 1, 1], [2, 2, 2]],
    )

    assert xs.name == "X"
    assert xs.symbol == "X"
    assert xs.shape[0] == 2
    assert xs.shape[1] == 3
    assert xs.lowerbounds == ["List", ["List", 1, 2, 3], ["List", 4, 5, 6]]
    assert xs.upperbounds == ["List", ["List", 10, 20, 30], ["List", 40, 50, 60]]
    assert xs.initialvalues == ["List", ["List", 1, 1, 1], ["List", 2, 2, 2]]

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
        initialvalues=[[[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3]], [[4, 4, 4, 4], [5, 5, 5, 5], [6, 6, 6, 6]]],
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
    assert xs.initialvalues == [
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
        initialvalues=[1, 1, 1],
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initialvalues = xs.get_initial_values()

    assert lowerbounds == [1, 2, 3]
    assert upperbounds == [10, 20, 30]
    assert initialvalues == [1, 1, 1]

    # Test 2D
    xs = TensorVariable(
        name="X",
        symbol="X",
        variable_type="integer",
        shape=[2, 3],
        lowerbounds=[[1, 2, 3], [4, 5, 6]],
        upperbounds=[[10, 20, 30], [40, 50, 60]],
        initialvalues=[[1, 1, 1], [2, 2, 2]],
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initialvalues = xs.get_initial_values()

    assert lowerbounds == [[1, 2, 3], [4, 5, 6]]
    assert upperbounds == [[10, 20, 30], [40, 50, 60]]
    assert initialvalues == [[1, 1, 1], [2, 2, 2]]

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
        initialvalues=[[[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3]], [[4, 4, 4, 4], [5, 5, 5, 5], [6, 6, 6, 6]]],
    )

    lowerbounds = xs.get_lowerbound_values()
    upperbounds = xs.get_upperbound_values()
    initialvalues = xs.get_initial_values()

    assert lowerbounds == [
        [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],
        [[13, 14, 15, 16], [17, 18, 19, 20], [21, 22, 23, 24]],
    ]
    assert upperbounds == [
        [[10, 20, 30, 40], [50, 60, 70, 80], [90, 100, 110, 120]],
        [[130, 140, 150, 160], [170, 180, 190, 200], [210, 220, 230, 240]],
    ]
    assert initialvalues == [[[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3]], [[4, 4, 4, 4], [5, 5, 5, 5], [6, 6, 6, 6]]]

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
    n_items = 4
    weight_values = [2, 3, 4, 5]
    profit_values = [3, 5, 6, 8]
    efficiency_values = [4, 2, 7, 3]

    max_weight = Constant(name="Maximum weights", symbol="w_max", value=5)

    weights = TensorConstant(name="Weights of the items", symbol="W", shape=[len(weight_values)], values=weight_values)
    profits = TensorConstant(name="Profits", symbol="P", shape=[len(profit_values)], values=profit_values)
    efficiencies = TensorConstant(
        name="Efficiencies", symbol="E", shape=[len(efficiency_values)], values=efficiency_values
    )

    choices = TensorVariable(
        name="Chosen items",
        symbol="X",
        shape=[n_items],
        variable_type="binary",
        lowerbounds=n_items * [0],
        upperbounds=n_items * [1],
        initialvalues=n_items * [1],
    )

    profit_objective = Objective(
        name="max profit",
        symbol="f_1",
        func="P*X",  # todo, define vector multiplication
        maximize=True,
        ideal=8,
        nadir=0,
        is_linear=True,
        is_convex=False,
        is_twice_differentiable=False,
    )

    efficiency_objective = Objective(
        name="max efficiency",
        symbol="f_2",
        func="E*X",  # todo, define vector multiplication
        maximize=True,
        ideal=7,
        nadir=0,
        is_linear=True,
        is_convex=False,
        is_twice_differentiable=False,
    )

    weight_constraint = Constraint(
        name="Weight constraint",
        symbol="g_1",
        cons_type="<=",
        func="W*X - w_max",
        is_linear=True,
        is_convex=False,
        is_twice_differentiable=False,
    )

    problem = Problem(
        name="Simple two-objective Knapsack problem",
        description="A simple variant of the classic combinatorial problem.",
        constants=[max_weight, weights, profits, efficiencies],
        variables=[choices],
        objectives=[profit_objective, efficiency_objective],
        constraints=[weight_constraint],
    )

    # TODO seems to work nicely for simple linear expressions, try something like x_i_j and w_i_j next
    evaluator = PyomoEvaluator(problem)
