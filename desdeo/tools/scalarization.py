"""Defines templates for scalariztation functions and utilities to handle the templates.

Note that when scalarization functions are defined, they must add the post-fix
'_min' to any symbol representing objective functions so that the maximization
or minimization of the corresponding objective functions may be correctly
accounted for when computing scalarization function values.
"""

import json
import pprint

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    InfixExpressionParser,
    Problem,
    ScalarizationFunction,
)


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


def get_corrected_ideal_and_nadir(problem: Problem) -> tuple[dict[str, float | None], dict[str, float | None] | None]:
    """Compute the corrected ideal and nadir points depending if an objective function is to be maximized or not.

    I.e., the ideal and nadir point element for objectives to be maximized will be multiplied by -1.

    Args:
        problem (Problem): the problem with the ideal and nadir points.

    Returns:
        tuple[list[float], list[float]]: a list with the corrected ideal point
            and a list with the corrected nadir point. Will return None for missing
            elements.
    """
    ideal_point = {
        objective.symbol: objective.ideal if not objective.maximize else -objective.ideal
        for objective in problem.objectives
    }
    nadir_point = {
        objective.symbol: objective.nadir if not objective.maximize else -objective.nadir
        for objective in problem.objectives
    }

    return ideal_point, nadir_point


def create_asf(
    problem: Problem,
    reference_point: dict[str, float],
    reference_in_aug=False,
    delta: float = 0.000001,
    rho: float = 0.000001,
) -> str:
    """Creates the achievement scalarizing function for the given problem and reference point.

    Requires that the ideal and nadir point have been defined for the problem.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        reference_point (dict[str, float]): a reference point as an objective dict.
        reference_in_aug (bool): whether the reference point should be used in
            the augmentation term as well. Defaults to False.
        delta (float, optional): the scalar value used to define the utopian point (ideal - delta).
            Defaults to 0.000001.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 0.000001.

    Raises:
        ScalarizationError: there are missing elements in the reference point, or if any of the ideal or nadir
            point values are undefined (None).

    Returns:
        str: The scalarization function in infix format.
    """
    # check that the reference point has all the objective components
    if not all(obj.symbol in reference_point for obj in problem.objectives):
        msg = f"The given reference point {reference_point} does not have a component defined for all the objectives."
        raise ScalarizationError(msg)

    # check if minimizing or maximizing and adjust ideal and nadir values correspondingly
    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)

    if any(value is None for value in ideal_point.values()) or any(value is None for value in nadir_point.values()):
        msg = f"There are undefined values in either the ideal ({ideal_point}) or the nadir point ({nadir_point})."
        raise ScalarizationError(msg)

    # Build the max term
    max_operands = [
        (
            f"({obj.symbol}_min - {reference_point[obj.symbol]}{" * -1" if obj.maximize else ''}) "
            f"/ ({nadir_point[obj.symbol]} - ({ideal_point[obj.symbol]} - {delta}))"
        )
        for obj in problem.objectives
    ]
    max_term = f"{Op.MAX}({', '.join(max_operands)})"

    # Build the augmentation term
    if not reference_in_aug:
        aug_operands = [
            f"{obj.symbol}_min / ({nadir_point[obj.symbol]} - ({ideal_point[obj.symbol]} - {delta}))"
            for obj in problem.objectives
        ]
    else:
        aug_operands = [
            (
                f"({obj.symbol}_min - {reference_point[obj.symbol]}{" * -1" if obj.maximize else 1}) "
                f"/ ({nadir_point[obj.symbol]} - ({ideal_point[obj.symbol]} - {delta}))"
            )
            for obj in problem.objectives
        ]

    aug_term = " + ".join(aug_operands)

    # Return the whole scalarization function
    return f"{max_term} + {rho} * ({aug_term})"


