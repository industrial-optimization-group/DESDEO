from desdeo.problem.schema import (
    Objective,
    Problem,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)

def mixed_variable_dimensions_problem():
    """Defines a problem with variables with mixed dimensions.

    Has both Variable and TensorVariable types of variables, where the TensorVariables have
    varying number of dimensions. Mostly for testing purposes.
    """
    x = Variable(
        name="Regular variable",
        symbol="x",
        variable_type=VariableTypeEnum.real,
        lowerbound=-1.0,
        upperbound=1.0,
        initial_value=0.5,
    )

    y = TensorVariable(
        name="1D vector",
        symbol="Y",
        shape=[5],
        variable_type=VariableTypeEnum.real,
        lowerbounds=5,
        upperbounds=5,
        initial_values=5,
    )

    z = TensorVariable(
        name="2D vector",
        symbol="Z",
        shape=[5, 2],
        variable_type=VariableTypeEnum.real,
        lowerbounds=-100,
        upperbounds=100,
        initial_values=1,
    )

    a = TensorVariable(
        name="2D vector",
        symbol="A",
        shape=[2, 3, 2],
        variable_type=VariableTypeEnum.real,
        lowerbounds=-100,
        upperbounds=100,
        initial_values=1,
    )

    dummy = Objective(
        name="dummy objective, not relevant",
        symbol="f_1",
        func="x - Y[1]",
        maximize=False,
        ideal=-1000,
        nadir=1000,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    dummy2 = Objective(
        name="dummy objective, not relevant",
        symbol="f_2",
        func="-x + Y[1]",
        maximize=False,
        ideal=-1000,
        nadir=1000,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

    return Problem(
        name="Mixed variable dimensions problem",
        description="A problem with variables with mixed dimensions. For testing.",
        variables=[x, y, z, a],
        objectives=[dummy, dummy2],
    )