"""Macros for dynamically adding content to the documentation."""

import inspect
import json
import re

from desdeo.problem import (
    Constant,
    Constraint,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    Problem,
    ScalarizationFunction,
    TensorConstant,
    TensorVariable,
    Variable,
)


# Schema stuff
def generate_schema_and_example(model_class, example):
    """Generates a schema and JSON example of a given model."""
    schema_json = model_class.model_json_schema()
    example_json = example.model_dump_json(indent=2)

    return json.dumps(schema_json, indent=4), example_json


def get_constant_info():
    """Gets information for a Constant model."""
    example = Constant(name="constant example", symbol="c", value=42.1)
    return generate_schema_and_example(Constant, example)


def get_tensor_constant_info():
    """Gets information for a TensorConstant model."""
    example = TensorConstant(
        name="Weights",
        symbol="A",
        shape=[2, 3],
        values=[[1, 2, 3], [4, 5, 6]],
    )
    return generate_schema_and_example(TensorConstant, example)


def get_variable_info():
    """Gets information for a Variable model."""
    example = Variable(
        name="example variable",
        symbol="x_1",
        variable_type="real",
        lowerbound=-0.75,
        upperbound=11.3,
        initial_value=4.2,
    )
    return generate_schema_and_example(Variable, example)


def get_tensor_variable_info():
    """Gets information for a TensorVariable model."""
    example = TensorVariable(
        name="example variables",
        symbol="X",
        variable_type="real",
        shape=[3, 2],
        lowerbounds=[[0, 0], [1, 1], [-1, -1]],
        upperbounds=[[10, 10], [5, 8], [19, 12]],
        initial_values=[[0.5, 0.5], [1.5, 1.5], [0, 0]],
    )
    return generate_schema_and_example(TensorVariable, example)


def get_extra_function_info():
    """Gets information for an ExtraFunction model."""
    example = ExtraFunction(
        name="example extra function",
        symbol="m",
        func=["Divide", "f_1", 100],
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
        scenario_keys="Scenario_1",
    )
    return generate_schema_and_example(ExtraFunction, example)


def get_scalarization_function_info():
    """Gets information for a ScalarizationFunction model."""
    example = ScalarizationFunction(
        name="Achievement scalarizing function",
        symbol="S",
        func=["Max", ["Multiply", "w_1", ["Add", "f_1", -1.1]], ["Multiply", "w_2", ["Add", "f_2", -2.2]]],
    )
    return generate_schema_and_example(ScalarizationFunction, example)


def get_objective_info():
    """Gets information for an Objective model."""
    example = Objective(
        name="example objective",
        symbol="f_1",
        func=["Divide", ["Add", "x_1", 3], 2],
        maximize=False,
        ideal=-3.3,
        nadir=5.2,
    )
    return generate_schema_and_example(Objective, example)


def get_constraint_info():
    """Gets information for a Constraint model."""
    example = Constraint(
        name="example constraint",
        symbol="g_1",
        func=["Add", ["Add", ["Divide", "x_1", 2], "c"], -4.2],
        cons_type="<=",
    )
    return generate_schema_and_example(Constraint, example)


def get_discrete_representation_info():
    """Gets information for a DiscreteRepresentation model."""
    example = DiscreteRepresentation(
        variable_values={"x_1": [4.1, 4.2, 5.1], "x_2": [-1.1, -1.2, -1.3], "x_3": [7.1, 5.9, 6.2]},
        objective_values={"f_1": [1, 2, 3], "f_2": [5, 2, 1.1], "f_3": [9, 1, 5.5]},
        non_dominated=False,
    )
    return generate_schema_and_example(DiscreteRepresentation, example)


def get_problem_info():
    """Gets information for a Problem model."""
    constant_example = Constant(name="constant example", symbol="c", value=42.1)
    variable_example = Variable(
        name="example variable",
        symbol="x_1",
        variable_type="real",
        lowerbound=-0.75,
        upperbound=11.3,
        initial_value=4.2,
    )
    objective_example = Objective(
        name="example objective",
        symbol="f_1",
        func=["Divide", ["Add", "x_1", 3], 2],
        maximize=False,
        ideal=-3.3,
        nadir=5.2,
    )
    constraint_example = Constraint(
        name="example constraint",
        symbol="g_1",
        func=["Add", ["Add", ["Divide", "x_1", 2], "c"], -4.2],
        cons_type="LTE",
    )
    extra_func_example = ExtraFunction(name="example extra function", symbol="m", func=["Divide", "f_1", 100])
    scalarization_function_example = ScalarizationFunction(
        name="Achievement scalarizing function",
        symbol="S",
        func=["Max", ["Multiply", "w_1", ["Add", "f_1", -1.1]], ["Multiply", "w_2", ["Add", "f_2", -2.2]]],
    )
    discrete_example = DiscreteRepresentation(
        variable_values={"x_1": [4.1, 4.2, 5.1], "x_2": [-1.1, -1.2, -1.3], "x_3": [7.1, 5.9, 6.2]},
        objective_values={"f_1": [1, 2, 3], "f_2": [5, 2, 1.1], "f_3": [9, 1, 5.5]},
        non_dominated=False,
    )
    example = Problem(
        name="Example problem",
        description="This is an example of a the JSON object of the 'Problem' model.",
        constants=[constant_example],
        variables=[variable_example],
        objectives=[objective_example],
        constraints=[constraint_example],
        extra_funcs=[extra_func_example],
        scalarizations_funcs=[scalarization_function_example],
        discrete_representation=discrete_example,
    )
    return generate_schema_and_example(Problem, example)


