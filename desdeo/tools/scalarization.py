"""Defines templates for scalariztation functions and utilities to handle the templates."""

from jinja2 import Environment, FileSystemLoader, Template

from desdeo.problem.schema import Problem
from desdeo.problem.testproblems import binh_and_korn

# TODO: fix
TEMPLATE_PATH = "desdeo/tools/scalarization_templates"

env = Environment(loader=FileSystemLoader(TEMPLATE_PATH))


class Op:
    """Defines the supported operators in the MathJSON format."""

    # TODO: move this to problem/schema.py, make it use this, and import it here from there
    # Basic arithmetic operators
    NEGATE = "Negate"
    ADD = "Add"
    SUB = "Subtract"
    MUL = "Multiply"
    DIV = "Divide"

    # Exponentation and logarithms
    EXP = "Exp"
    LN = "Ln"
    LB = "Lb"
    LG = "Lg"
    LOP = "LogOnePlus"
    SQRT = "Sqrt"
    SQUARE = "Square"
    POW = "Power"

    # Rounding operators
    ABS = "Abs"
    CEIL = "Ceil"
    FLOOR = "Floor"

    # Trigonometric operations
    ARCCOS = "Arccos"
    ARCCOSH = "Arccosh"
    ARCSIN = "Arcsin"
    ARCSINH = "Arcsinh"
    ARCTAN = "Arctan"
    ARCTANH = "Arctanh"
    COS = "Cos"
    COSH = "Cosh"
    SIN = "Sin"
    SINH = "Sinh"
    TAN = "Tan"
    TANH = "Tanh"

    # Comparison operators
    EQUAL = "Equal"
    GREATER = "Greater"
    GREATER_EQUAL = "GreaterEqual"
    LESS = "Less"
    LESS_EQUAL = "LessEqual"
    NOT_EQUAL = "NotEqual"

    # Other operators
    MAX = "Max"
    RATIONAL = "Rational"


def create_asf(problem: Problem, reference_point: list[float], delta: float = 0.000001, rho: float = 0.000001):
    """Creates the achievement scalarizing function for the given problem and reference point.

    Args:
        problem (Problem): _description_
        reference_point (list[float]): _description_.
        delta (float, optional): _description_. Defaults to 0.000001.
        rho (float, optional): _description_. Defaults to 0.000001.
    """
    # Question: is minimization assumed here always?
    # Question: unwrapping by replacing function is fine?
    objective_symbols = [objective.symbol for objective in problem.objectives]
    ideal_point = [objective.ideal for objective in problem.objectives]
    nadir_point = [objective.nadir for objective in problem.objectives]

    # Build the max term
    max_operands = [
        f"({objective_symbols[i]} - {reference_point[i]}) / ({nadir_point[i]} - ({ideal_point[i]} - {delta}))"
        for i in range(len(problem.objectives))
    ]
    max_term = f"{Op.MAX}({', '.join(max_operands)})"

    # Build the augmentation term
    aug_operands = [
        f"{objective_symbols[i]} / ({nadir_point[i]} - ({ideal_point[i]} - {delta}))"
        for i in range(len(problem.objectives))
    ]
    aug_term = " + ".join(aug_operands)

    # Return the whole scalarization function
    return f"{max_term} + {rho} * ({aug_term})"


if __name__ == "__main__":
    problem = binh_and_korn()
    res = create_asf(problem, [5.0, 2.0])
    print(res)
