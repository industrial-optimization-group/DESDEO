# The Problem format

Multiobjective optimization problems are represented by pydantic dataclasses
in DESDEO. These are serializable and therefore easy to store. Moreover,
they can be readily transformed into JSON objects, which makes passing
them from DESDEO's web-API to various frontend applications seamless. This
also facilitates the parsing of the problem format into other formats as well.
While representing problems as pydantic dataclasses comes with some overhead,
this justified by the utility and robustness of the pydantic dataclasses.

One of the challenges with this kind of representation is representing function
expression. These have been taken care by exploiting the MathJSON format, which
is described in more details in the section
[The MathJSONformat](#the-mathjson-format).  The pydantic dataclass for representing a
multiobjective optimization problem in DESDEO is detailed in the section
[The Problem schema](#the-problem-schema), where the structure, or schema, of the
dataclass is described in detail.

## The MathJSON format

MathJSON is a lightweight, JSON-based format designed for representing
mathematical expressions in a structured and easily parsable manner. It provides
a standardized way to represent mathematical notation within JSON objects.
Moreover, it allows users to define mathematical formulations in web-based
frontend applications, which can then be directly represented in the DESDEO
problem schema.

In DESDEO, the MathJSON format is utilized to represent function
expression found throughout the problem schema. MathJSON follows
Polish notation, which means that mathematical operators precede
the operands when defining mathematical expressions. As an example,
consider the following expression:

$$
\max(x, y ,z) + \frac{y}{z} - \sin\left(z^x + 4.2\right)^3,
$$

where x, y, and x are some variables. The equivalent of this
expression in the MathJSON format (Polish notation), would be:

```json
[
  "Add",
  ["Divide", "y", "z"],
  ["Max", "x", "y", "z"],
  [
    "Negate",
    ["Power", ["Sin", ["Add", ["Power", "z", "x"], 4.2]], 3]
  ]
]
```

At first glance, this may look overly complicated, but from a programming
perspective, parsing Polish notation is much simpler than infix notation,
e.g., "normal" notation, where the operations are between the operands.

The MathJSON notation is utilized for all function expressions found
in the problem schema in DESDEO. For more information on the MathJSON
format, see the [MathJSON project](https://cortexjs.io/math-json/).


## The Problem schema

Here, the structure of the problem dataclass, or the schema, is presented
in detail. The `Problem` dataclass itself is constructed from other dataclasses
contained in its field.  We will refer to the schemas as _models_ from thereon.

### The symbol field

Across many of the models found in the `Problem` dataclass, the field `symbol`
will be often present. This field is very important, because it is utilized
to identify variables and function expression across the `Problem` model.
Therefore, the `symbol` field should contain a symbol that is unique across the
whole `Problem` model. The symbol itself is nothing more than a string value.
Some symbol names are reserved in DESDEO, and users should avoid defining
variables or function expression with these symbols. Reserved symbols
are discussed in the section [Symbols and expressions](#symbols-and-expressions).

### Problem

The main dataclass storing information related to a multiobjective optimization is the
`Problem` model, which consists of other models. The relational map of the
`Problem` model, and the models contained therein, has been visualized below:

![Relational map of problem](../assets/problem_map.png "The relational map of the Problem model.")

The `Problem` model consists of various fields: the name of the problem (**name**), the
description of the problem (**description**), a list of constant utilized in the definition of the
problem (**constants**), a list of the variables of the problem (**variables**), a list of the
objective functions of the problem (**objectives**), an optional list of the constraints of the problem
(**constraints**), an optional list of extra functions utilized in defining the problem (**extra_funcs**),
an optional list of scalarized representations of the problem (**scalarization_funcs**), an optional
representation of the problem as discrete decision variable vector and objective
vector pairs (**discrete_representation**), and an optional list of evaluated
solutions of the problem (**evaluated_solutions**).

The **name** and **description** of the problem are just strings. The other fields consist of one or
more additional models, which will be described next.

!!! Note
    The `symbol` entries across all fields must be unique. If one or more non-unique symbols are
    defined, `Problem` will raise an error when being initialized.

!!! Note
    The `Problem` model and all its field are **immutable**. The only exception to this
    is the `symbol` field of the `ScalarizationFunction` models. 


### Constant

The `Constant` model defines a constant with the fields `name`, `symbol` and
`value`. The field `name` is the name of the constant, for example "Price", the `symbol`
is the constant's mathematical symbol, for example "c_1", and the `value`
represents the numerical value of the constant, for example 4.2. The
JSON schema of `Constant` looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_constant_info()[0] }}
```
</details>
</br>

and an example of the JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_constant_info()[1] }}
```
</details>
</br>

### Variable

The `Variable` model defines a decision variable with the fields
`name`, `symbol`, `variable_type`, `lowerbounds`,
`upperbounds`, and `initial_value`.
The `name` and `symbol` represent the name and mathematical symbol of the variable.
The field `variable_type` represents the variable's type, either "real", "integer",
or "binary". Lastly, the `initial_value` field is the initial value of the variable. This
can be used by some optimizers found in DESDEO in finding an optimal solution
to, e.g., a scalarized variant of the problem. The JSON schema
`Variable` looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_variable_info()[0]}}
```
</details>
</br>

and an example of the JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_variable_info()[1]}}
```
</details>
</br>

