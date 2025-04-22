"""Defines a parser to parse multiobjective optimziation problems defined in a JSON format."""

from collections.abc import Callable
from enum import Enum
from functools import reduce

import gurobipy as gp
import numpy as np
import polars as pl
import pyomo.environ as pyomo
import sympy as sp
from pyomo.core.expr.numeric_expr import MaxExpression as _PyomoMax
from pyomo.core.expr.numeric_expr import MinExpression as _PyomoMin

# Mathematical objects in gurobipy can take many types
gpexpression = gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr


class FormatEnum(str, Enum):
    """Enumerates the supported formats the JSON format may be parsed to."""

    polars = "polars"
    pyomo = "pyomo"
    sympy = "sympy"
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

        # Vector and matrix operations
        self.MATMUL: str = "MatMul"
        self.SUM: str = "Sum"
        self.RANDOM_ACCESS = "At"

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
        self.MIN: str = "Min"
        self.RATIONAL: str = "Rational"

        self.literals = int | float

        def to_expr(x: self.literals | pl.Expr):
            """Helper function to convert literals to polars expressions."""
            return pl.lit(x) if isinstance(x, self.literals) else x

        def to_sympy_expr(x):
            return sp.sympify(x, evaluate=False) if isinstance(x, self.literals) else x

        def gp_error():
            msg = "The gurobipy model format only supports linear and quadratic expressions."
            ParserError(msg)

        def _polars_reduce(ufunc, exprs):
            def _reduce_function(acc, x, ufunc=ufunc):
                acc_numpy = acc.to_numpy()
                x_numpy = x.to_numpy()

                if acc_numpy.shape == x_numpy.shape:
                    return pl.Series(values=ufunc(acc_numpy, x_numpy))

                expanded_shape = acc_numpy.shape + (1,) * (x_numpy.ndim - acc_numpy.ndim)

                return pl.Series(values=ufunc(acc_numpy.reshape(expanded_shape), x_numpy))

            return pl.reduce(function=_reduce_function, exprs=exprs)

        def _polars_reduce_unary(expr, ufunc):
            def _reduce_function(acc, _, ufunc=ufunc):
                return pl.Series(values=ufunc(acc.to_numpy()))

            return pl.reduce(function=_reduce_function, exprs=[expr, None])

        def _polars_reduce_matmul(*exprs):
            def _reduce_function(acc, x):
                acc = acc.to_numpy()
                x = x.to_numpy()

                if len(acc.shape) == 2 and len(x.shape) == 2:
                    # Row vectors, just return the dot product, polars does not handle
                    # "column" vectors anyway
                    return pl.Series(values=np.einsum("ij,ij->i", acc, x, optimize=True))

                # actual matrix product required
                return pl.Series(values=np.matmul(acc, x))

            return pl.reduce(function=_reduce_function, exprs=exprs)

        def _polars_summation(expr):
            """Polars matrix summation."""

            def _reduce_function(acc, _):
                acc_numpy = acc.to_numpy()
                return pl.Series(values=np.sum(acc_numpy, axis=tuple(range(1, acc_numpy.ndim))))

            return pl.reduce(function=_reduce_function, exprs=[expr, None])

        def _polars_random_access(expr, *indices):
            """Polars tensor random access."""
            for index in indices:
                expr = expr.arr.get(index - 1)  # 1 indexing assumed in JSON format

            return expr

        def _polars_generic_apply(a, b):
            pass

        polars_env = {
            # Define the operations for the different operators.
            # Basic arithmetic operations
            self.NEGATE: lambda x: _polars_reduce_unary(x, np.negative),
            self.ADD: lambda *args: _polars_reduce(np.add, args),
            self.SUB: lambda *args: _polars_reduce(np.subtract, args),
            self.MUL: lambda *args: _polars_reduce(np.multiply, args),
            self.DIV: lambda *args: _polars_reduce(np.divide, args),
            # Vector and matrix operations
            self.MATMUL: _polars_reduce_matmul,
            self.SUM: lambda x: _polars_summation(x),
            self.RANDOM_ACCESS: _polars_random_access,
            # Exponentiation and logarithms
            self.EXP: lambda x: _polars_reduce_unary(x, np.exp),
            self.LN: lambda x: _polars_reduce_unary(x, np.log),
            self.LB: lambda x: _polars_reduce_unary(x, np.log2),
            self.LG: lambda x: _polars_reduce_unary(x, np.log10),
            self.LOP: lambda x: _polars_reduce_unary(x, np.log1p),
            self.SQRT: lambda x: _polars_reduce_unary(x, np.sqrt),
            self.SQUARE: lambda x: _polars_reduce_unary(x, lambda y: np.power(y, 2)),
            self.POW: lambda *args: _polars_reduce(np.power, args),
            # Trigonometric operations
            self.ARCCOS: lambda x: _polars_reduce_unary(x, np.arccos),
            self.ARCCOSH: lambda x: _polars_reduce_unary(x, np.arccosh),
            self.ARCSIN: lambda x: _polars_reduce_unary(x, np.arcsin),
            self.ARCSINH: lambda x: _polars_reduce_unary(x, np.arcsinh),
            self.ARCTAN: lambda x: _polars_reduce_unary(x, np.arctan),
            self.ARCTANH: lambda x: _polars_reduce_unary(x, np.arctanh),
            self.COS: lambda x: _polars_reduce_unary(x, np.cos),
            self.COSH: lambda x: _polars_reduce_unary(x, np.cosh),
            self.SIN: lambda x: _polars_reduce_unary(x, np.sin),
            self.SINH: lambda x: _polars_reduce_unary(x, np.sinh),
            self.TAN: lambda x: _polars_reduce_unary(x, np.tan),
            self.TANH: lambda x: _polars_reduce_unary(x, np.tanh),
            # Rounding operations
            self.ABS: lambda x: _polars_reduce_unary(x, np.abs),
            self.CEIL: lambda x: _polars_reduce_unary(x, np.ceil),
            self.FLOOR: lambda x: _polars_reduce_unary(x, np.floor),
            # Other operations
            self.RATIONAL: lambda lst: reduce(lambda x, y: x / y, lst),  # Not supported
            self.MAX: lambda *args: reduce(lambda x, y: pl.max_horizontal(to_expr(x), to_expr(y)), args),
            self.MIN: lambda *args: reduce(lambda x, y: pl.min_horizontal(to_expr(x), to_expr(y)), args),
        }

        def _pyomo_negate(x):
            """Negates the given operand."""

            def _expr_negate_rule(x):
                def _inner(_, *indices):
                    return -x[indices]

                return _inner

            def _negate(x):
                # check if operand in indexed
                if hasattr(x, "index_set") and x.is_indexed():
                    # indexed, return new pyomo expression
                    expr = pyomo.Expression(x.index_set(), rule=_expr_negate_rule(x))
                    expr.construct()

                    return expr

                # not indexed, just regular negate
                return -x

            return _negate(x)

        def _pyomo_pow(base, exp):
            """Implements a power operator compatible with Pyomo expressions."""

            def _expr_pow_rule(base, exp):
                def _inner(_, *indices):
                    return base[indices] ** exp

                return _inner

            def _pow(base, exp=exp):
                # check if operand in indexed
                if hasattr(base, "index_set") and base.is_indexed():
                    # indexed, return new pyomo expression
                    expr = pyomo.Expression(base.index_set(), rule=_expr_pow_rule(base, exp))
                    expr.construct()

                    return expr

                # not indexed, just regular power
                return base**exp

            return _pow(base, exp)

        def _pyomo_unary(x, op):
            """Implements unary operators to work with indexed expressions."""

            def _expr_rule(x, op):
                def _inner(_, *indices, op=op):
                    return op(x[indices])

                return _inner

            def _op(x, op):
                # check if operand in indexed
                if hasattr(x, "index_set") and x.is_indexed():
                    # indexed, return new pyomo expression
                    expr = pyomo.Expression(x.index_set(), rule=_expr_rule(x, op))
                    expr.construct()

                    return expr

                # not indexed, just regular power
                return op(x)

            return _op(x, op)

        def _pyomo_addition(*args, subtraction=False):
            """Add (subtract) scalars or tensors to (from) each other."""

            def _expr_matrix_addition_rule(x, y, subtraction=subtraction):
                def _inner(_, *args):
                    return x[*args] + y[*args] if not subtraction else x[*args] - y[*args]

                return _inner

            def _expr_elementwise_with_single_indexed(indexed, not_indexed, subtraction=subtraction):
                def _inner(_, *indices):
                    return (indexed[indices] + not_indexed) if not subtraction else (indexed[indices] - not_indexed)

                return _inner

            def _add(x, y, subtraction=subtraction):
                # if both are indexed, try matrix addition
                if (hasattr(x, "index_set") and x.is_indexed()) and (hasattr(y, "index_set") and y.is_indexed()):
                    # try matrix addition
                    # check that the dimensions of x and y matches
                    if x.index_set().set_tuple != y.index_set().set_tuple:
                        msg = (
                            f"The dimensions of x {x.index_set().set_tuple} must match that"
                            f" of y {y.index_set().set_tuple} for matrix addition."
                        )
                        raise ParserError(msg)

                    expr = pyomo.Expression(
                        x.index_set(), rule=_expr_matrix_addition_rule(x, y, subtraction=subtraction)
                    )
                    expr.construct()

                    return expr

                # if neither is indexed, do normal addition
                if not (hasattr(x, "index_set") and x.is_indexed()) and not (
                    hasattr(y, "index_set") and y.is_indexed()
                ):
                    if not subtraction:
                        # try regular addition
                        return x + y
                    # try regular subtraction
                    return x - y

                # x is indexed, y is not
                if (hasattr(x, "index_set")) and x.is_indexed():
                    expr = pyomo.Expression(
                        x.index_set(), rule=_expr_elementwise_with_single_indexed(x, y, subtraction=subtraction)
                    )

                    expr.construct()
                    return expr

                # if y is indexed, x is not
                if (hasattr(y, "index_set")) and y.is_indexed():
                    expr = pyomo.Expression(
                        y.index_set(), rule=_expr_elementwise_with_single_indexed(y, x, subtraction=subtraction)
                    )

                    expr.construct()
                    return expr

                # if only one of the operands is indexed, then addition is not supported. Throw error.
                msg = "For addition, both operands must be either scalars or matrices with matching dimensions."
                raise ParserError(msg)

            return reduce(_add, args)

        def _pyomo_subtraction(*args):
            return _pyomo_addition(*args, subtraction=True)

        def _pyomo_multiply(*args, division=False):
            """Multiply tensor with a scalar."""

            def _expr_multiply_with_scalar_rule(scalar_value, to_multiply, division=division):
                def _inner(_, *indices):
                    return to_multiply[indices] * scalar_value if not division else to_multiply[indices] / scalar_value

                return _inner

            def _expr_matrix_multiply_rule(x, y, division=division):
                def _inner(_, *args):
                    return x[*args] * y[*args] if not division else x[*args] / y[*args]

                return _inner

            def _multiply(x, y, division=division):
                if not hasattr(x, "is_indexed") and not hasattr(y, "is_indexed"):
                    # x and y are scalars
                    return x * y if not division else x / y

                # check if x or y is scalar
                if (
                    hasattr(x, "is_indexed")
                    and x.is_indexed()
                    and x.dim() > 0
                    and (not hasattr(y, "is_indexed") or not y.is_indexed() or y.is_indexed() and y.dim() == 0)
                ):
                    # x is a tensor, y is scalar
                    expr = pyomo.Expression(
                        x.index_set(), rule=_expr_multiply_with_scalar_rule(y, x, division=division)
                    )
                    expr.construct()
                    return expr
                if (
                    hasattr(y, "is_indexed")
                    and y.is_indexed()
                    and y.dim() > 0
                    and (not hasattr(x, "is_indexed") or not x.is_indexed() or x.is_indexed() and x.dim() == 0)
                ):
                    # y is a tensor, x is scalar
                    expr = pyomo.Expression(
                        y.index_set(), rule=_expr_multiply_with_scalar_rule(x, y, division=division)
                    )
                    expr.construct()
                    return expr

                # check if both are indexed
                if hasattr(x, "index_set") and hasattr(y, "index_set"):
                    # both are indexed, neither is a scalar, check dims and sized, if match,
                    # multiply together element-wise
                    if x.index_set() != y.index_set():
                        msg = (
                            f"The dimensions of x {x.index_set().set_tuple} must match that"
                            f" of y {y.index_set().set_tuple} for element-wise matrix multiplication."
                        )
                        raise ParserError(msg)

                    expr = pyomo.Expression(x.index_set(), rule=_expr_matrix_multiply_rule(x, y, division=division))
                    expr.construct()

                    return expr

                # both are scalars
                return x * y if not division else x / y

            return reduce(_multiply, args)

        def _pyomo_division(*args):
            return _pyomo_multiply(*args, division=True)

        def _pyomo_matrix_multiplication(*args):
            """Multiply two matrices together."""

            def _expr_matmul_rule(mat_a, mat_b, j_indices):
                def _inner(_, i_index, k_index):
                    return sum(mat_a[i_index, j] * mat_b[j, k_index] for j in j_indices)

                return _inner

            def _matmul(mat_a, mat_b):
                if not (hasattr(mat_a, "is_indexed") and mat_a.is_indexed()) or not (
                    hasattr(mat_b, "is_indexed") and mat_b.is_indexed()
                ):
                    # either mat_a or mat_b is not tensor
                    msg = "Either mat_a or mat_b, or both, is not indexed. Cannot perform matrix multiplication."
                    raise ParserError(msg)

                # check for regular vectors, then do dot product
                if mat_a.dim() == 1 and mat_b.dim() == 1:
                    if (len_a := len(mat_a.index_set())) != (len_b := len(mat_b.index_set())):
                        msg = (
                            "For dot product, the sizes of the vectors must match."
                            f" Sizes mat_a = {len_a} and mat_b = {len_b}."
                        )
                        raise ParserError(msg)

                    return pyomo.sum_product(mat_a, mat_b, index=mat_a.index_set())

                # assuming mat_a has dimensions i,j; and mat_b j,k;
                # then the j dimension is squeezed and the i and k dimensions are kept.

                # check that we are dealing with matrices
                min_dimension = 2
                if (
                    not hasattr(mat_a.index_set(), "set_tuple") or len(mat_a.index_set().set_tuple) < min_dimension
                ) or (not hasattr(mat_b.index_set(), "set_tuple") and len(mat_b.index_set().set_tuple) < min_dimension):
                    msg = "Both mat_a and mat_b must have at least two dimensions."
                    raise ParserError(msg)

                # check that the outer dimensions (the one to be squeezed) matches
                if len(mat_a.index_set().set_tuple[-1]) != len(mat_b.index_set().set_tuple[0]):
                    msg = (
                        f"The last dimension size of mat_a ({mat_a.index_set().set_tuple[-1]}) must "
                        f"match the first dimension of mat_b ({mat_b.index_set().set_tuple[0]})"
                    )
                    raise ParserError(msg)

                expr = pyomo.Expression(
                    mat_a.index_set().set_tuple[0],
                    mat_b.index_set().set_tuple[1],
                    rule=_expr_matmul_rule(mat_a, mat_b, mat_a.index_set().set_tuple[1]),
                )
                expr.construct()

                return expr

            return reduce(_matmul, args)

        def _pyomo_summation(summand):
            """Sum an indexed Pyomo object."""
            return pyomo.sum_product(summand, index=summand.index_set())

        def _pyomo_random_access(indexed, *indices):
            return indexed[*indices]

        pyomo_env = {
            # Define the operations for the different operators.
            # Basic arithmetic operations
            self.NEGATE: _pyomo_negate,
            self.ADD: _pyomo_addition,
            self.SUB: _pyomo_subtraction,
            self.MUL: _pyomo_multiply,
            self.DIV: _pyomo_division,
            # Vector and matrix operations
            self.MATMUL: _pyomo_matrix_multiplication,
            self.SUM: _pyomo_summation,
            self.RANDOM_ACCESS: _pyomo_random_access,
            # Exponentiation and logarithms
            self.EXP: lambda x: _pyomo_unary(x, pyomo.exp),
            self.LN: lambda x: _pyomo_unary(x, pyomo.log),
            self.LB: lambda x: _pyomo_unary(
                x, lambda x: pyomo.log(x) / pyomo.log(2)
            ),  # change of base, pyomo has no log2
            self.LG: lambda x: _pyomo_unary(x, pyomo.log10),
            self.LOP: lambda x: _pyomo_unary(x, lambda x: pyomo.log(x + 1)),
            self.SQRT: lambda x: _pyomo_unary(x, pyomo.sqrt),
            self.SQUARE: lambda x: _pyomo_pow(x, 2),
            self.POW: lambda x, y: _pyomo_pow(x, y),
            # Trigonometric operations
            self.ARCCOS: lambda x: _pyomo_unary(x, pyomo.acos),
            self.ARCCOSH: lambda x: _pyomo_unary(x, pyomo.acosh),
            self.ARCSIN: lambda x: _pyomo_unary(x, pyomo.asin),
            self.ARCSINH: lambda x: _pyomo_unary(x, pyomo.asinh),
            self.ARCTAN: lambda x: _pyomo_unary(x, pyomo.atan),
            self.ARCTANH: lambda x: _pyomo_unary(x, pyomo.atanh),
            self.COS: lambda x: _pyomo_unary(x, pyomo.cos),
            self.COSH: lambda x: _pyomo_unary(x, pyomo.cosh),
            self.SIN: lambda x: _pyomo_unary(x, pyomo.sin),
            self.SINH: lambda x: _pyomo_unary(x, pyomo.sinh),
            self.TAN: lambda x: _pyomo_unary(x, pyomo.tan),
            self.TANH: lambda x: _pyomo_unary(x, pyomo.tanh),
            # Rounding operations
            self.ABS: lambda x: _pyomo_unary(x, abs),
            self.CEIL: lambda x: _pyomo_unary(x, pyomo.ceil),
            self.FLOOR: lambda x: _pyomo_unary(x, pyomo.floor),
            # Other operations
            self.RATIONAL: lambda lst: reduce(lambda x, y: x / y, lst),  # not supported
            # probably a better idea to reformulate expressions with a max when utilized with pyomo
            # self.MAX: lambda *args: reduce(lambda x, y: _PyomoMax((x, y)), args),
            self.MAX: lambda *args: _PyomoMax(args),
            self.MIN: lambda *args: _PyomoMin(args),
        }

        def _sympy_matmul(*args):
            """Sympy matrix multiplication."""
            msg = (
                "Matrix multiplication '@' has not been implemented for the Sympy parser yet."
                " Feel free to contribute!"
            )
            raise NotImplementedError(msg)

        def _sympy_summation(summand):
            """Sympy matrix summation."""
            msg = (
                "Matrix summation 'Sum' has not been implemented for the Sympy parser yet." " Feel free to contribute!"
            )
            raise NotImplementedError(msg)

        def _sympy_random_access(*args):
            msg = (
                "Tensor random access with 'At' has not been implemented for the Sympy parser yet. "
                "Feel free to contribute!"
            )
            raise NotImplementedError(msg)

        sympy_env = {
            # Basic arithmetic operations
            self.NEGATE: lambda x: -to_sympy_expr(x),
            self.ADD: lambda *args: reduce(lambda x, y: to_sympy_expr(x) + to_sympy_expr(y), args),
            self.SUB: lambda *args: reduce(lambda x, y: to_sympy_expr(x) - to_sympy_expr(y), args),
            self.MUL: lambda *args: reduce(lambda x, y: to_sympy_expr(x) * to_sympy_expr(y), args),
            self.DIV: lambda *args: reduce(lambda x, y: to_sympy_expr(x) / to_sympy_expr(y), args),
            # Vector and matrix operations
            self.MATMUL: _sympy_matmul,
            self.SUM: _sympy_summation,
            self.RANDOM_ACCESS: _sympy_random_access,
            # Exponentiation and logarithms
            self.EXP: lambda x: sp.exp(to_sympy_expr(x)),
            self.LN: lambda x: sp.log(to_sympy_expr(x)),
            self.LB: lambda x: sp.log(to_sympy_expr(x), 2),
            self.LG: lambda x: sp.log(to_sympy_expr(x), 10),
            self.LOP: lambda x: sp.log(1 + to_sympy_expr(x)),
            self.SQRT: lambda x: sp.sqrt(to_sympy_expr(x)),
            self.SQUARE: lambda x: to_sympy_expr(x) ** 2,
            self.POW: lambda x, y: to_sympy_expr(x) ** to_sympy_expr(y),
            # Trigonometric operations
            self.SIN: lambda x: sp.sin(to_sympy_expr(x)),
            self.COS: lambda x: sp.cos(to_sympy_expr(x)),
            self.TAN: lambda x: sp.tan(to_sympy_expr(x)),
            self.ARCSIN: lambda x: sp.asin(to_sympy_expr(x)),
            self.ARCCOS: lambda x: sp.acos(to_sympy_expr(x)),
            self.ARCTAN: lambda x: sp.atan(to_sympy_expr(x)),
            # Hyperbolic functions
            self.SINH: lambda x: sp.sinh(to_sympy_expr(x)),
            self.COSH: lambda x: sp.cosh(to_sympy_expr(x)),
            self.TANH: lambda x: sp.tanh(to_sympy_expr(x)),
            self.ARCSINH: lambda x: sp.asinh(to_sympy_expr(x)),
            self.ARCCOSH: lambda x: sp.acosh(to_sympy_expr(x)),
            self.ARCTANH: lambda x: sp.atanh(to_sympy_expr(x)),
            # Other
            self.ABS: lambda x: sp.Abs(to_sympy_expr(x)),
            self.CEIL: lambda x: sp.ceiling(to_sympy_expr(x)),
            self.FLOOR: lambda x: sp.floor(to_sympy_expr(x)),
            # Note: Max and Min in sympy take any number of arguments
            self.MAX: lambda *args: sp.Max(*args),
            self.MIN: lambda *args: sp.Min(*args),
            # Rational numbers, for now assuming two-element list for numerator and denominator
            self.RATIONAL: lambda x, y: sp.Rational(x, y),
        }

        def _gurobipy_matmul(*args):
            """Gurobipy matrix multiplication."""

            def _matmul(a, b):
                if isinstance(a, list):
                    a = np.array(a)
                if isinstance(b, list):
                    b = np.array(b)
                if len(np.shape(a @ b)) == 1:
                    return a @ b
                return (a @ b).sum()

            return reduce(_matmul, args)
            msg = (
                "Matrix multiplication '@' has not been implemented for the Gurobipy parser yet."
                " Feel free to contribute!"
            )
            raise NotImplementedError(msg)

        def _gurobipy_summation(summand):
            """Gurobipy matrix summation."""

            def _sum(summand):
                if isinstance(summand, list):
                    summand = np.array(summand)
                return summand.sum()

            return _sum(summand)
            msg = (
                "Matrix summation 'Sum' has not been implemented for the Gurobipy parser yet."
                " Feel free to contribute!"
            )
            raise NotImplementedError(msg)

        def _gurobipy_random_access(*args):
            msg = (
                "Tensor random access with 'At' has not been implemented for the Gurobipy parser yet. "
                "Feel free to contribute!"
            )
            raise NotImplementedError(msg)

        gurobipy_env = {
            # Define the operations for the different operators.
            # Basic arithmetic operations
            self.NEGATE: lambda x: -x,
            self.ADD: lambda *args: reduce(lambda x, y: x + y, args),
            self.SUB: lambda *args: reduce(lambda x, y: x - y, args),
            self.MUL: lambda *args: reduce(lambda x, y: x * y, args),
            self.DIV: lambda *args: reduce(lambda x, y: x / y, args),
            # Vector and matrix operations
            self.MATMUL: _gurobipy_matmul,
            self.SUM: _gurobipy_summation,
            self.RANDOM_ACCESS: _gurobipy_random_access,
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
            self.POW: lambda x, y: x**y,  # this will likely cause an error at some point for most y
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
            self.MAX: lambda *args: gp.max_(args),  ## OBS! max and min are unsupported, but left here for reasons
            self.MIN: lambda *args: gp.min_(args),
        }

        match to_format:
            case FormatEnum.polars:
                self.env = polars_env
                self.parse = self._parse_to_polars
            case FormatEnum.pyomo:
                self.env = pyomo_env
                self.parse = self._parse_to_pyomo
            case FormatEnum.sympy:
                self.env = sympy_env
                self.parse = self._parse_to_sympy
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

        Raises:
            ParserError: when a unsupported operator type is encountered.

        Returns:
            pl.Expr: A polars expression that may be evaluated further.

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
            if len(expr) == 1 and isinstance(expr[0], str | self.literals):
                # Terminal case, single symbol expression or literal
                if isinstance(expr[0], str):
                    return pl.col(expr)
                # just a literal
                return pl.lit(expr[0])

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

    def _parse_to_pyomo(
        self, expr: list | str | int | float | pyomo.Expression, model: pyomo.Model
    ) -> pyomo.Expression:
        """Parses the MathJSON format recursively into a Pyomo expression.

        Args:
            expr (list | str | int | float): a list with a Polish notation expression that describes a, e.g.,
                ["Multiply", ["Sqrt", 2], "x2"]
            model (pyomo.Model): a pyomo model with the symbols defined appearing in the expression.
                E.g., "x2" -> model.x2 must be defined.

        Raises:
            ParserError: when a unsupported operator type is encountered.

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
            if len(expr) == 1 and isinstance(expr[0], str | self.literals):
                # Terminal case, single symbol expression or literal
                if isinstance(expr[0], str):
                    return getattr(model, expr[0])
                # just a literal
                return pyomo.Expression(expr=expr[0])

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

    def _parse_to_sympy(self, expr: list | str | int | float | sp.Basic) -> sp.Basic:
        """Parse the MathJSON format recursively into a sympy expression.

        Args:
            expr (list | str | int | float | sp.Basic): base call should be a list in Polish
                notation representing a mathematical expression. Recursion calls can be of various
                types.

        Raises:
            ParserError: when a unsupported operator type is encountered.

        Returns:
            sp.Basic: a sympy expression that represents the original mathematical
                expression in the supplied MathJSON format.
        """
        if isinstance(expr, sp.Basic):
            # Terminal case: sympy expression
            return expr
        if isinstance(expr, str):
            # Terminal case: represents a variable
            return sp.sympify(expr, evaluate=False)
        if isinstance(expr, self.literals):
            # Terminal case: numeric literal
            return sp.sympify(expr, evaluate=False)

        if isinstance(expr, list):
            if len(expr) == 1 and isinstance(expr[0], str | self.literals):
                # Terminal case, single symbol expression or literal
                return sp.sympify(expr[0], evaluate=False)

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

    def _parse_to_gurobipy(
        self, expr: list | str | int | float, callback: Callable[[str], gpexpression | int | float]
    ) -> gpexpression | int | float:
        """Parses the MathJSON format recursively into a gurobipy expression.

        Gurobi only fundamentally supports linear and quadratic expressions, and this parser
        does not check that the inputs are valid. If you try to input something else, you will
        likely encounter an error at some point.

        Args:
            expr (list | str | int | float): a list with a Polish notation expression that describes a, e.g.,
                ["Multiply", ["Sqrt", 2], "x2"]
            callback (Callable): A function that can return a gurobipy expression associated with the
                correct model when called with symbol str.

        Returns:
            Returns a gurobipy expression (that can belong into one of multiple types) equivalent to the original
            expressions.
            All possible output types should be supported as parts of gurobipy constraints. gurobipy.GenExpr at
            least isn't supported as an objective function.
        """
        if isinstance(expr, gpexpression):
            # Terminal case: gurobipy expression
            return expr
        if isinstance(expr, str):
            # Terminal case: str expression, represent a variable or expression
            return callback(expr)
        if isinstance(expr, self.literals):
            # Terminal case: numeric literal
            return expr

        if isinstance(expr, list):
            # Extract the operation name
            if isinstance(expr[0], str) and expr[0] in self.env:
                op_name = expr[0]
                # Parse the operands
                operands = [self._parse_to_gurobipy(e, callback) for e in expr[1:]]

                while isinstance(operands, list) and len(operands) == 1:
                    # if the operands have redundant brackets, remove them
                    operands = operands[0]

                if isinstance(operands, list):
                    return self.env[op_name](*operands)

                return self.env[op_name](operands)

            # else, assume the list contents are parseable expressions
            return [self._parse_to_gurobipy(e, callback) for e in expr]

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
        if target == lst:
            if isinstance(sub, str):
                return lst.replace(target, sub)
            return sub
        return lst
    return lst
