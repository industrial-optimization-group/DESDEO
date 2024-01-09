"""Tests for the MathJSON parser."""
import json  # noqa: I001
import pytest

from pathlib import Path
from desdeo.problem.parser import MathParser

import polars as pl


@pytest.fixture
def four_bar_truss_problem():
    """Loads the four bar truss problem."""
    with Path("tests/example_problem.json").open("r") as f:
        return json.load(f)


def test_basic():
    """A basic test to test the parsing of Polish notation to polars expressions."""
    math_parser = MathParser()
    json_expr = [
        "Add",
        ["Divide", ["Multiply", 2, ["Square", "x_1"]], "x_2"],
        ["Multiply", "x_1", "x_3"],
        -180,
    ]

    expr = math_parser.parse(expr=json_expr)

    data = pl.DataFrame({"x_1": [20, 30], "x_2": [5, 8], "x_3": [60, 21]})

    objectives = data.select(expr.alias("Objective 1"))

    assert objectives["Objective 1"][0] == 1180
    assert objectives["Objective 1"][1] == 675


"""
def test_parser_truss_problem(four_bar_truss_problem):
    problem = four_bar_truss_problem

    parser = MathParser("polars")

    expr = parser.parse(problem["variables"][0]["upperbound"])

    parsed_variable_ub
    parsed_variable_ub
"""