### Objective

The `Objective` model defines an objective function with the fields `name`, `symbol`, `func`, 
`maximized`, `ideal`, `nadir`, and `objective_type`. The `name` and `symbol`
represent the objective's name and mathematical symbol. The field
`func` represents the objective's mathematical, or analytical, formulation.
This can be given either in the MathJSON format, or it may also be supplied
in infix, e.g., "normal", notation. In the case of the latter, the expression
will be parsed into the MathJSON format. The field `maximized` indicated
whether the objective function is to be maximized or not. By default, this
field is assumed to be false, i.e., objective functions are assumed to be
minimized in DESDEO unless it is explicitly specified that maximization
is desired. The fields `ideal` and `nadir` are the objective function's
ideal and nadir points, respectively. These are also optional, but supplying
them, if known, can expedite the execution of some methods in DESDEO. Lastly,
`objective_type` is the type of the objective functions. Currently, this can be
either "analytical" or "data_based". In the latter case, the `func` field
may be left empty, but it is then expected that a `DiscreteRepresentation`
for the objective is available in the `Problem` model. See the
subsection [DiscreteRepresentation](#discreterepresentation).

The JSON schema of `Objective` looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_objective_info()[0] }}
```
</details>
</br>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_objective_info()[1] }}
```
</details>
</br>

### Constraint

The `Constraint` model defines a constraint function with the fields `name`,
`symbol`, `cons_type`, `linear` and `func`.  The `name` and `symbol` represent
the constraint's name and mathematical symbol, respectively. The field
`cons_type` represents the type of constraint. Currently, the type can be
either "<=" for inequality constraints, or "=" for equality constraints.
The field `linear` indicates whether the constraint is linear, which defaults to
true. Lastly, `func` is the mathematical representation of the constraint function.
This can be supplied either in the MathJSON format or in "normal" infix format.
As for how the constraint should be defined, see the note below.

!!! note
    The constraint is expected in a standard format where the function expression of the constraint is on the left hand side of an
    inequality expression, and on the right hand side a zero is assumed. Likewise, for equality constraints, the left hand side has a function
    expression that must be equal to zero. In other words, a constraint, such as `x_1 <= 5` must first be expressed as `x_1 - 5 <= 0`, and then the
    constraint expression supplied to the `Constraint` model would be `x_1 - 5`. Likewise, an equality constraint, such as `x_1 + x_2 == 5` would be first
    expressed as `x_1 + x_2 - 5 == 0`, and the supplied function expression would be `x_1 + x_2 - 5`.

Its JSON schema of `Constraint` looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_constraint_info()[0]}}
```
</details>
</br>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_constraint_info()[1]}}
```
</details>
</br>

### ExtraFunction

The `ExtraFunction` model defines any functions utilized in the definition of the problem. The extra function has the fields `name`,
`symbol`, and `func`. The fields `name` and `symbol` represent the extra function's name and mathematical symbol, respectively.
The field `func` is the mathematical representation of the extra function, which must be supplied either in the MathJSON
format, or in the "normal" infix notation.

The JSON schema of `ExtraFunction` looks as:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_extra_function_info()[0]}}
```
</details>
</br>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_extra_function_info()[1]}}
```
</details>
</br>

### ScalarizationFunction


The `ScalarizationFunction` model defines any scalarizations of the problem being solved. The scalarization
function has the fields `name`, `symbol` and `func`. The fields `name` and `symbol` represent the function's
name and mathematical symbol. The `func` field is the mathematical representation of the scalarization
function, it must be supplied either is the MathJSON format or "normal" infix notation.
Usually, scalarization functions are added by various methods found in DESDEO, and are not expected
to be supplied by users directly. Nevertheless, the field can be supplied by a user, if such a need arises.

Its JSON schema of `ScalarizationFunction` looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_scalarization_function_info()[0]}}
```
</details>
</br>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_scalarization_function_info()[1]}}
```
</details>
</br>

