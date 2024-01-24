""" Macros for dynamically adding content to the documentation."""

import json

from desdeo.problem.schema import (
    Variable,
    Constant,
    Constraint,
    Objective,
    ExtraFunction,
    ScalarizationFunction,
    EvaluatedSolutions,
    EvaluatedInfo,
    Problem,
)


def generate_schema_and_example(model_class, example):
    """Generates a schema and JSON example of a given model."""
    schema_json = model_class.model_json_schema()
    example_json = example.model_dump_json(indent=2)

    return json.dumps(schema_json, indent=4), example_json


def get_constant_info():
    """Gets information for a Constant model."""
    example = Constant(name="constant example", symbol="c", value=42.1)
    return generate_schema_and_example(Constant, example)


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


def get_extra_function_info():
    """Gets information for an ExtraFunction model."""
    example = ExtraFunction(name="example extra function", symbol="m", func=["Divide", "f_1", 100])
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


def get_evaluated_info_info():
    """Gets information for an EvaluatedInfo model."""
    example = EvaluatedInfo(source="NSGA-III", dominated=False)
    return generate_schema_and_example(EvaluatedInfo, example)


def get_evaluated_solutions_info():
    """Gets information for an EvaluatedSolutions model."""
    evaluated_info_example = EvaluatedInfo(source="NSGA-III", dominated=False)
    example = EvaluatedSolutions(
        info=evaluated_info_example,
        decision_vectors=[[4.2, -1.2, 6.6], [4.2, -1.2, 6.6], [4.2, -1.2, 6.6]],
        objective_vectors=[[1, 2, 3], [1, 2, 3], [1, 2, 3]],
    )
    return generate_schema_and_example(EvaluatedSolutions, example)


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
    evaluated_solutions_example = EvaluatedSolutions(
        info=EvaluatedInfo(source="NSGA-III", dominated=False),
        decision_vectors=[[4.2, -1.2, 6.6], [4.2, -1.2, 6.6], [4.2, -1.2, 6.6]],
        objective_vectors=[[1, 2, 3], [1, 2, 3], [1, 2, 3]],
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
        evaluated_solutions=[evaluated_solutions_example],
    )
    return generate_schema_and_example(Problem, example)


def define_env(env):
    """Defines the env used by mkdocs and registers various functions as macros.

    For any function to be utilized in the documentation, it must be registered.
    """
    env.macro(get_constant_info)
    env.macro(get_variable_info)
    env.macro(get_extra_function_info)
    env.macro(get_scalarization_function_info)
    env.macro(get_objective_info)
    env.macro(get_constraint_info)
    env.macro(get_evaluated_info_info)
    env.macro(get_evaluated_solutions_info)
    env.macro(get_problem_info)