def create_asf_generic(
    problem: Problem,
    reference_point: list[float],
    weights: list[float],
    reference_in_aug=False,
    delta: float = 0.000001,
    rho: float = 0.000001,
) -> str:
    """Creates the generic achievement scalarizing function for the given problem and reference point, and weights.

    Args:
        problem (Problem): the problem to which the scalarization function should be added.
        reference_point (list[float]): a reference point with as many components as there are objectives.
        weights (list[float]): the weights to be used in the scalarization function. must be positive.
        reference_in_aug (bool, optional): Whether the reference point should be used in the augmentation term.
            Defaults to False.
        delta (float, optional): the scalar value used to define the utopian point (ideal - delta). Defaults to 0.000001.
        rho (float, optional): the weight factor used in the augmentation term. Defaults to 0.000001.

    Raises:
        ScalarizationError: If either the reference point or the weights given are missing any of the objective
            components.
        ScalarizationError: If any of the ideal or nadir point values are undefined (None).

    Returns:
        str: _description_
    """
    # check that the reference point has all the objective components
    if not all(obj.symbol in reference_point for obj in problem.objectives):
        msg = f"The given reference point {reference_point} does not have a component defined for all the objectives."
        raise ScalarizationError(msg)

    # check that the weights have all the objective components
    if not all(obj.symbol in weights for obj in problem.objectives):
        msg = f"The given weight vector {weights} does not have a component defined for all the objectives."
        raise ScalarizationError(msg)

    # check if minimizing or maximizing and adjust ideal and nadir values correspondingly
    ideal_point, nadir_point = get_corrected_ideal_and_nadir(problem)

    if any(value is None for value in ideal_point.values()) or any(value is None for value in nadir_point.values()):
        msg = f"There are undefined values in either the ideal ({ideal_point}) or the nadir point ({nadir_point})."
        raise ScalarizationError(msg)

    # Build the max term
    max_operands = [
        (f"({obj.symbol}_min - {reference_point[obj.symbol]} * {-1 if obj.maximize else 1}) / ({weights[obj.symbol]})")
        for obj in problem.objectives
    ]
    max_term = f"{Op.MAX}({', '.join(max_operands)})"

    # Build the augmentation term
    if not reference_in_aug:
        aug_operands = [f"{obj.symbol}_min / ({weights[obj.symbol]})" for obj in problem.objectives]
    else:
        aug_operands = [
            (
                f"({obj.symbol}_min - {reference_point[obj.symbol]}) * {-1 if obj.maximize else 1} / "
                f"({weights[obj.symbol]})"
            )
            for obj in problem.objectives
        ]

    aug_term = " + ".join(aug_operands)

    # Return the whole scalarization function
    return f"{max_term} + {rho} * ({aug_term})"


def create_weighted_sums(problem: Problem, weights: dict[str, float]) -> str:
    """Add the weighted sums scalarization.

    Args:
        problem (Problem): the problem to which the scalarization should be added.
        weights (dict[str, float]): the weights. For the method to work, the weights
            should sum to 1. However, this is not a condition that is checked.

    Raises:
        ScalarizationError: if the weights are missing any of the objective components.

    Returns:
        str: The scalarization function for in infix format.
    """
    # check that the weights have all the objective components
    if not all(obj.symbol in weights for obj in problem.objectives):
        msg = f"The given weight vector {weights} does not have a component defined for all the objectives."
        raise ScalarizationError(msg)

    # Build the sum
    sum_terms = [f"({weights[obj.symbol]} * {obj.symbol}_min)" for obj in problem.objectives]
    return " + ".join(sum_terms)


def create_from_objective(problem: Problem, objective_symbol: str) -> str:
    """Creates a scalarization where one of the problem's objective functions is optimized.

    Args:
        problem (Problem): the problem to which the scalarization should be added.
        objective_symbol (str): the symbol of the objective function to be optimized.

    Raises:
        ScalarizationError: the given objective_symbol does not exist in the problem.

    Returns:
        str: _description_
    """
    # check that symbol exists
    if objective_symbol not in (correct_symbols := [objective.symbol for objective in problem.objectives]):
        msg = f"The given objective symbol {objective_symbol} should be one of {correct_symbols}."
        raise ScalarizationError(msg)

    return f"1 * {objective_symbol}_min"


def create_epsilon_constraints(
    problem: Problem, objective_symbol: str, epsilons: dict[str, float]
) -> tuple[str, list[str]]:
    """Creates expressions for an epsilon constraints scalarization and constraints.

    It is assumed that epsilon have been given in a format where each objective is to be minimized.

    Args:
        problem (Problem): the problem to scalarize.
        objective_symbol (str): the objective used as the objective in the epsilon constraint scalarization.
        epsilons (dict[str, float]): the epsilon constraint values in a dict
            with each key being an objective's symbol.

    Raises:
        ScalarizationError: `objective_symbol` not found in problem definition.

    Returns:
        tuple[str, list[str]]: the first element is the expression of the
            scalarized objective, the second element is a list of expressions of the
            constraints. The constraints are in less than or equal format.
    """
    if objective_symbol not in (correct_symbols := [objective.symbol for objective in problem.objectives]):
        msg = f"The given objective symbol {objective_symbol} should be one of {correct_symbols}."
        raise ScalarizationError(msg)

    scalarization_expr = f"1 * {objective_symbol}_min"

    # the epsilons must be given such that each objective function is to be minimized
    constraint_exprs = [
        f"{obj.symbol}_min - {epsilons[obj.symbol]}" for obj in problem.objectives if obj.symbol != objective_symbol
    ]

    return scalarization_expr, constraint_exprs


