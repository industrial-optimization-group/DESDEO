"""Defines parsers for parsing mathematical expression in an infix format and expressed as string.

Currently, mostly parses to MathJSON, e.g., "n / (1 + n)" -> ['Divide', 'n', ['Add', 1, 'n']].
"""

from typing import ClassVar

from pyparsing import (
    DelimitedList,
    Forward,
    Group,
    Literal,
    OpAssoc,
    ParserElement,
    Regex,
    Suppress,
    infix_notation,
    one_of,
    pyparsing_common,
)

# Enable Packrat for better performance in recursive parsing
ParserElement.enablePackrat(None)


class InfixExpressionParser:
    """A class for defining infix notation parsers."""

    SUPPORTED_TARGETS: ClassVar[list] = ["MathJSON"]

    # Supported infix binary operators, i.e., '1+1'. The key is the notation of the operator in infix format,
    # and the value the notation in parsed format.
    BINARY_OPERATORS: ClassVar[dict] = {
        "+": "Add",
        "-": "Subtract",
        "*": "Multiply",
        "/": "Divide",
        "**": "Power",
        "@": "MatMul",
    }

    # Supported infix unary operators, i.e., 'Cos(90)'. The key is the notation of the operator in infix format,
    # and the value the notation in parsed format.
    UNARY_OPERATORS: ClassVar[dict] = {
        "Cos": "Cos",
        "Sin": "Sin",
        "Tan": "Tan",
        "Exp": "Exp",
        "Ln": "Ln",
        "Lb": "Lb",
        "Lg": "Lg",
        "LogOnePlus": "LogOnePlus",
        "Sqrt": "Sqrt",
        "Square": "Square",
        "Abs": "Abs",
        "Ceil": "Ceil",
        "Floor": "Floor",
        "Arccos": "Arccos",
        "Arccosh": "Arccosh",
        "Arcsin": "Arcsin",
        "Arcsinh": "Arcsinh",
        "Arctan": "Arctan",
        "Arctanh": "Arctanh",
        "Cosh": "Cosh",
        "Sinh": "Sinh",
        "Tanh": "Tanh",
        "Rational": "Rational",
        "-": "Negate",
        "Sum": "Sum",
    }

    # Supported infix variadic operators (operators that take one or more comma separated arguments),
    # i.e., 'Max(1,2, Cos(3)). The key is the notation of the operator in infix format,
    # and the value the notation in parsed format.
    VARIADIC_OPERATORS: ClassVar[dict] = {"Max": "Max"}

    def __init__(self, target="MathJSON"):
        """A parser for infix notation, e.g., the huma readable way of notating mathematical expressions.

        The parser can parse infix notation stored in a string to different formats. For instance,
        "Cos(2 + f_1) - 7.2 + Max(f_2, -f_3)" is first parsed to the list:
        ['Cos', [[2, '+', 'f_1']]], '-', 7.2, '+', ['Max', ['f_2', ['-', 'f_3']]. Then, if parsed to
        the MathJSON format, it will be parsed to the list:
        [
            [["Subtract", ["Cos", ["Add", 2, "f_1"]], ["Add", 7.2, ["Max", ["f_2", ["Negate", "f_3"]]]]]]
        ].


        Args:
            target (str, optional): The target format to parse an infix expression to.
                Currently only "MathJSON" is supported. Defaults to "MathJSON".
        """
        if target not in InfixExpressionParser.SUPPORTED_TARGETS:
            msg = f"The target '{target} is not supported. Should be one of {InfixExpressionParser.SUPPORTED_TARGETS}"
            raise ValueError(msg)
        self.target = target

        # Scope limiters
        lparen = Suppress("(")
        rparen = Suppress(")")

        # Define keywords (Note that binary operators must be defined manually)
        symbols_variadic = set(InfixExpressionParser.VARIADIC_OPERATORS)
        symbols_unary = set(InfixExpressionParser.UNARY_OPERATORS)

        # Define binary operation symbols (this is the manual part)
        # If new binary operators are to be added, they must be defined here.
        signop = one_of("+ -")
        multop = one_of("* / . @")
        plusop = one_of("+ -")
        expop = Literal("**")

        # Dynamically create Keyword objects for variadric functions
        variadic_pattern = r"\b(" + f"{'|'.join([*symbols_variadic])}" + r")\b"
        variadic_func_names = Regex(variadic_pattern)

        # Dynamically create Keyword objects for unary functions
        # unary_func_names = reduce(or_, (Keyword(k) for k in symbols_unary))
        unary_pattern = r"\b(" + f"{'|'.join([*symbols_unary])}" + r")\b"
        unary_func_names = Regex(unary_pattern)

        # Define operands
        integer = pyparsing_common.integer

        # Scientific notation
        scientific = pyparsing_common.sci_real

        # Complete regex pattern with exclusions and identifier pattern
        exclude = f"{'|'.join([*symbols_variadic, *symbols_unary])}"
        pattern = r"(?!\b(" + exclude + r")\b)(\b[a-zA-Z_][a-zA-Z0-9_]*\b)"
        variable = Regex(pattern)

        operands = variable | scientific | integer

        # Forward declarations of variadric and unary function calls
        variadic_call = Forward()
        unary_call = Forward()

        # The parsed expressions are assumed to follow a standard infix syntax. The operands
        # of the infix syntax can be either the literal 'operands' defined above (these are singletons),
        # or either a variadic function call or a unary function call. These latter two will be
        # defined to be recursive.
        #
        # Note that the order of the operators in the second argument (the list) of infixNotation matters!
        # The operation with the highest precedence is listed first.
        infix_expn = infix_notation(
            operands | variadic_call | unary_call,
            [
                (expop, 2, OpAssoc.LEFT),
                (signop, 1, OpAssoc.RIGHT),
                (multop, 2, OpAssoc.LEFT),
                (plusop, 2, OpAssoc.LEFT),
            ],
        )

        # These are recursive definitions of the forward declarations of the two type of function calls.
        # In essence, the recursion continues until a singleton operand is encountered.
        variadic_call <<= Group(variadic_func_names + lparen + Group(DelimitedList(infix_expn)) + rparen)
        unary_call <<= Group(unary_func_names + lparen + Group(infix_expn) + rparen)

        self.expn = infix_expn

        # The infix operations do not need to be in this list because they are handled by infixNotation() above.
        # If new binary operations are to be added, they must be updated in the infixNotation() call (the list).
        self.reserved_symbols: set[str] = symbols_unary | symbols_variadic

        # It is assumed that the dicts in the three class variables have unique keys.
        self.operator_mapping = {
            **InfixExpressionParser.BINARY_OPERATORS,
            **InfixExpressionParser.UNARY_OPERATORS,
            **InfixExpressionParser.VARIADIC_OPERATORS,
        }

        if self.target == "MathJSON":
            self.pre_parse = self._pre_parse
            self.parse_to_target = self._to_math_json
        else:
            self.pre_parse = None
            self.parse_to_target = None

    def _pre_parse(self, str_expr: str):
        return self.expn.parse_string(str_expr, parse_all=True)

    def _is_number_or_variable(self, c):
        return isinstance(c, int | float) or (isinstance(c, str) and c not in self.reserved_symbols)

    def _to_math_json(self, parsed: list | str) -> list:
        """Converts a list of expressions into a MathJSON compliant format.

        The conversion happens recursively. Each list of recursed until a terminal character is reached.
        Terminal characters are integers (int), floating point numbers (float), or non-keyword strings (str).
        Keyword strings are reserved for operations, such as 'Cos' or 'Max'.

        Args:
            parsed (list): A list possibly containing other lists. Represents a mathematical expression.

        Returns:
            list: A list representing a mathematical expression in a MathJSON compliant format.
        """
        # Directly return the input if it is an integer or a float
        if self._is_number_or_variable(parsed):
            return parsed

        # Flatten binary operations like 1 + 2 + 3 into ["Add", 1, 2, 3]
        # Last check is to make sure that in cases like ["Max", ["x", "y", ...]] the 'y' is not confused to
        # be an operator.
        num_binary_elements = 3
        if (
            len(parsed) >= num_binary_elements
            and isinstance(parsed[1], str)
            and parsed[1] in InfixExpressionParser.BINARY_OPERATORS
        ):
            # Initialize the list to collect operands for the current operation
            operands = []

            # Check if the first operation is subtraction and handle it specially
            if parsed[1] == "-":
                current_operator = "Add"
                # Negate the operand immediately following the subtraction operator
                operands.append(self._to_math_json(parsed[0]))  # Add the first operand
                operands.append(["Negate", self._to_math_json(parsed[2])])  # Negate the second operand
                start_index = 3  # Start processing the rest of the expression from the next element
            else:
                current_operator = self.operator_mapping[parsed[1]]
                operands.append(self._to_math_json(parsed[0]))  # Add the first operand as is
                start_index = 1  # Start processing the rest of the expression from the second element

            i = start_index

            while i < len(parsed) - 1:
                op = parsed[i]

                if isinstance(parsed[i], str) and i + 2 < len(parsed) and parsed[i] == parsed[i + 2]:
                    next_operand = self._to_math_json(parsed[i + 1])  # Next operand

                    if op == "-":  # If subtraction, negate and add
                        operands.append(["Negate", next_operand])
                    else:
                        operands.append(next_operand)
                    i += 2
                else:
                    # Handle last expression, negate if needed.
                    if op == "-":
                        return [[current_operator, *operands, ["Negate", *self._to_math_json(parsed[i + 1 :])]]]

                    return [[current_operator, *operands, *self._to_math_json(parsed[i + 1 :])]]

            return [[current_operator, *operands]]

            """
            # Process the rest of the expression
            for i in range(start_index, len(parsed), 2):
                op = parsed[i]  # Operator
                next_operand = self._to_math_json(parsed[i + 1])  # Next operand

                if op == "-":  # If subtraction, negate and add
                    operands.append(["Negate", next_operand])
                elif op == "+":  # If addition, just add
                    operands.append(next_operand)
                else:  # For other operators, use the mapping
                    current_operator = self.operator_mapping[op]
                    operands.append(next_operand)

            # Return the operation with operands correctly merged into a single operation
            return [current_operator] + operands
            """

        # Handle unary operations and functions
        if isinstance(parsed[0], str) and parsed[0] in self.reserved_symbols:
            if parsed[0] in self.operator_mapping:
                operator = self.operator_mapping.get(parsed[0], parsed[0])
                operands = [self._to_math_json(p) for p in parsed[1:]]

                while isinstance(operands, list) and len(operands) == 1 and isinstance(operands[0], list):
                    operands = operands[0]

                return [operator, [*operands]]

            operand = self._to_math_json(parsed[1])

            return [parsed[0], operand]

        # For lists and nested expressions
        return [self._to_math_json(part) for part in parsed]

    def _remove_extra_brackets(self, lst: list) -> list:
        """Removes recursively extra brackets from a nested list that may have been left when parsing an expression.

        Args:
            lst (list): A (nested) list that needs extra bracket removal.

        Returns:
            list: A list with extra brackets removed.
        """
        # Base case: if it's not a list, just return the item itself
        if not isinstance(lst, list):
            return lst

        # If the list has only one element and that element is a list, unpack it
        if len(lst) == 1 and (isinstance(lst[0], list) or self._is_number_or_variable(lst[0])):
            return self._remove_extra_brackets(lst[0])

        # Otherwise, process each element of the list
        return [self._remove_extra_brackets(item) for item in lst]

    def parse(self, str_expr: str) -> list:
        """The method to call when parsing an infix expression in represented by a string.

        Args:
            str_expr (str): A string expression to be parsed.

        Returns:
            list: A list representing the parsed expression.
        """
        return self._remove_extra_brackets(self.parse_to_target(self.pre_parse(str_expr)))


if __name__ == "__main__":
    # Parse and convert
    test = "(x_1 - c_2) ** 2 + x_2 ** 2 - 25"

    ohh_no = "['Add', ['Negate', ['Square', ['Subtract', 'x_1', 8]]], ['Negate', ['Square', ['Add', 'x_2', 3]]], 7.7]"

    to_json_parser = InfixExpressionParser(target="MathJSON")

    parsed_expression = to_json_parser.parse(test)

    print(f"Expresion:\n{test}")
    print(f"Parsed:\n{to_json_parser._pre_parse(test)}")
    print(f"MathJSON:\n{parsed_expression}")
