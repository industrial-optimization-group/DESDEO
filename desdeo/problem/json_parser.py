"""Defines a parser to parse multiobjective optimziation problems defined in a JSON foramt."""
from enum import Enum
from functools import reduce

import polars as pl
import pyomo.environ as pyomo
from pyomo.core.expr.numeric_expr import MaxExpression as _PyomoMax

import gurobipy as gp
from gurobipy_model_extension import GurobipyModel


class FormatEnum(str, Enum):
    """Enumerates the supported formats the JSON format may be parsed to."""

    polars = "polars"
    pyomo = "pyomo"
    gurobipy = "gurobipy"


class ParserError(Exception):
    """Raised when an error related to the MathParser class in encountered."""


class MathParser:
    """A class to instantiate MathJSON parsers.

    Currently only parses MathJSON to polars expressions. Pyomo WIP.
    """

    def __init__(self, to_format: FormatEnum = "polars"):
        """Create a parser instance for parsing MathJSON notation into polars expressions.

        Args:
            to_format (FormatEnum, optional): to which format a JSON representation should be parsed to.
                Defaults to "polars".
        """
        # Define operator names. Change these when the name is altered in the JSON format.
        # Basic arithmetic operators
        self.NEGATE: str = "Negate"
        self.ADD: str = "Add"
        self.SUB: str = "Subtract"
        self.MUL: str = "Multiply"
        self.DIV: str = "Divide"

        # Exponentation and logarithms
        self.EXP: str = "Exp"
        self.LN: str = "Ln"
        self.LB: str = "Lb"
        self.LG: str = "Lg"
        self.LOP: str = "LogOnePlus"
        self.SQRT: str = "Sqrt"
        self.SQUARE: str = "Square"
        self.POW: str = "Power"

        # Rounding operators
        self.ABS: str = "Abs"
        self.CEIL: str = "Ceil"
        self.FLOOR: str = "Floor"

        # Trigonometric operations
        self.ARCCOS: str = "Arccos"
        self.ARCCOSH: str = "Arccosh"
        self.ARCSIN: str = "Arcsin"
        self.ARCSINH: str = "Arcsinh"
        self.ARCTAN: str = "Arctan"
        self.ARCTANH: str = "Arctanh"
        self.COS: str = "Cos"
        self.COSH: str = "Cosh"
        self.SIN: str = "Sin"
        self.SINH: str = "Sinh"
        self.TAN: str = "Tan"
        self.TANH: str = "Tanh"

        # Comparison operators
        self.EQUAL: str = "Equal"
        self.GREATER: str = "Greater"
        self.GE: str = "GreaterEqual"
        self.LESS: str = "Less"
        self.LE: str = "LessEqual"
        self.NE: str = "NotEqual"

        # Other operators
        self.MAX: str = "Max"
        self.RATIONAL: str = "Rational"

        self.literals = int | float

        def to_expr(x: self.literals | pl.Expr):
            """Helper function to convert literals to polars expressions."""
            return pl.lit(x) if isinstance(x, self.literals) else x

        polars_env = {
            # Define the operations for the different operators.
            # Basic arithmetic operations
            self.NEGATE: lambda x: -to_expr(x),
            self.ADD: lambda *args: reduce(lambda x, y: to_expr(x) + to_expr(y), args),
            self.SUB: lambda *args: reduce(lambda x, y: to_expr(x) - to_expr(y), args),
            self.MUL: lambda *args: reduce(lambda x, y: to_expr(x) * to_expr(y), args),
            self.DIV: lambda *args: reduce(lambda x, y: to_expr(x) / to_expr(y), args),
            # Exponentiation and logarithms
            self.EXP: lambda x: pl.Expr.exp(to_expr(x)),
            self.LN: lambda x: pl.Expr.log(to_expr(x)),
            self.LB: lambda x: pl.Expr.log(to_expr(x), 2),
            self.LG: lambda x: pl.Expr.log10(to_expr(x)),
            self.LOP: lambda x: pl.Expr.log1p(to_expr(x)),
            self.SQRT: lambda x: pl.Expr.sqrt(to_expr(x)),
            self.SQUARE: lambda x: to_expr(x) ** 2,
            self.POW: lambda x, y: to_expr(x) ** to_expr(y),
            # Trigonometric operations
            self.ARCCOS: lambda x: pl.Expr.arccos(to_expr(x)),
            self.ARCCOSH: lambda x: pl.Expr.arccosh(to_expr(x)),
            self.ARCSIN: lambda x: pl.Expr.arcsin(to_expr(x)),
            self.ARCSINH: lambda x: pl.Expr.arcsinh(to_expr(x)),
            self.ARCTAN: lambda x: pl.Expr.arctan(to_expr(x)),
            self.ARCTANH: lambda x: pl.Expr.arctanh(to_expr(x)),
            self.COS: lambda x: pl.Expr.cos(to_expr(x)),
            self.COSH: lambda x: pl.Expr.cosh(to_expr(x)),
            self.SIN: lambda x: pl.Expr.sin(to_expr(x)),
            self.SINH: lambda x: pl.Expr.sinh(to_expr(x)),
            self.TAN: lambda x: pl.Expr.tan(to_expr(x)),
            self.TANH: lambda x: pl.Expr.tanh(to_expr(x)),
            # Rounding operations
            self.ABS: lambda x: pl.Expr.abs(to_expr(x)),
            self.CEIL: lambda x: pl.Expr.ceil(to_expr(x)),
            self.FLOOR: lambda x: pl.Expr.floor(to_expr(x)),
            # Other operations
            self.RATIONAL: lambda lst: reduce(lambda x, y: x / y, lst),  # Not supported
            self.MAX: lambda *args: reduce(lambda x, y: pl.max_horizontal(to_expr(x), to_expr(y)), args),
        }

        pyomo_env = {
            # Define the operations for the different operators.
            # Basic arithmetic operations
            self.NEGATE: lambda x: -x,
            self.ADD: lambda *args: reduce(lambda x, y: x + y, args),
            self.SUB: lambda *args: reduce(lambda x, y: x - y, args),
            self.MUL: lambda *args: reduce(lambda x, y: x * y, args),
            self.DIV: lambda *args: reduce(lambda x, y: x / y, args),
            # Exponentiation and logarithms
            self.EXP: lambda x: pyomo.exp(x),
            self.LN: lambda x: pyomo.log(x),
            self.LB: lambda x: pyomo.log(x) / pyomo.log(2),  # change of base, pyomo has no log2
            self.LG: lambda x: pyomo.log10(x),
            self.LOP: lambda x: pyomo.log(x + 1),
            self.SQRT: lambda x: pyomo.sqrt(x),
            self.SQUARE: lambda x: x**2,
            self.POW: lambda x, y: x**y,
            # Trigonometric operations
            self.ARCCOS: lambda x: pyomo.acos(x),
            self.ARCCOSH: lambda x: pyomo.acosh(x),
            self.ARCSIN: lambda x: pyomo.asin(x),
            self.ARCSINH: lambda x: pyomo.asinh(x),
            self.ARCTAN: lambda x: pyomo.atan(x),
            self.ARCTANH: lambda x: pyomo.atanh(x),
            self.COS: lambda x: pyomo.cos(x),
            self.COSH: lambda x: pyomo.cosh(x),
            self.SIN: lambda x: pyomo.sin(x),
            self.SINH: lambda x: pyomo.sinh(x),
            self.TAN: lambda x: pyomo.tan(x),
            self.TANH: lambda x: pyomo.tanh(x),
            # Rounding operations
            self.ABS: lambda x: abs(x),
            self.CEIL: lambda x: pyomo.ceil(x),
            self.FLOOR: lambda x: pyomo.floor(x),
            # Other operations
            self.RATIONAL: lambda lst: reduce(lambda x, y: x / y, lst),  # not supported
            # probably a better idea to reformulate expressions with a max when utilized with pyomo
            # self.MAX: lambda *args: reduce(lambda x, y: _PyomoMax((x, y)), args),
            self.MAX: lambda *args: _PyomoMax(args),
        }

        def gp_error():
            msg = "The gurobipy model format only supports linear and quadratic expressions."
            ParserError(msg) 

        gurobipy_env = {
            # Define the operations for the different operators.
            # Basic arithmetic operations
            self.NEGATE: lambda x: -x,
            self.ADD: lambda *args: reduce(lambda x, y: x + y, args),
            self.SUB: lambda *args: reduce(lambda x, y: x - y, args),
            self.MUL: lambda *args: reduce(lambda x, y: x * y, args),
            self.DIV: lambda *args: reduce(lambda x, y: x / y, args),

            # Exponentiation and logarithms
            # it would be possible to implement some of these with the special functions that
            # gurobi has to offer, but they would only work under specific circumstances
            self.EXP: lambda x: gp_error(),
            self.LN: lambda x: gp_error(),
            self.LB: lambda x: gp_error(),
            self.LG: lambda x: gp_error(),
            self.LOP: lambda x: gp_error(),
            self.SQRT: lambda x: gp_error(),
            self.SQUARE: lambda x: x**2,
            self.POW: lambda x, y: x**y, #this will likely cause an error at some point for most y

            # Trigonometric operations
            # it would be possible to implement some of these with the special functions that
            # gurobi has to offer, but they would only work under specific circumstances
            self.ARCCOS: lambda x: gp_error(),
            self.ARCCOSH: lambda x: gp_error(),
            self.ARCSIN: lambda x: gp_error(),
            self.ARCSINH: lambda x: gp_error(),
            self.ARCTAN: lambda x: gp_error(),
            self.ARCTANH: lambda x: gp_error(),
            self.COS: lambda x: gp_error(),
            self.COSH: lambda x: gp_error(),
            self.SIN: lambda x: gp_error(),
            self.SINH: lambda x: gp_error(),
            self.TAN: lambda x: gp_error(),
            self.TANH: lambda x: gp_error(),
            # Rounding operations
            self.ABS: lambda x: gp.abs_(x),
            self.CEIL: lambda x: gp_error(),
            self.FLOOR: lambda x: gp_error(),
            # Other operations
            self.RATIONAL: lambda lst: reduce(lambda x, y: x / y, lst),  # not supported
            self.MAX: lambda *args: gp.max_(args),
        }

        match to_format:
            case FormatEnum.polars:
                self.env = polars_env
                self.parse = self._parse_to_polars
            case FormatEnum.pyomo:
                self.env = pyomo_env
                self.parse = self._parse_to_pyomo
            case FormatEnum.gurobipy:
                self.env = gurobipy_env
                self.parse = self._parse_to_gurobipy
            case _:
                msg = f"Given target format {to_format} not supported. Must be one of {FormatEnum}."
                raise ParserError(msg)

    def _parse_to_polars(self, expr: list | str | int | float) -> pl.Expr:
        """Recursively parses JSON math expressions and returns a polars expression.

        Arguments:
            expr (list): A list with a Polish notation expression that describes a, e.g.,
                ["Multiply", ["Sqrt", 2], "x2"]

        Returns:
            pl.Expr: A polars expression that may be evaluated further.

        Raises:
            ParserError: If the type of the text neither str,list nor int,float, it will
                raise type error; If the operation in expr not found, it means we currently
                don't support such function operation.
        """
        if isinstance(expr, pl.Expr):
            # Terminal case: polars expression
            return expr
        if isinstance(expr, str):
            # Terminal case: str expression (represents a column name)
            return pl.col(expr)
        if isinstance(expr, self.literals):
            # Terminal case: numeric literal
            return pl.lit(expr)

        if isinstance(expr, list):
            # Extract the operation name
            if isinstance(expr[0], str) and expr[0] in self.env:
                op_name = expr[0]
                # Parse the operands
                operands = [self.parse(e) for e in expr[1:]]

                if isinstance(operands, list) and len(operands) == 1:
                    # if the operands have redundant brackets, remove them
                    operands = operands[0]

                if isinstance(operands, list):
                    return self.env[op_name](*operands)

                return self.env[op_name](operands)

            # else, assume the list contents are parseable expressions
            return [self.parse(e) for e in expr]

        msg = f"Encountered unsupported type '{type(expr)}' during parsing."
        raise ParserError(msg)

    def _parse_to_pyomo(self, expr: list | str | int | float, model: pyomo.Model) -> pyomo.Expression:
        """Parses the MathJSON format recursively into a Pyomo expression.

        Args:
            expr (list | str | int | float): a list with a Polish notation expression that describes a, e.g.,
                ["Multiply", ["Sqrt", 2], "x2"]
            model (pyomo.Model): a pyomo model with the symbols defined appearing in the expression.
                E.g., "x2" -> model.x2 must be defined.

        Returns:
            pyomo.Expression: returns a pyomo expression equivalent to the original expressions.
        """
        if isinstance(expr, pyomo.Expression):
            # Terminal case: pyomo expression
            return expr
        if isinstance(expr, str):
            # Terminal case: str expression, represent a variable or expression
            return getattr(model, expr)
        if isinstance(expr, self.literals):
            # Terminal case: numeric literal
            return expr

        if isinstance(expr, list):
            # Extract the operation name
            if isinstance(expr[0], str) and expr[0] in self.env:
                op_name = expr[0]
                # Parse the operands
                operands = [self._parse_to_pyomo(e, model) for e in expr[1:]]

                if isinstance(operands, list) and len(operands) == 1:
                    # if the operands have redundant brackets, remove them
                    operands = operands[0]

                if isinstance(operands, list):
                    return self.env[op_name](*operands)

                return self.env[op_name](operands)

            # else, assume the list contents are parseable expressions
            return [self._parse_to_pyomo(e, model) for e in expr]

        msg = f"Encountered unsupported type '{type(expr)}' during parsing."
        raise ParserError(msg)
    
    def _parse_to_gurobipy( self, expr: list | str | int | float, model: GurobipyModel ) -> ( 
            gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float):
        """Parses the MathJSON format recursively into a gurobipy expression.
        Gurobi only fundamentally supports linear and quadratic expressions, and this parser
        does not check that the inputs are valid. If you try to input something else, you will
        likely encounter an error at some point.

        Args:
            expr (list | str | int | float): a list with a Polish notation expression that describes a, e.g.,
                ["Multiply", ["Sqrt", 2], "x2"]
            model (GurobipyModel): a gurobipy model with the symbols defined appearing in the expression.
                E.g., "x2" -> model.x2 must be defined.

        Returns:
            Returns a gurobipy expression (that can belong into one of multiple types) equivalent to the original expressions.
            All possible output types should be supported as parts of gurobipy constraints. gurobipy.GenExpr at least isn't 
            supported as an objective function.
        """
        gpexpression = ( 
            gp.Var | 
            gp.MVar | 
            gp.LinExpr | 
            gp.QuadExpr | 
            gp.MLinExpr | 
            gp.MQuadExpr | 
            gp.GenExpr 
        )

        if isinstance(expr, gpexpression):
            # Terminal case: gurobipy expression
            return expr
        if isinstance(expr, str):
            # Terminal case: str expression, represent a variable or expression
            return model.getExpressionByName(expr)
        if isinstance(expr, self.literals):
            # Terminal case: numeric literal
            return expr

        if isinstance(expr, list):
            # Extract the operation name
            if isinstance(expr[0], str) and expr[0] in self.env:
                op_name = expr[0]
                # Parse the operands
                operands = [self._parse_to_gurobipy(e, model) for e in expr[1:]]

                if isinstance(operands, list) and len(operands) == 1:
                    # if the operands have redundant brackets, remove them
                    operands = operands[0]

                if isinstance(operands, list):
                    return self.env[op_name](*operands)

                return self.env[op_name](operands)

            # else, assume the list contents are parseable expressions
            return [self._parse_to_gurobipy(e, model) for e in expr]

        msg = f"Encountered unsupported type '{type(expr)}' during parsing."
        raise ParserError(msg)


def replace_str(lst: list | str, target: str, sub: list | str | float | int) -> list:
    """Replace a target in list with a substitution recursively.

    Arguments:
    lst (list or str): The list where the substitution is to be made.
    target (str): The target of the substitution.
    sub (list or str): The content to substitute the target.

    Return:
    list or str: The list or str with the substitution.

    Example:
    replace_str("["Max", "g_i", ["Add","g_i","f_i"]]]", "_i", "_1") --->
    ["Max", "g_1", ["Add","g_1","f_1"]]]
    """
    if isinstance(lst, list):
        return [replace_str(item, target, sub) for item in lst]
    if isinstance(lst, str):
        if target in lst:
            if isinstance(sub, str):
                return lst.replace(target, sub)
            return sub
        return lst
    return lst
