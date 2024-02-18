"""Tests the proximal solver."""
import numpy.testing as npt

from desdeo.problem import simple_data_problem
from desdeo.tools.scalarization import add_scalarization_function, create_asf, create_weighted_sums
from desdeo.tools.proximal_solver import create_proximal_solver


def test_proximal_with_simple_data_problem():
    """Test the proximal solver with a simple data problem."""
    problem = simple_data_problem()
    objective_symbols = [obj.symbol for obj in problem.objectives]
    objective_values = problem.discrete_definition.objective_values
    variable_values = problem.discrete_definition.variable_values
    const_symbol = problem.constraints[0].symbol

    # we know that (for simple data problem)
    # g_1 = sum of squares of variables (max)
    # g_2 = minimum of variables (min)
    # g_3 = negative sum of variables (min)
    # variables are defined in ascending order
    # the constraint's value is always 'y_1 + y_2 - 10'

    # Test 1: the optimum of the first objective function
    # should result in the last objective vector, since the first objective is to be maximized
    obj_should_be = [objective_values[symbol][-1] for symbol in objective_values]
    const_should_be = [variable_values["y_1"][-1] + variable_values["y_2"][-1] - 1000]

    sf = create_weighted_sums(problem, weights=[1, 0, 0])

    problem, target = add_scalarization_function(problem, sf, symbol="ws_1")

    solver = create_proximal_solver(problem)

    res = solver(target)

    npt.assert_array_almost_equal([res.optimal_objectives[symbol] for symbol in objective_symbols], obj_should_be)
    npt.assert_array_almost_equal(res.constraint_values[const_symbol], const_should_be)

    # Test 2: the optimum of the second objective function
    # should result in the first objective vector, since we are minimizing
    obj_should_be = [objective_values[symbol][0] for symbol in objective_values]
    const_should_be = [variable_values["y_1"][0] + variable_values["y_2"][0] - 1000]

    sf = create_weighted_sums(problem, weights=[0, 1, 0])

    problem, target = add_scalarization_function(problem, sf, symbol="ws_2")

    solver = create_proximal_solver(problem)

    res = solver(target)

    npt.assert_array_almost_equal([res.optimal_objectives[symbol] for symbol in objective_symbols], obj_should_be)
    npt.assert_array_almost_equal(res.constraint_values[const_symbol], const_should_be)

    # Test 3: the optimum of the last objective function
    # should result in the last objective vector, since we are minimizing
    obj_should_be = [objective_values[symbol][-1] for symbol in objective_values]
    const_should_be = [variable_values["y_1"][-1] + variable_values["y_2"][-1] - 1000]

    sf = create_weighted_sums(problem, weights=[0, 0, 1])

    problem, target = add_scalarization_function(problem, sf, symbol="ws_3")

    solver = create_proximal_solver(problem)

    res = solver(target)

    npt.assert_array_almost_equal([res.optimal_objectives[symbol] for symbol in objective_symbols], obj_should_be)
    npt.assert_array_almost_equal(res.constraint_values[const_symbol], const_should_be)

    # Test 4: asf, should result in the 5th objective vector
    obj_should_be = [objective_values[symbol][4] for symbol in objective_values]
    const_should_be = [variable_values["y_1"][4] + variable_values["y_2"][4] - 1000]

    reference_point = [750.0, 6.1, -27.1]
    sf = create_asf(problem, reference_point)

    problem, target = add_scalarization_function(problem, sf, symbol="asf")

    solver = create_proximal_solver(problem)

    res = solver(target)

    npt.assert_array_almost_equal([res.optimal_objectives[symbol] for symbol in objective_symbols], obj_should_be)
    npt.assert_array_almost_equal(res.constraint_values[const_symbol], const_should_be)