### DiscreteRepresentation

The `DiscreteRepresentation` model defines a discrete representation of a
problem.  This representation is defined by the decision variable and objective
function value pairs, which are defined in the fields `variable_values` and
`objective_values`, respectively.  This representation may consist of only
non-dominated solutions, or it may contain dominated solutions as well. This is
indicated by the `non_dominated` field. This representation is useful for
problems that do not have an analytical formulation. It may also be used in
conjunction with an analytical formulation. Some interactive multiobjective
optimization methods can utilize both representations, while other are better
suited just for one. For instance, NAUTILUS Navigator is best utilized with a
discrete representation.

The JSON schema `DiscreteRepresentation` looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_discrete_representation_info()[0] }}
```
</details>
</br>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ get_discrete_representation_info()[1] }}
```
</details>
</br>

## Symbols and expressions

The field `symbol`, which is found across the `Problem` schema, plays a very important role
in DESDEO. It is utilized to identify variables, constants, and function expression. Symbols
can also be utilized across the fields of `Problem` to refer to each other. In other words,
the `func` field in a `ScalarizationModel` can contain the symbol referencing
the `func` field of an `ExtraFunction`, or the value of a `Constant`, for instance. This is
also an important fact to keep in mind when parsing the a `Problem` model from one
representation to another. This will be discussed in more detail in the 
section [Parsing and Evaluation](./parsing_and_evaluating.md/#parsing-and-evaluating-problems).

It is assumed that any expression in a `func` field, that is not a numerical value,
refers to either a symbol or a mathematical operation. In what follows, the
reserved symbols are presented in the section [Reserved symbols](#reserved-symbols).
The supported mathematical expressions are presented in the section
[Supported expression](#supported-expressions).

### Reserved symbols

In essence, any symbol that starts with an underscore, e.g., `_x` is considered
to be reserved. This is because some of the routines in DESDEO that manipulate the
problem formulation may add, for instance, auxiliary variables, which are
automatically named with a symbol that starts with an underscore. To avoid
confusion and bugs, users are advised to avoid utilizing symbols
starting with underscores when defining problems.

Another symbol, which is should be avoided, is any symbol that ends in
`_min`, e.g., `f_1_min`. Since DESDEO internally transforms all
expressions to be optimized into their minimization form, routines will
append a `_min` to symbols to indicate that the expression the symbol
 represents, is to be, or has been, minimized. Other routines will
 expect these symbols to be available. Users are therefore advised to
 avoid symbols that end in a `_min`.

### Supported expressions

Expressions representing mathematical operations are
automatically identified by DESDEO. The expressions
are case sensitive. Currently supported expressions are listed
in the table below:

!!! note
    The equivalent infix notation operator is given in parentheses.
    For operators without this equivalent, the operator will
    still work in infix notation, e.g., `Sin(x) + 3`.

| Expression  | Explanation                                 |
|-------------|---------------------------------------------|
| Negate (-)  | Negates the value (changes its sign).       |
| Add (+)     | Adds two values.                            |
| Subtract (-)| Subtracts one value from another.           |
| Multiply (*)| Multiplies two values.                      |
| Divide (/)  | Divides one value by another.               |
| Exp         | Calculates the exponential of a value.      |
| Ln          | Natural logarithm of a value.               |
| Lb          | Logarithm base 2 of a value.                |
| Lg          | Logarithm base 10 of a value.               |
| LogOnePlus  | Natural logarithm of (1 + value).           |
| Sqrt        | Square root of a value.                     |
| Square      | Squares a value.                            |
| Power (**)  | Raises a value to the power of another.     |
| Abs         | Absolute value.                             |
| Ceil        | Rounds a value up to the nearest integer.   |
| Floor       | Rounds a value down to the nearest integer. |
| Arccos      | Inverse cosine of a value.                  |
| Arccosh     | Inverse hyperbolic cosine of a value.       |
| Arcsin      | Inverse sine of a value.                    |
| Arcsinh     | Inverse hyperbolic sine of a value.         |
| Arctan      | Inverse tangent of a value.                 |
| Arctanh     | Inverse hyperbolic tangent of a value.      |
| Cos         | Cosine of a value.                          |
| Cosh        | Hyperbolic cosine of a value.               |
| Sin         | Sine of a value.                            |
| Sinh        | Hyperbolic sine of a value.                 |
| Tan         | Tangent of a value.                         |
| Tanh        | Hyperbolic tangent of a value.              |
| Max         | Finds the maximum of values.                |