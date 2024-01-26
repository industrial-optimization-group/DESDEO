import json

from pyparsing import (
    Word,
    Combine,
    Optional,
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
    Literal,
    one_of,
)

# Enable Packrat for better performance in recursive parsing
ParserElement.enablePackrat()

# Scope limiters
lparen = Suppress("(")
rparen = Suppress(")")

# Define operation symbols
signop = one_of("+ -")
multop = one_of("* /")
plusop = one_of("+ -")
expop = Literal("**")

# Define function symbols
variadric_func_names = Keyword("Max")
unary_func_names = Keyword("Cos") | Keyword("Sin")
reserved_keywords = variadric_func_names | unary_func_names


# Define parse actions
def parse_integer(tokens):
    """Parses a Literal integer into a Python int."""
    return int(tokens[0])


def parse_real(tokens):
    """Parses the Literal 'real' into a Python float."""
    return float("".join(tokens))


# Derfine operands
integer = Word(nums).add_parse_action(parse_integer)
real = Combine(Word(nums) + "." + Word(nums)).set_parse_action(parse_real)
variable = ~reserved_keywords + Word(alphas + "_", alphas + nums + "_")
operands = real | integer | variable

# Forward declarations of variadric and unary function calls
variadric_call = Forward()
unary_call = Forward()

# The parsed expressions are assumed to follow a standard infix syntax. The operands
# of the infix syntax can be either the literal 'operands' defined above (these are singletons),
# or either a varaidric function call or a unary function call. These latter two will be
# defined to be recursive.
infix_expn = infixNotation(
    operands | variadric_call | unary_call,
    [
        (signop, 1, opAssoc.RIGHT),
        (expop, 2, opAssoc.LEFT),
        (multop, 2, opAssoc.LEFT),
        (plusop, 2, opAssoc.LEFT),
    ],
)

# These are recursive definitions of the forward declarations of the two type of function calls.abs
# In essence, the resurcion continues until a singleton operand is encountered.
variadric_call <<= Group(variadric_func_names + lparen + Group(delimitedList(infix_expn)) + rparen)
unary_call <<= Group(unary_func_names + lparen + Group(infix_expn) + rparen)


test = " 123 + Max(Max(1+Max(2), Max(Max(1-1)))) + 3 + Max(3 - 1.123)"
test2 = "Cos(1+1) + 1 - Cos(Cos(1) + 2)"
test3 = "1 + Cos(2) + Cos(Max(1, 2)) - Max(Cos(1-2), 4)"
test4 = "-1 + -Max(-3 + (-3))"
expression2 = "Max(( f_1 - 3 ) / ( 4 - ( 1 - 0.001 )) , ( f_2 - 3 ) / ( 5 - ( 2 - 0.001 )) , ( f_3 - 3 ) / ( 6 - ( 3 - 0.001 ))) + 0.00001 * ( f_1 / ( 4 - ( 1 ) - 0.001 ) + f_2 / ( 5 - ( 2 ) - 0.001 ) + f_3 / ( 6 - ( 3 ) - 0.001 ))"


# Operator mapping to desired format
operator_mapping = {
    "+": "Add",
    "-": "Subtract",
    "--": "Negate",
    "*": "Multiply",
    "/": "Divide",
    "cos": "Cos",
    "Max": "Max",
}


def convert_to_mathjson(parsed):
    # Directly return the input if it is an integer or a float
    if isinstance(parsed, (int, float)):
        return parsed

    if len(parsed) == 1 and isinstance(parsed[0], (int, float, list)):
        return convert_to_mathjson(parsed[0])

    # Flatten binary operations like 1 + 2 + 3 into ["Add", 1, 2, 3]
    if len(parsed) >= 3 and isinstance(parsed[1], str):
        current_operator = operator_mapping.get(parsed[1], parsed[1])
        operands = [convert_to_mathjson(parsed[0])]

        i = 1
        while i < len(parsed) - 1:
            if isinstance(parsed[i], str) and i + 2 < len(parsed) and parsed[i] == parsed[i + 2]:
                operands.append(convert_to_mathjson(parsed[i + 1]))
                i += 2
            else:
                # If a different operation is encountered, process it separately
                return [current_operator] + operands + [convert_to_mathjson(parsed[i + 1 :])]

        return [current_operator] + operands

    # Handle unary operations and functions
    if isinstance(parsed[0], str):
        if parsed[0] in operator_mapping:
            operator = operator_mapping[parsed[0]]
            operands = [convert_to_mathjson(p) for p in parsed[1:]]
            return [operator] + operands
        else:
            operand = convert_to_mathjson(parsed[1])
            return [parsed[0], operand]

    # For lists and nested expressions
    return [convert_to_mathjson(part) for part in parsed]


def flatten_single_element_lists(lst):
    """Flatten lists that contain a single element."""
    if isinstance(lst, list):
        # If the list has only one element and that element is itself a list, flatten it
        if len(lst) == 1 and isinstance(lst[0], list):
            return flatten_single_element_lists(lst[0])
        else:
            # Otherwise, recursively apply this function to all elements
            return [flatten_single_element_lists(element) for element in lst]
    else:
        # If it's not a list, just return the element
        return lst


# Parse and convert
test = test4
parsed_expression = infix_expn.parseString(test, parseAll=True)
mathjson_format = flatten_single_element_lists(convert_to_mathjson(parsed_expression))


def pprint(mathjson_format, indent=0):
    # Start with an opening bracket
    print("[")

    for i, element in enumerate(mathjson_format):
        # Print a comma after the previous element, except for the first one
        if i > 0:
            print(",")

        # Print the element with indentation
        print("  " * (indent + 1) + json.dumps(element), end="")

    # Close the bracket with the correct indentation
    print("\n" + "  " * indent + "]", end="\n")


pprint(mathjson_format)
