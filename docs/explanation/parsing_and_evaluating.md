# Parsing and evaluating problems

In DESDEO, the problem format (c.f., section [The Problem Format](./problem_format.md))
can be parsed into other formats and evaluated. The purpose of evaluating is to
allow different solvers, discussed in section [Solvers](./solvers.md), to solve
the modeled multiobjective optimization problem. 

Here, we will first discuss the parsing and the parses found in DESDEO in
the section [Parsing and parsers](#parsing-and-parsers). Then, we will discuss the
solvers available in DESDEO for solving multiobjective optimization
problems in the section [Evaluating and evaluators](#evaluating-and-evaluators).

## Parsing and parsers

### From the problem format to other formats

The most central parsers in DESDEO are those that allow parsing the problem
format from the MathJSON format discussed in section [The MathJSON
format](./problem_format.md#the-mathjson-format) to other formats that different
solvers can understand. These kind of parsers can be found in the [JSON parser][desdeo.problem.json_parser]
module.

The [MathParser][desdeo.problem.json_parser.MathParser] handles parsing of the problem format
into a polars format or a pyomo format. In the polars format, the problem is represented by
polars expression. Likewise, in the pyomo format, the problem is represented as a pyomo model.
This allows different solvers to handle the problems we have defined in DESDEO.

### From other formats to the problem format

DESDEO has also parsers that allow other formats to be parsed into the MathJSON format
representing multiobjective optimization problems. The most notable of these, and the currently
only one present, is the infix notation parser found in the [Infix parser][desdeo.problem.infix_parser]
module. This allows mathematical expression formatted in a typical infix format, i.e.,
how one would regularly write a mathematical expression down, e.g., `x * 2 - y`, to the MathJSON
format, e.g., 

```json
["Add",
    ["Multiply", "x", 2],
    ["Negate", "y"]
]
```

This is useful when one wants to model a multiobjective optimization problem in DESDEO since it
allows the function expression to be written down as they are, without a manual conversion to
the MathJSON format first. When adding function expression to the [Problem model][desdeo.problem.schema.Problem],
if a `func` field is given as a string in an infix format, it is automatically converted to the JSON
format utilizing the infix parser. The infix parser can also prove useful when defining various
scalarization functions in a dynamic way (c.f., the section [Scalarization](./scalarization.md#scalarization))

!!! warning
    The infix parser introduced a little bit of overhead. If the parser is utilized to parse infix expressions
    into the MathJSON format consecutively multiple times, as can be the case with some navigation-based methods,
    then the overhead might accumulate slowing the method down considerably. In such cases, it is advised to
    provide the expression directly in the MathJSON format to save time.

## Evaluating and evaluators