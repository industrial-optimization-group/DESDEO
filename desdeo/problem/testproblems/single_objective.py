"""Here a variety of single-objective optimization problems are defined."""

import math

from desdeo.problem import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    ExtraFunction,
    Objective,
    Problem,
    Variable,
    VariableTypeEnum,
)


def mystery_function() -> Problem:
    r"""Add the constrained mystery function as defined in Sasena 2002.

    Global solution's value (constrained): -1.174261 at x = [2.5044, 2.5778].

    Returns:
        Problem: the problem model.

    References:
        Michael Sasena. 2002. Flexibility and Eiciency Enhancements For
            Constrained Global Design Optimization with Kriging Approximations. Ph.D.  Dissertation.
    """
    pi = Constant(name="Pi", symbol="PI", value=math.pi)
    x_1 = Variable(
        name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=5.0, initial_value=0.1
    )
    x_2 = Variable(
        name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.0, upperbound=5.0, initial_value=0.1
    )

    f_1_def = "2 + 0.01*(x_2 - x_1**2)**2 + (1 - x_1)**2 + 2*(2 - x_2)**2 + 7*Sin(0.5*x_1)*Sin(0.7*x_1*x_2)"
    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f_1_def,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    c_1_def = "-Sin(x_1 - x_2 - PI/8.0)"
    c_1 = Constraint(
        name="c_1",
        symbol="c_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=c_1_def,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="Mystery function",
        description="The single-objective mystery function.",
        constants=[pi],
        variables=[x_1, x_2],
        objectives=[f_1],
        constraints=[c_1],
    )


def new_branin_function() -> Problem:
    """Implements the new Branin function.

    Global optimal -268.78792 at x = [3.2730, 0.0489].
    """
    pi = Constant(name="Pi", symbol="PI", value=math.pi)
    x_1 = Variable(
        name="x_1",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=-5.0,
        upperbound=10.0,
        initial_value=0.1,
    )
    x_2 = Variable(
        name="x_2",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=0.0,
        upperbound=15.0,
        initial_value=0.1,
    )

    f_1_def = "-(x_1 - 10)**2 - (x_2 - 15)**2"
    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f_1_def,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    c_1_def = "(x_2 - (5.1 / (4*PI**2)) * x_1**2 + (5 / PI)*x_1 - 6)**2 + 10*(1 - 1/(8*PI))*Cos(x_1) + 5"
    c_1 = Constraint(
        name="c_1",
        symbol="c_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=c_1_def,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="New Branin function",
        description="The single-objective mystery function.",
        constants=[pi],
        variables=[x_1, x_2],
        objectives=[f_1],
        constraints=[c_1],
    )


def mishras_bird_constrained() -> Problem:
    """Implements the constrained variant of Mishra's bird function.

    Global optima: -106.7645367 at [-3.1302468, -1.5821422]
    """
    x_1 = Variable(
        name="x_1",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=-10.0,
        upperbound=0.0,
        initial_value=-0.1,
    )
    x_2 = Variable(
        name="x_2",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=-6.5,
        upperbound=0.0,
        initial_value=-0.1,
    )

    f_1_def = "Sin(x_2)*Exp((1 - Cos(x_1))**2) + Cos(x_1)*Exp((1 - Sin(x_2))**2) + (x_1 - x_2)**2"
    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f_1_def,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    c_1_def = "(x_1 + 5)**2 + (x_2 + 5)**2 - 25"
    c_1 = Constraint(
        name="c_1",
        symbol="c_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=c_1_def,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="Mishra's bird function",
        description="The constrained variant of Mishra's bird function",
        variables=[x_1, x_2],
        objectives=[f_1],
        constraints=[c_1],
    )


def rosenbrock_disk() -> Problem:
    """Defines the Rosenbrock test functions constrained to a disk.

    Global optima is 0 at [1.0, 1.0].
    """
    x = Variable(
        name="x",
        symbol="x",
        variable_type=VariableTypeEnum.real,
        lowerbound=-1.5,
        upperbound=1.5,
        initial_value=0.1,
    )
    y = Variable(
        name="y",
        symbol="y",
        variable_type=VariableTypeEnum.real,
        lowerbound=-1.5,
        upperbound=1.5,
        initial_value=0.1,
    )

    f_1_def = "(1 - x)**2 + 100*(y - x**2)**2"
    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f_1_def,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    c_1_def = "x**2 + y**2 - 2.0"
    c_1 = Constraint(
        name="c_1",
        symbol="c_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=c_1_def,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="Rosenbrock test function",
        description="The Rosenbrock test function constrained to a disk.",
        variables=[x, y],
        objectives=[f_1],
        constraints=[c_1],
    )


def townsend_modified() -> Problem:
    """Implements the modified Townsend function.

    Global optima is -2.0239884 at [2.0052938, 1.1944509].
    """
    x = Variable(
        name="x",
        symbol="x",
        variable_type=VariableTypeEnum.real,
        lowerbound=-2.25,
        upperbound=2.25,
        initial_value=0.1,
    )
    y = Variable(
        name="y",
        symbol="y",
        variable_type=VariableTypeEnum.real,
        lowerbound=-2.5,
        upperbound=1.75,
        initial_value=0.1,
    )

    f_1_def = "-1.0 * (Cos((x - 0.1)*y))**2 - x*Sin(3.0*x + y)"
    f_1 = Objective(
        name="f_1",
        symbol="f_1",
        func=f_1_def,
        maximize=False,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    # define the atan2 functions as the double of the arctangent of the half tangent
    # Obs! Risk of dividing by zero!
    t_symbol = "t"
    t_def = "2.0*Arctan(x / (Sqrt(y**2 + x**2) + y))"
    t = ExtraFunction(
        name="Atan2", symbol=t_symbol, func=t_def, is_convex=False, is_linear=False, is_twice_differentiable=True
    )

    c_1_def = "x**2 + y**2 - (2.0*Cos(t) - 0.5*Cos(2.0*t) - 0.25*Cos(3.0*t) - 0.125*Cos(4.0*t))**2 - (2.0*Sin(t))**2"
    c_1 = Constraint(
        name="c_1",
        symbol="c_1",
        cons_type=ConstraintTypeEnum.LTE,
        func=c_1_def,
        is_linear=False,
        is_convex=False,
        is_twice_differentiable=True,
    )

    return Problem(
        name="Townsend function",
        description="The modified Townsend function.",
        variables=[x, y],
        objectives=[f_1],
        constraints=[c_1],
        extra_funcs=[t],
    )
