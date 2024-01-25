from pyparsing import (
    Word,
    alphas,
    nums,
    Group,
    Forward,
    infixNotation,
    opAssoc,
    ParserElement,
    delimitedList,
    Suppress,
    Keyword,
)


# Define grammar
ParserElement.enablePackrat()

# Basic elements
number = Word(nums + ".")
variable = Word(alphas + "_", alphas + nums + "_")
max_func_name = Keyword("Max")
lparen = Suppress("(")
rparen = Suppress(")")

operands = number

function_call = Forward()

# args = operands | function_call | infix_operation

infix_expr = infixNotation(
    operands | function_call,
    [
        ("cos", 1, opAssoc.RIGHT),
        ("*", 2, opAssoc.LEFT),
        ("/", 2, opAssoc.LEFT),
        ("+", 2, opAssoc.LEFT),
        ("-", 2, opAssoc.LEFT),
    ],
)


function_call <<= Group(max_func_name + lparen + Group(delimitedList(function_call | operands)) + rparen) | infix_expr


test = "1.123+ 1 + Max(1,2 + Max(1,2))"


res = function_call.parse_string(test)
print(res)


exit()

# Define function call
function_name = Word(alphas)
function_args = delimitedList(integer | variable)
function_call = Group(function_name + "(" + Group(function_args) + ")")

# Update atom to include function calls
atom = operand | function_call | Group("(" + Forward() + ")")

# Define the operator precedence
expn = Forward()
atom = operand | Group("(" + expn + ")")

# Define the operator precedence
expn = Forward()
expn <<= infixNotation(
    atom,
    [
        ("cos", 1, opAssoc.RIGHT),
        ("*", 2, opAssoc.LEFT),
        ("/", 2, opAssoc.LEFT),
        ("+", 2, opAssoc.LEFT),
        ("-", 2, opAssoc.LEFT),
    ],
)

# Operator mapping to desired format
operator_mapping = {"+": "Add", "-": "Subtract", "*": "Multiply", "/": "Divide", "cos": "Cos", "Max": "Max"}

# Example expression
expression2 = "Max(( f_1 - 3 ) / ( 4 - ( 1 - 0.001 )) , ( f_2 - 3 ) / ( 5 - ( 2 - 0.001 )) , ( f_3 - 3 ) / ( 6 - ( 3 - 0.001 ))) + 0.00001 * ( f_1 / ( 4 - ( 1 ) - 0.001 ) + f_2 / ( 5 - ( 2 ) - 0.001 ) + f_3 / ( 6 - ( 3 ) - 0.001 ))"


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

    # Handle 'Max' and other possible functions
    if parsed[0] in operator_mapping and isinstance(parsed[1], list):
        operator = operator_mapping[parsed[0]]
        operands = [convert_to_mathjson(p) for p in parsed[1]]
        return [operator] + operands

    # For more complex or nested expressions
    result = []
    for part in parsed:
        result.append(convert_to_mathjson(part))
    return result


# Parse and convert
parsed_expression2 = expn.parseString(expression2, parseAll=True)
mathjson_format2 = convert_to_mathjson(parsed_expression2)

print(mathjson_format2)