def create_epsilon_constraints_json(
    problem: Problem, objective_symbol: str, epsilons: dict[str, float]
) -> tuple[str, list[str]]:
    """Creates JSON expressions for an epsilon constraints scalarization and constraints.

    It is assumed that epsilon have been given in a format where each objective is to be minimized.

    Args:
        problem (Problem): the problem to scalarize.
        objective_symbol (str): the objective used as the objective in the epsilon constraint scalarization.
        epsilons (dict[str, float]): the epsilon constraint values in a dict
            with each key being an objective's symbol.

    Raises:
        ScalarizationError: `objective_symbol` not found in problem definition.

    Returns:
        tuple[list, list]: the first element is the expression of the scalarized objective expressed in MathJSON format.
        The second element is a list of expressions of the constraints expressed in MathJSON format.
            The constraints are in less than or equal format.
    """
    correct_symbols = [objective.symbol for objective in problem.objectives]
    if objective_symbol not in correct_symbols:
        msg = f"The given objective symbol {objective_symbol} should be one of {correct_symbols}."
        raise ScalarizationError(msg)
    correct_symbols.remove(objective_symbol)

    scalarization_expr = ["Multiply", 1, f"{objective_symbol}_min"]

    # the epsilons must be given such that each objective function is to be minimized
    constraint_exprs = [["Add", f"{obj}_min", ["Negate", epsilons[obj]]] for obj in correct_symbols]

    return scalarization_expr, constraint_exprs


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


def add_lte_constraints(
    problem: Problem, funcs: list[str], symbols: list[str], names: list[str | None] | None = None
) -> Problem:
    """Adds constraints to a problem that are defined in the less than or equal format.

    Is is assumed that the constraints expression at position funcs[i] is symbolized by the
    symbol at position symbols[i] for all i.

    Does not modify problem, but makes a copy of it instead and returns it.

    Args:
        problem (Problem): the problem to which the constraints are added.
        funcs (list[str]): the expressions of the constraints.
        symbols (list[str]): the symbols of the constraints. In order.
        names (list[str  |  None] | None, optional): The names of the
            constraints. For any name with 'None' the symbol is used as the name. If
            names is None, then the symbol is used as the name for all the
            constraints. Defaults to None.

    Raises:
        ScalarizationError: if the lengths of the arguments do not match.

    Returns:
        Problem: a copy of the original problem with the constraints added.
    """
    if (len_f := len(funcs)) != (len_s := len(symbols)) and names is not None and (len_n := len(names)) != len(funcs):
        msg = (
            f"The lengths of ({len_f=}) and 'symbols' ({len_s=}) must match. "
            f"If 'names' is not None, then its length ({len_n=}) must also match."
        )
        raise ScalarizationError(msg)

    if names is None:
        names = symbols

    return problem.model_copy(
        update={
            "constraints": [
                *(problem.constraints if problem.constraints is not None else []),
                *[
                    Constraint(
                        name=(name if (name := names[i]) is not None else symbols[i]),
                        symbol=symbols[i],
                        cons_type=ConstraintTypeEnum.LTE,
                        func=funcs[i],
                    )
                    for i in range(len(funcs))
                ],
            ]
        }
    )


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
    sf, con_exprs = create_epsilon_constraints(
        problem, "f_3", {"f_1": 2.5, "f_2": 3.5, "f_3": 1.2, "f_4": 0.8, "f_5": 5.1}
    )

    problem_w_cons = add_lte_constraints(problem, con_exprs, [f"con_{i}" for i in range(1, len(con_exprs) + 1)])

    print(problem_w_cons.constraints)

    print(con_exprs)

    parser = InfixExpressionParser()
    print(f"Infix:\n\n{sf}\n")
    dump = json.dumps(parser.parse(sf), indent=2)
    print("JSON:\n")
    pprint.pprint(json.loads(dump))
