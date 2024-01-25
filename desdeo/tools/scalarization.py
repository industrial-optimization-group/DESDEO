"""Defines templates for scalariztation functions and utilities to handle the templates."""

from jinja2 import Environment, FileSystemLoader, Template

from desdeo.problem.schema import Problem

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


template = env.get_template("asf.j2")


# Render the template with a specific value for k
rendered = template.render(
    k=3,
    Op=Op,
    reference_point=[3, 3, 3],
    ideal_point=[1, 2, 3],
    nadir_point=[4, 5, 6],
    objective_symbols=["f_1", "f_2", "f_3"],
    delta=1e-6,
    rho=1e-9,
)

print(rendered)
