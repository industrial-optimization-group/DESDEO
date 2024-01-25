"""Minimal example of parsing infix expressions to the MathJSON format."""
from pyparsing import Word, alphas, nums, Group, Forward, infixNotation, opAssoc, ParserElement, delimitedList

# Define grammar
ParserElement.enablePackrat()

# Basic elements
integer = Word(nums)
variable = Word(alphas, exact=1)
operand = integer | variable

# Define the operator precedence
expn = Forward()
atom = operand | Group("(" + expn + ")")

# Define the operation list
ops = [
    ("cos", 1, opAssoc.RIGHT),
    ("*", 2, opAssoc.LEFT),
    ("/", 2, opAssoc.LEFT),
    ("+", 2, opAssoc.LEFT),
    ("-", 2, opAssoc.LEFT),
]

# Define max expression
max_expr = Forward()
max_expr << Group("Max" + "(" + delimitedList(expn) + ")")

# Define the expression
expn <<= max_expr | infixNotation(atom, ops)

# Operator mapping to desired format
operator_mapping = {"+": "Add", "-": "Subtract", "*": "Multiply", "/": "Divide", "cos": "Cos", "Max": "Max"}


# Example expression
expression = "(a + b) * y / x - cos(k)"
expression2 = "cos(( f_1 - 3 ) / ( 4 - ( 1 - 1e-06 )) , ( f_2 - 3 ) / ( 5 - ( 2 - 1e-06 )) , ( f_3 - 3 ) / ( 6 - ( 3 - 1e-06 ))) + 1e-09 * ( f_1 / ( 4 - ( 1 ) - 1e-06 ) f_2 / ( 5 - ( 2 ) - 1e-06 ) f_3 / ( 6 - ( 3 ) - 1e-06 ))"


def convert_to_mathjson(parsed):
    # If the parsed object is a string, return it as-is
    if isinstance(parsed, str):
        return parsed

    # Check and convert ParseResults to a regular list if needed
    if not isinstance(parsed, list):
        parsed = parsed.asList()

    # Filter out parentheses
    parsed = [p for p in parsed if p not in ["(", ")"]]

    if len(parsed) == 1:
        # Unpack single-element lists
        return convert_to_mathjson(parsed[0])

    if isinstance(parsed[0], str) and len(parsed) == 2:
        # Unary operator case (e.g., ["cos", ...])
        operator = operator_mapping.get(parsed[0], parsed[0])
        operand = convert_to_mathjson(parsed[1])
        return [operator, operand]

    if isinstance(parsed[1], str) and len(parsed) == 3:
        # Binary operator case (e.g., [..., "+", ...])
        operand1 = convert_to_mathjson(parsed[0])
        operator = operator_mapping.get(parsed[1], parsed[1])
        operand2 = convert_to_mathjson(parsed[2])
        return [operator, operand1, operand2]

    # For more complex or nested expressions
    result = []
    for part in parsed:
        result.append(convert_to_mathjson(part))
    return result


# Parse and convert
parsed_expression = expn.parseString(expression, parseAll=True)
mathjson_format = convert_to_mathjson(parsed_expression)

parsed_expression2 = expn.parseString(expression2, parseAll=True)
mathjson_format2 = convert_to_mathjson(parsed_expression2)

print(mathjson_format)
print(mathjson_format2)
