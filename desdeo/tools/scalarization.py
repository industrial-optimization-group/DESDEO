"""Defines templates for scalariztation functions and utilities to handle the templates.

Note that when scalarization functions are defined, they must add the post-fix
'_min' to any symbol representing objective functions so that the maximization
or minimization of the corresponding objective functions may be correctly
accounted for when computing scalarization function values.
"""

import json, pprint

from desdeo.problem import InfixExpressionParser
from desdeo.problem import Problem, ScalarizationFunction


class ScalarizationError(Exception):
    """Raised when issues with creating or adding scalarization functions are encountered."""


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


def create_asf(problem: Problem, reference_point: list[float], delta: float = 0.000001, rho: float = 0.000001) -> str:
    """Creates the achievement scalarizing function for the given problem and reference point.

    Requires that the ideal and nadir point have been defined for the problem.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        reference_point (list[float]): a reference poin with as many components as there are objectives.
        delta (float, optional): the scalar value used to define the utopian point (ideal - delta).
            Defaults to 0.000001.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 0.000001.

    Raises:
        ScalarizationError: when the number of components in the reference point
            does not match the number of objectives, or if any of the ideal or nadir
            point values are undefined (None).

    Returns:
        str: The scalarization function in infix format.
    """
    if (len_ref := len(reference_point)) != (len_obj := len(problem.objectives)):
        msg = (
            f"The number of components in the reference point ({len_ref}) must "
            f"match the number of objective ({len_obj})."
        )
        raise ScalarizationError(msg)

    objective_symbols = [objective.symbol for objective in problem.objectives]
    ideal_point = [objective.ideal for objective in problem.objectives]
    nadir_point = [objective.nadir for objective in problem.objectives]

    if (None in ideal_point) or (None in nadir_point):
        msg = f"There are undefined values in either the ideal ({ideal_point}) or the nadir point ({nadir_point})."
        raise ScalarizationError(msg)

    # Build the max term
    max_operands = [
        f"({objective_symbols[i]}_min - {reference_point[i]}) / ({nadir_point[i]} - ({ideal_point[i]} - {delta}))"
        for i in range(len(problem.objectives))
    ]
    max_term = f"{Op.MAX}({', '.join(max_operands)})"

    # Build the augmentation term
    aug_operands = [
        f"{objective_symbols[i]}_min / ({nadir_point[i]} - ({ideal_point[i]} - {delta}))"
        for i in range(len(problem.objectives))
    ]
    aug_term = " + ".join(aug_operands)

    # Return the whole scalarization function
    return f"{max_term} + {rho} * ({aug_term})"


def create_weighted_sums(problem: Problem, weights: list[float]) -> str:
    """Add the weighted sums scalarization.

    Args:
        problem (Problem): the problem to which the scalarization should be added.
        weights (list[float]): the weights. For the method to work, the weights
            should sum to 1. However, this is not a condition that is checked.

    Raises:
        ScalarizationError: if the number of weights and number of objectives in problem do not match.

    Returns:
        str: The scalarization function for in infix format.
    """
    # Check dimensions, there must be as many weights as there are objectives
    if (len_obj := len(problem.objectives)) != (len_w := len(weights)):
        msg = f"The number of weights ({len(len_w)}) does not match the number of objectives ({len_obj})."
        raise ScalarizationError(msg)

    objective_symbols = [objective.symbol for objective in problem.objectives]

    # Build the sum
    sum_terms = [f"({weights[i]} * {objective_symbols[i]}_min)" for i in range(len(problem.objectives))]
    return " + ".join(sum_terms)


def add_scalarization_function(
    problem: Problem,
    func: str,
    symbol: str,
    name: str | None = None,
) -> tuple[Problem, str]:
    """Adds a scalarization function to a Problem.

    Returns a new instanse of the Problem with the new scalarization function
    and the symbol of the scalarization function added.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        func (str): the scalarization function to be added as a string in infix notation.
        symbol (str): the symbol reference the added scalarization function.
            This is important when the added scalarization function should be
            utilized when optimizing a problem.
        name (str, optional): the name to be given to the scalarization
            function. If None, the symbol is used as the name. Defaults to None.

    Returns:
        tuple[Problem, str]: A tuple with the new Problem with the added
            scalarization function and the function's symbol.
    """
    scalarization_function = ScalarizationFunction(
        name=symbol if name is None else name,
        symbol=symbol,
        func=func,
    )
    return problem.add_scalarization(scalarization_function), symbol


if __name__ == "__main__":
    from desdeo.problem import river_pollution_problem

    problem = river_pollution_problem()
    problem = problem.model_copy(
        update={
            "objectives": [
                objective.model_copy(update={"ideal": 0.5, "nadir": 5.5}) for objective in problem.objectives
            ]
        }
    )
    res = create_asf(problem, [1, 2, 3, 2, 1], delta=0.1, rho=2.2)

    parser = InfixExpressionParser()
    print(f"Infix:\n\n{res}\n")
    dump = json.dumps(parser.parse(res), indent=2)
    print("JSON:\n")
    pprint.pprint(json.loads(dump))
