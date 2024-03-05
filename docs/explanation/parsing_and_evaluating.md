# Parsing and evaluating problems

In DESDEO, the problem format (c.f., section [The Problem Format](./problem_format.md))
can be parsed into other formats and evaluated. The purpose of evaluating is to
allow different solvers, discussed in section [Solvers](./solvers.md), to solve
the modeled multiobjective optimization problem. 

Here, we will first discuss the parsing and the parsers found in DESDEO in
section [Parsing and parsers](#parsing-and-parsers). Then, we will discuss the
solvers available in DESDEO for solving multiobjective optimization
problems in section [Evaluating and evaluators](#evaluating-and-evaluators).
After these sections, the reader should have a basic understanding on how 
the problems defined in DESDEO are solved.

## Parsing and parsers

### From the problem format to other formats
The most central parsers in DESDEO are those that allow parsing the problem
format from the MathJSON format discussed in section [The MathJSON
format](./problem_format.md#the-mathjson-format) to other formats that different
solvers (i.e., optimizers)
can understand. These kind of parsers can be found in the [JSON parser][desdeo.problem.json_parser]
module.

The [MathParser][desdeo.problem.json_parser.MathParser] handles parsing of the problem format
into a polars format or a pyomo format. In the polars format, the problem is represented by
polars expressions. Likewise, in the pyomo format, the problem is represented as a pyomo model.
This allows different solvers to handle the problems we have defined in DESDEO.

### From other formats to the problem format

DESDEO has also parsers that allow other formats to be parsed into the MathJSON format
representing multiobjective optimization problems. The most notable of these, and the currently
only one present, is the infix notation parser found in the [Infix parser][desdeo.problem.infix_parser]
module. This allows mathematical expression formatted in a typical infix format, i.e.,
how one would regularly write a mathematical expression down, e.g., `x * 2 - y`, to the MathJSON
format:

```json
["Add",
    ["Multiply", "x", 2],
    ["Negate", "y"]
]
```

This is useful when one wants to model a multiobjective optimization problem in DESDEO since it
allows the function expression to be written down as they are, without requiring a manual conversion to
the MathJSON format first. When adding function expression to the [Problem model][desdeo.problem.schema.Problem],
if a `func` field is initialized with a string in an infix format, it is automatically converted to the JSON
format utilizing the infix parser. The infix parser can also prove useful when defining various
scalarization functions in a dynamic way (c.f., the section [Scalarization](./scalarization.md#scalarization)).

!!! warning
    The infix parser introduces a little bit of overhead. If the parser is utilized to parse infix expressions
    into the MathJSON format consecutively multiple times, as can be the case with some navigation-based methods,
    then the overhead might accumulate slowing the method down considerably. In such cases, it is advised to
    provide the expression directly in the MathJSON format to save time.

## Evaluating and evaluators

While parsers transform the problem format in DESDEO from one representation to another,
evaluators enable the evaluating of a problem, usually by supplying one or more
decision variable vectors. Evaluators are not something a user is expected to directly
utilize, rather, evaluators are often tied to solvers and solver interfaces, which
are discussed in the [Solvers](./solvers.md) section.

It is important to understand in which order the various fields found 
in the problem format (c.f., [The Problem schema](./problem_format.md#the-problem-schema)
and [Problem][desdeo.problem.schema.Problem]) are evaluated.
The first field to be evaluated is the `constants` field, which is made up of
[`Constant`][desdeo.problem.schema.Constant] models. Evaluating these fields amounts to
replacing the symbol of the constant with its numerical value, or defining an internal
variable with the same value.

Next, the `extra_funcs` field made up of [`ExtraFunction`][desdeo.problem.schema.ExtraFunction]
models is evaluated. This assumes that the extra functions might utilize constants in them, which
requires the constants to be available prior to the evaluation. Naturally, evaluating any extra
functions is skipped if they are not defined for the problem being evaluated.

After the extra functions, the [`Objective`][desdeo.problem.schema.Objective] models, found
in the field `objectives` of the problem, are evaluated. These can depend on constants
and extra functions, which means that these must have been evaluated prior to evaluating any
objectives.

Then, any [`Constraint`][desdeo.problem.schema.Constraint] models in the `constraints` field
of the problem are evaluated. This assumes that prior to evaluating any constraints, any
constants, extra functions, or objectives utilized in the constraint have been evaluated.
Objectives might be part of a constraint in, e.g., the epsilon-constraint scalarization.
If no constraints have been defined, then this step is skipped.

Lastly, any [`ScalarizationFunction`][desdeo.problem.schema.ScalarizationFunction] present
in the `scalarizations_funcs` field are evaluated. These can again depend on any of the
constants, extra functions, constraints, or objectives defined for the problem. If no
scalarization functions have been defined, then their evaluation is skipped.

The order of evaluation is important to understand to avoid bugs and unexpected behavior when
defining problems in DESDEO. The order of evaluating the fields found in the problem model
has been summarized in the list below:

1. Constants, if any.
2. Extra functions, if any.
3. Objective functions.
4. Constraint functions, if any.
5. Scalarization functions, if any.

### The polars evaluator

### The pyomo evaluator