# Problem definition examples
def extract_marked_section(func, start_marker, end_marker, tab_size=4) -> str:
    """Extract the source code of a function between a start and end marker.

    Args:
        func (Callable): The function which source code should be extracted.
        start_marker (str): The start marker. Usually a comment starting with '#' in the source code of func.
        end_marker (_type_): The end marer. Usually a comment starting with '#' in the source code of func.
        tab_size (int, optional): Tab size used to deindent the source code to look nicer. Defaults to 4.

    Returns:
        str: The snippet of the code of func between the markers.
    """
    pattern = re.compile(f"{start_marker}(.*?){end_marker}", re.DOTALL)
    source = inspect.getsource(func)
    match = pattern.search(source)
    if match:
        snippet = match.group(1).strip()
        # Split the snippet into lines
        lines = snippet.split("\n")

        # Define a single tab's worth of spaces, or use a tab character '\t' if preferred
        tab = " " * tab_size

        # Deindent each line by one tab
        deindented_lines = [line[tab_size:] if line.startswith(tab) else line for line in lines]

        return "\n".join(deindented_lines)

    return "Section not found."


def river_problem_example():
    """An example used in the docs to define the river pollution problem."""
    # variables_start

    from desdeo.problem.schema import Variable

    variable_1 = Variable(
        name="BOD", symbol="x_1", variable_type="real", lowerbound=0.3, upperbound=1.0, initial_value=0.65
    )
    variable_2 = Variable(
        name="DO", symbol="x_2", variable_type="real", lowerbound=0.3, upperbound=1.0, initial_value=0.65
    )

    # variables_end

    # infix_objectives_start

    f_1 = "-4.07 - 2.27 * x_1"
    f_2 = "-2.60 - 0.03 * x_1 - 0.02 * x_2 - 0.01 / (1.39 - x_1**2) - 0.30 / (1.39 - x_2**2)"
    f_3 = "-8.21 + 0.71 / (1.09 - x_1**2)"
    f_4 = "-0.96 + 0.96 / (1.09 - x_2**2)"
    f_5 = "Max(Abs(x_1 - 0.65), Abs(x_2 - 0.65))"

    # infix_objectives_end

    # objectives_start
    from desdeo.problem.schema import Objective

    objective_1 = Objective(name="DO city", symbol="f_1", func=f_1, maximize=False)
    objective_2 = Objective(name="DO municipality", symbol="f_2", func=f_2, maximize=False)
    objective_3 = Objective(name="(negated) ROI fishery", symbol="f_3", func=f_3, maximize=False)
    objective_4 = Objective(name="(negated) ROI city", symbol="f_4", func=f_4, maximize=False)
    objective_5 = Objective(name="BOD deviation", symbol="f_5", func=f_5, maximize=False)
    # objectives_end

    from desdeo.problem.schema import Problem

    # problem_start
    river_problem = Problem(
        name="The river pollution problem",
        description="The river pollution problem to maximize return of investments and minimize pollution.",
        variables=[variable_1, variable_2],
        objectives=[objective_1, objective_2, objective_3, objective_4, objective_5],
    )
    # problem_end

    return river_problem.model_dump_json(indent=2)


def get_river_snippet(marker: str):
    """Helper function to get snippets of the river pollution problem example."""
    return extract_marked_section(river_problem_example, "# " + marker + "_start", "# " + marker + "_end")


# Add stuff to env
def define_env(env):
    """Defines the env used by mkdocs and registers various functions as macros.

    For any function to be utilized in the documentation, it must be registered.
    """
    # Schema examples
    env.macro(get_constant_info)
    env.macro(get_tensor_constant_info)
    env.macro(get_variable_info)
    env.macro(get_tensor_variable_info)
    env.macro(get_extra_function_info)
    env.macro(get_scalarization_function_info)
    env.macro(get_objective_info)
    env.macro(get_constraint_info)
    env.macro(get_problem_info)
    env.macro(get_discrete_representation_info)
    # River problem example
    env.macro(get_river_snippet)
    env.macro(river_problem_example)


if __name__ == "__main__":
    import inspect

    print(river_problem_example())
