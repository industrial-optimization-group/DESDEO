"""Defines a parser to parse multiobjective optimziation problems defined in a JSON foramt."""
from functools import reduce

import polars as pl

SUPPORTED_PARSER_TYPES = ["polars", "pandas"]


class ParserError(Exception):
    """Raised when an error related to the MathParser class in encountered."""


class MathParser:
    """A inner class for only parsing functions in JSON file which defined as CortexJS.

    See https://cortexjs.io/compute-engine/

    Arguments:
    parser (str): Names of the parser:choose (polars, pandas)
    """

    def __init__(self, parser: str = "polars"):
        """Init the class."""
        if parser not in SUPPORTED_PARSER_TYPES:
            # Check if the selected parser is supported.
            msg = "The selected parser must be either 'polars' of 'pandas'."
            raise ParserError(msg)

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

        # Define the environment model.
        # It provides a way to represent and track the association between variables and and operators.
        self.env: dict = {}
        self.parser: str = parser

        if self.parser == "polars":
            polars_env = {
                # Define the operations for the different operators.
                # Basic arithmethic operations
                self.NEGATE: lambda x: -x,
                self.ADD: lambda lst: reduce(lambda x, y: x + y, lst),
                self.SUB: lambda lst: reduce(lambda x, y: x - y, lst),
                self.MUL: lambda lst: reduce(lambda x, y: x * y, lst),
                self.DIV: lambda lst: reduce(lambda x, y: x / y, lst),
                # Exponentation and logarithms
                self.EXP: lambda x: pl.Expr.exp(x),
                self.LN: lambda x: pl.Expr.log(x),  # 30
                self.LB: lambda x: pl.Expr.log(x, 2),
                self.LG: lambda x: pl.Expr.log10(x),
                self.LOP: lambda x: pl.Expr.log1p(x),
                self.SQRT: lambda x: pl.Expr.sqrt(x),
                self.SQUARE: lambda x: x**2,
                self.POW: lambda lst: reduce(lambda x, y: x**y, lst),
                # Trigonometric operations
                self.ARCCOS: lambda x: pl.Expr.arccos(x),  #  x ∊ [-1, 1]
                self.ARCCOSH: lambda x: pl.Expr.arccosh(x),
                self.ARCSIN: lambda x: pl.Expr.arcsin(x),
                self.ARCSINH: lambda x: pl.Expr.arcsinh(x),
                self.ARCTAN: lambda x: pl.Expr.arctan(x),
                self.ARCTANH: lambda x: pl.Expr.arctanh(x),  # # x ∊ [-1, 1]
                self.COS: lambda x: pl.Expr.cos(x),
                self.COSH: lambda x: pl.Expr.cosh(x),
                self.SIN: lambda x: pl.Expr.sin(x),
                self.SINH: lambda x: pl.Expr.sinh(x),
                self.TAN: lambda x: pl.Expr.tan(x),
                self.TANH: lambda x: pl.Expr.tanh(x),
                # Comparison operations
                self.EQUAL: lambda lst: reduce(lambda x, y: x == y, lst),
                self.GREATER: lambda lst: reduce(lambda x, y: x > y, lst),
                self.GE: lambda lst: reduce(lambda x, y: x >= y, lst),
                self.LESS: lambda lst: reduce(lambda x, y: x < y, lst),
                self.LE: lambda lst: reduce(lambda x, y: x <= y, lst),
                self.NE: lambda lst: reduce(lambda x, y: x != y, lst),
                # Rounding operations
                self.ABS: lambda x: pl.Expr.abs(x),
                self.CEIL: lambda x: pl.Expr.ceil(x),  #
                self.FLOOR: lambda x: pl.Expr.floor(x),  #
                # Other operations
                self.RATIONAL: lambda lst: reduce(lambda x, y: x / y, lst),
                self.MAX: lambda lst: reduce(lambda x, y: pl.max(x, y), lst),
            }
            self.append(polars_env)
        elif parser == "pandas":
            pandas_env = {
                # Basic arithmethic operations
                self.NEGATE: lambda a: "(-%s)" % a,
                self.ADD: lambda lst: reduce(
                    # lambda x, y: "(%s +  %s)" % (x, y) if isinstance(x, str) or isinstance(y, str) else x + y,
                    lambda x, y: f"({x} +  {y})" if isinstance(x, str) or isinstance(y, str) else x + y,
                    lst,
                ),
                self.SUB: lambda lst: reduce(
                    # lambda x, y: "(%s -  %s)" % (x, y) if isinstance(x, str) or isinstance(y, str) else x - y,
                    lambda x, y: f"({x} -  {y})" if isinstance(x, str) or isinstance(y, str) else x - y,
                    lst,
                ),
                self.MUL: lambda lst: reduce(
                    # lambda x, y: "(%s *  %s)" % (x, y) if isinstance(x, str) or isinstance(y, str) else x * y,
                    lambda x, y: f"({x} *  {y})" if isinstance(x, str) or isinstance(y, str) else x * y,
                    lst,
                ),
                self.DIV: lambda lst: reduce(
                    # lambda x, y: "(%s /  %s)" % (x, y) if isinstance(x, str) or isinstance(y, str) else x / y,
                    lambda x, y: f"({x} /  {y})" if isinstance(x, str) or isinstance(y, str) else x / y,
                    lst,
                ),
                # Max function is not supported in pandas.eval()
                # self.MAX: lambda lst:reduce(lambda a,b:'where(%s,%s)'%(a,b), lst),
                # Exponentation and logarithms
                self.EXP: lambda a: "exp(%s)" % (a),
                self.LN: lambda a: "log(%s)" % (a),
                self.LB: lambda a: "log(%s,2)" % a,
                self.LG: lambda a: "log10(%s)" % (a),
                self.LOP: lambda a: "log1p(%s)" % (a),
                self.SQRT: lambda a: "(%s ** (1/2))" % a if isinstance(a, str) else a ** (1 / 2),
                self.SQUARE: lambda a: "(%s ** (2))" % a if isinstance(a, str) else a ** (2),
                # Trigonometric operations
                self.ARCCOS: lambda a: "arccos(%s)" % (a),
                self.ARCCOSH: lambda a: "arccosh(%s)" % (a),  # ∀x >= 1 ,
                self.ARCSIN: lambda a: "arcsin(%s)" % (a),  # ∀ x ∊ [ - 1 , 1 ]
                self.ARCSINH: lambda a: "arcsinh(%s)" % (a),
                self.ARCTAN: lambda a: "arctan(%s)" % (a),  # ∀ x ∊ ( - 1 , 1 )
                self.ARCTANH: lambda a: "arctanh(%s)" % (a),
                self.COS: lambda a: "cos(%s)" % (a),
                self.COSH: lambda a: "cosh(%s)" % (a),
                self.SIN: lambda a: "sin(%s)" % (a),
                self.SINH: lambda a: "sinh(%s)" % (a),
                self.TAN: lambda a: "tan(%s)" % (a),
                self.TANH: lambda a: "tanh(%s)" % (a),
                # Comparison operations
                self.EQUAL: lambda a, b: f"({a} == {b})",
                self.GREATER: lambda a, b: f"({a} >  {b})",
                self.GE: lambda a, b: f"({a} >= {b})",
                self.LESS: lambda a, b: f"({a} <  {b})",
                self.LE: lambda a, b: f"({a} <= {b})",
                self.NE: lambda a, b: f"({a} != {b})",
                # Rounding operations
                self.ABS: lambda a: "abs(%s)" % (a),
                # self.CEIL:              lambda a: 'ceil(%s)'%(a),   #Pandas.eval() not support ceil
                # self.FLOOR:             lambda a: 'floor(%s)'%(a),  #Pandas.eval() not support floor
                # Other operations
                self.RATIONAL: lambda lst: reduce(
                    # lambda x, y: "(%s /  %s)" % (x, y) if isinstance(x, str) or isinstance(y, str) else x / y,
                    lambda x, y: f"({x} /  {y})" if isinstance(x, str) or isinstance(y, str) else x / y,
                    lst,
                ),
                self.POW: lambda lst: reduce(
                    # lambda x, y: "(%s**  %s)" % (x, y) if isinstance(x, str) or isinstance(y, str) else x**y,
                    lambda x, y: f"({x}**{y})" if isinstance(x, str) or isinstance(y, str) else x**y,
                    lst,
                ),
            }
            self.append(pandas_env)
        else:
            msg = "The selected parser must be either 'polars' of 'pandas'."
            raise ParserError(msg)

        # Definition of keywords.
        # Whenever a keyword in the JSON file has been altered, change the name here.
        self.CONSTANTS: str = "constants"
        self.VARIABLES: str = "variables"
        self.EXTRA: str = "extra_func"
        self.OBJECTIVES: str = "objectives"
        self.CONSTRAINTS: str = "constraints"
        self.NAME: str = "shortname"
        self.VALUE: str = "value"
        self.FUNC: str = "func"
        self.LB: str = "lowerbound"
        self.UB: str = "upperbound"
        self.TYPE: str = "type"
        self.IV: str = "initialvalue"
        self.MAX: str = "max"

    def __get_parser_name__(self):
        """Return the currently defined parser."""
        return self.parser

    def append(self, d: dict):
        """Update the current env with the contents of a dictionary.

        Arguments:
        d (dict): dictionary used to update the current env.
        """
        self.env.update(d)

    def parse_sum(self, expr: list) -> list:
        """Convert Sum Operation into Add Operation.

        Arguments:
        expr (list): A list containing a Sum expression. Must contain the keywords
            'Triple' and 'Hold'.

        Returns:
        list: An Add expression derived from the Sum expression.

        Example:
        parse_sum(["Sum", ["Max", "g_i", 0], ["Triple", ["Hold", "i"], 1, 3]]) --->
        ["Add", ["Max", "g_1", 0],["Max", "g_2", 0],["Max", "g_3", 0] ]
        """
        len_of_sum_expr = 3
        if not expr or len(expr) != len_of_sum_expr:
            msg = "The Sum Expression List is either empty or wrong format"
            raise ParserError(msg)

        # Get the iterator
        logic_list = expr[2]
        if logic_list[0] != "Triple":
            msg = "The Control Operation is not recognizable, No keyword: Triple is not found "
            raise ParserError(msg)
        hold_list = logic_list[1]
        if hold_list[0] != "Hold":
            msg = "The Control Operation is not recognizable,No keyword:Hold is not found"
            raise ParserError(msg)
        holder: str = hold_list[1]
        start = logic_list[2]
        end = logic_list[3]

        # Replace the iterator in the expression with the holder
        expr = expr[1]
        pl_list = []
        for i in range(start, end + 1):
            it_name = "_" + holder
            new_it = "_" + str(i)
            left = replace_str(expr, it_name, new_it)
            pl_list.append(left)
        new_expr = ["Add"]
        for e in pl_list:
            new_expr.append(e)
        return new_expr

    def parse(self, expr: list):
        """Parses Polish notation and returns a polars expression.

        Arguments:
            expr (list): A list with a Polish notation expression that describes a, e.g.,
                ["Multiply", ["Sqrt", 2], "x2"]

        Raises:
            ParserError: If the type of the text neither str,list nor int,float, it will
            raise type error; If the operation in expr not found, it means we currently
            don't support such function operation.
        """
        if expr is None:
            return expr
        if isinstance(expr, str):
            # Handle variable symbols
            if expr in self.env:
                return self.parse(self.env[expr])
            if self.__get_parser_name__() == "polars":
                return pl.col(expr)
            if self.__get_parser_name__() == "pandas":
                return expr
            msg = "incorrect parser"
            raise ParserError(msg)
        if isinstance(expr, int | float):
            # Handle numeric constants
            return expr
        if isinstance(expr, list):
            # Handle function expressions
            op = expr[0]
            operands = expr[1:]
            length = len(operands)
            if op in self.env:
                if length == 1:
                    return self.env[op](self.parse(expr[1]))
                if length > 1:
                    return self.env[op](self.parse(e) for e in operands)
            if op == "Sum":
                new_expr = self.parse_sum(expr)
                return self.parse(new_expr)
            # raise error message:
            msg = f"I am sorry the operator:{op} is not found."
            raise ParserError(msg)

        # raise error message:
        text_type = type(expr)
        msg = f"The type of {text_type} is not found."
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
