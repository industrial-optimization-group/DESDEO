# The problem format

## MathJSON

TODO:

- Explain the MathJSON format and how it is used to store function expressions.

## The pydantic schema

### Problem

Multiobjective optimization problems are represented by models stored in JSON files.
The schema of the models have been defined utilizing pydantic. The main
model storing information related to a multiobjective optimization is the
`Problem` model, which consists of other models. The relational map of the
`Problem` model, and the models contained therein, has been visualized below:

![Relational map of problem](../assets/problem_map.png "The relational map of the Problem model.")

The `Problem` model consists of various fields: the name of the problem (**name**), the
description of the problem (**description**), a list of constant utilized in the definition of the
problem (**constants**), a list of the variables of the problem (**variables**), a list of the
objective functions of the problem (**objectives**), an optional list of the constraints of the problem
(**constraints**), an optional list of extra functions utilized in defining the problem (**extra_funcs**),
an optional list of scalarized representations of the problem (**scalarization_funcs**), and an optional list
of evaluated solutions of the problem (**evaluated_solutions**).

The **name** and **description** of the problem are just strings. The other fields consist of one or
more additional models, which will be described next.

### Constant

The `Constant` model defines a constant with a name, symbol and a value. Its JSON
schema looks as follows:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "description": "Model for a constant.",
  "properties": {
    "name": {
      "description": [
        "Descriptive name of the constant. This can be used in UI and visualizations.",
        " Example: 'maximum cost'."
      ],
      "title": "Name",
      "type": "string"
    },
    "symbol": {
      "description": "Symbol to represent the constant. This will be used in the rest of the problem definition. It may also be used in UIs and visualizations. Example: 'c_1'.",
      "title": "Symbol",
      "type": "string"
    },
    "value": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "number"
        },
        {
          "type": "boolean"
        }
      ],
      "description": "Value of the constant.",
      "title": "Value"
    }
  },
  "required": ["name", "symbol", "value"],
  "title": "Constant",
  "type": "object"
}
```
</details>

and an example of the JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "name": "constant example",
  "symbol": "c",
  "value": 42.1
}
```
</details>

### Variable

The `Variable` model defines a decision variable with a name, symbol, variable type, lower and upper
bounds, and an initial values. Its JSON schema looks as follows:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "$defs": {
    "VariableTypeEnum": {
      "enum": ["real", "integer", "binary"],
      "title": "VariableTypeEnum",
      "type": "string"
    }
  },
  "description": "Model for a variable.",
  "properties": {
    "name": {
      "description": "Descriptive name of the variable. This can be used in UI and visualizations. Example: 'velocity'.",
      "title": "Name",
      "type": "string"
    },
    "symbol": {
      "description": "Symbol to represent the variable. This will be used in the rest of the problem definition. It may also be used in UIs and visualizations. Example: 'v_1'.",
      "title": "Symbol",
      "type": "string"
    },
    "variable_type": {
      "allOf": [
        {
          "$ref": "#/$defs/VariableTypeEnum"
        }
      ],
      "description": "Type of the variable. Can be real, integer or binary."
    },
    "lowerbound": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        },
        {
          "type": "boolean"
        }
      ],
      "description": "Lower bound of the variable.",
      "title": "Lowerbound"
    },
    "upperbound": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        },
        {
          "type": "boolean"
        }
      ],
      "description": "Upper bound of the variable.",
      "title": "Upperbound"
    },
    "initial_value": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        },
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "description": "Initial value of the variable. This is optional.",
      "title": "Initial Value"
    }
  },
  "required": [
    "name",
    "symbol",
    "variable_type",
    "lowerbound",
    "upperbound",
    "initial_value"
  ],
  "title": "Variable",
  "type": "object"
}
```
</details>

and an example of the JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "name": "example variable",
  "symbol": "x_1",
  "variable_type": "real",
  "lowerbound": -0.75,
  "upperbound": 11.3,
  "initial_value": 4.2
}
```
</details>

### Objective

The `Objective` model defines an objective function with a name, symbol, function expression, whether the function is
to be maximized or not, and the function's ideal and nadir value. Its JSON schema looks as follows:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "description": "Model for an objective function.",
  "properties": {
    "name": {
      "description": [
        "Descriptive name of the objective function. This can be used in UI and visualizations.",
        " Example: 'time'."
      ],
      "title": "Name",
      "type": "string"
    },
    "symbol": {
      "description": "Symbol to represent the objective function. This will be used in the rest of the problem definition. It may also be used in UIs and visualizations. Example: 'f_1'.",
      "title": "Symbol",
      "type": "string"
    },
    "func": {
      "description": "The objective function. This is a JSON object that can be parsed into a function.Must be a valid MathJSON object. The symbols in the function must match the symbols defined for variable/constant/extra function.",
      "items": {},
      "title": "Func",
      "type": "array"
    },
    "maximize": {
      "default": false,
      "description": "Whether the objective function is to be maximized or minimized.",
      "title": "Maximize",
      "type": "boolean"
    },
    "ideal": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "description": "Ideal value of the objective. This is optional.",
      "title": "Ideal"
    },
    "nadir": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "description": "Nadir value of the objective. This is optional.",
      "title": "Nadir"
    }
  },
  "required": ["name", "symbol", "func", "ideal", "nadir"],
  "title": "Objective",
  "type": "object"
}
```
</details>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "name": "example objective",
  "symbol": "f_1",
  "func": ["Divide", ["Add", "x_1", 3], 2],
  "maximize": false,
  "ideal": -3.3,
  "nadir": 5.2
}
```
</details>

!!! note
    The `func` entry in the JSON object of the objective model must adhere to the MathJSON format.

### Constraint

The `Constraint` model defines a constraint function with a name, symbol, and function expression. Its JSON schema looks as follows:

!!! note
    The constraint must be expected in a standard format where the function expression of the constraint is on the left hand side of an
    inequality expression, and on the right hand side a zero is assumed. Likewise, for equality constraints, the left hand side has a function
    expression that must be equal to zero. In other words, a constraint, such as `x_1 <= 5` must first be expressed as `5 - x_1 <= 0`, and then the
    constraint expression supplied to the `Constraint` model would be `5 - x_1`. Likewise, an equality constraint, such as `x_1 + x_2 == 5` would be first
    expressed as `x_1 + x_2 - 5 == 0`, and the supplied function expression would be `x_1 + x_2 - 5`.

<details>
<summary><b>Click to expand</b></summary>
```json
{
  {
  "$defs": {
    "ConstraintTypeEnum": {
      "description": "An enumerator for supported constraint expression types.",
      "enum": [
        "=",
        "<="
      ],
      "title": "ConstraintTypeEnum",
      "type": "string"
    }
  },
  "description": "Model for a constraint function.",
  "properties": {
    "name": {
      "description": "Descriptive name of the constraint. This can be used in UI and visualizations. Example: 'maximum length'",
      "title": "Name",
      "type": "string"
    },
    "symbol": {
      "description": "Symbol to represent the constraint. This will be used in the rest of the problem definition. It may also be used in UIs and visualizations. Example: 'g_1'.",
      "title": "Symbol",
      "type": "string"
    },
    "cons_type": {
      "allOf": [
        {
          "$ref": "#/$defs/ConstraintTypeEnum"
        }
      ],
      "description": "The type of the constraint. Constraints are assumed to be in a standard form where the supplied 'func' expression is on the left hand side of the constraint's expression, and on the right hand side a zero value is assume. The comparison between the left hand side and right hand side is either and quality comparison ('=') or lesser than equal comparison ('<=')."
    },
    "func": {
      "description": "Function of the constraint. This is a JSON object that can be parsed into a function.Must be a valid MathJSON object. The symbols in the function must match objective/variable/constant shortnames.",
      "items": {},
      "title": "Func",
      "type": "array"
    }
  },
  "required": [
    "name",
    "symbol",
    "cons_type",
    "func"
  ],
  "title": "Constraint",
  "type": "object"
}
}
```
</details>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  {
  "name": "example constraint",
  "symbol": "g_1",
  "cons_type": "<=",
  "func": [
    "Add",
    [
      "Add",
      [
        "Divide",
        "x_1",
        2
      ],
      "c"
    ],
    -4.2
  ]
 }
}
```
</details>

!!! note
    The `func` entry in the JSON object of the constraint model must adhere to the MathJSON format.

### ExtraFunction

The `ExtraFunction` model defines any functions utilized in the definition of the problem. The extra function has a name,
symbol, and function expression. Its JSON schema looks as:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "description": "Model for extra functions.\n\nThese functions can, e.g., be functions that are re-used in the problem formulation, or\nthey are needed for other computations related to the problem.",
  "properties": {
    "name": {
      "description": "Descriptive name of the function. Example: 'normalization'",
      "title": "Name",
      "type": "string"
    },
    "symbol": {
      "description": "Symbol to represent the function. This will be used in the rest of the problem definition. It may also be used in UIs and visualizations. Example: 'avg'.",
      "title": "Symbol",
      "type": "string"
    },
    "func": {
      "description": "The string representing the function. This is a JSON object that can be parsed into a function.Must be a valid MathJSON object. The symbols in the function must match symbols defined for objective/variable/constant.",
      "items": {},
      "title": "Func",
      "type": "array"
    }
  },
  "required": ["name", "symbol", "func"],
  "title": "ExtraFunction",
  "type": "object"
}
```
</details>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "name": "example extra function",
  "symbol": "m",
  "func": ["Divide", "f_1", 100]
}
```
</details>

!!! note
    The `func` entry in the JSON object of the extra function model must adhere to the MathJSON format.

### ScalarizationFunction

The `ScalarizationFunction` model defines any scalarizations of the problem being solved. The scalarization
function has a name and a function definition. Its JSON schema looks as follows:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "description": "Model for scalarization of the problem.",
  "properties": {
    "name": {
      "description": "Name of the scalarization. Example: 'STOM'",
      "title": "Name",
      "type": "string"
    },
    "symbol": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": "Optional symbol to represent the scalarization function. This may be used in in UIs and visualizations.",
      "title": "Symbol"
    },
    "func": {
      "description": "Function representation of the scalarization. This is a JSON object that can be parsed into a function.Must be a valid MathJSON object. The symbols in the function must match the symbols defined for objective/variable/constant/extra function.",
      "items": {},
      "title": "Func",
      "type": "array"
    }
  },
  "required": ["name", "func"],
  "title": "ScalarizationFunction",
  "type": "object"
}
```
</details>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "name": "Achievement scalarizing function",
  "symbol": "S",
  "func": [
    "Max",
    ["Multiply", "w_1", ["Add", "f_1", -1.1]],
    ["Multiply", "w_2", ["Add", "f_2", -2.2]]
  ]
}
```
</details>

!!! note
    The `func` entry in the JSON object of the scalarization function model must adhere to the MathJSON format.

### EvaluatedInfo

The `EvaluatedInfo` model defines information related to one or more evaluated solutions to the problem. It contains
infor about the source of the solution (e.g., which method has been used to compute it) and, in case the information
describes multiple solutions, whether the solutions are mutually dominated or not. The model's JSON schema looks as
follows:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "description": "Model to represent information about an evaluated solution or solutions to the problem.\n\nThis model may be extended as needed.",
  "properties": {
    "source": {
      "description": "The source of the evaluated solution(s). E.g., an optimization method's name.",
      "title": "Source",
      "type": "string"
    },
    "dominated": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "description": "Optional. Are the solutions dominated?",
      "title": "Dominated"
    }
  },
  "required": ["source", "dominated"],
  "title": "EvaluatedInfo",
  "type": "object"
}
```
</details>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "source": "NSGA-III",
  "dominated": false
}
```
</details>

### EvaluatedSolutions

The `EvaluatedSolutions` model defines one or more evaluated decision vectors and their corresponding objective vectors. The model
contains also information on the evaluated solutions. Its JSON schema looks as follows:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "$defs": {
    "EvaluatedInfo": {
      "description": "Model to represent information about an evaluated solution or solutions to the problem.\n\nThis model may be extended as needed.",
      "properties": {
        "source": {
          "description": "The source of the evaluated solution(s). E.g., an optimization method's name.",
          "title": "Source",
          "type": "string"
        },
        "dominated": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "description": "Optional. Are the solutions dominated?",
          "title": "Dominated"
        }
      },
      "required": ["source", "dominated"],
      "title": "EvaluatedInfo",
      "type": "object"
    }
  },
  "description": "Model to represent the evaluated objective values of a decision vector.\n\nThe decision vectors 'decision_vectors' and objective vectors\n'objective_vector' correspond to each other based on their ordering. I.e.,\nthe evaluated objective function values for the decision vector at position i\n(decision_vectors[i]) are represented by the objective vector at position i\n(objective_vector[i]).",
  "properties": {
    "info": {
      "allOf": [
        {
          "$ref": "#/$defs/EvaluatedInfo"
        }
      ],
      "description": "Information about the evaluated solutions."
    },
    "decision_vectors": {
      "description": "A list of the evaluated decision vectors.",
      "items": {
        "items": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "integer"
            },
            {
              "type": "boolean"
            }
          ]
        },
        "type": "array"
      },
      "title": "Decision Vectors",
      "type": "array"
    },
    "objective_vectors": {
      "description": "A list of the values of the evaluated objective functions.",
      "items": {
        "items": {
          "type": "number"
        },
        "type": "array"
      },
      "title": "Objective Vectors",
      "type": "array"
    }
  },
  "required": ["info", "decision_vectors", "objective_vectors"],
  "title": "EvaluatedSolutions",
  "type": "object"
}
```
</details>

and an example of a JSON object corresponding to the schema looks like:

<details>
<summary><b>Click to expand</b></summary>
```json
{
  "info": {
    "source": "NSGA-III",
    "dominated": false
  },
  "decision_vectors": [
    [4.2, -1.2, 6.6],
    [4.2, -1.2, 6.6],
    [4.2, -1.2, 6.6]
  ],
  "objective_vectors": [
    [1.0, 2.0, 3.0],
    [1.0, 2.0, 3.0],
    [1.0, 2.0, 3.0]
  ]
}
```
</details>

## Parsing

The problem defined in a `Problem` model is parsed into polars expressions that can be numerically evaluated.
Parsing is done according to the following logic described below.

### Initialization

1. **Create Math Parser**: Initialize a math parser of a specified type. The
   default is a polars parser.
2. **Constant Replacement**: Examine a given instance of a `Problem` model for any
   instances of `Constant`.
   If found, replace these constants with their numerical values across all
   function expressions within the problem model.
3. **Function Expression Parsing**: Convert the function expressions
   found in the `Objective`, `Constraint`, `ExtraFunction`, `ScalarizationFunction` models of the problem
   into a structured format, a dataframe in case of the default polars parser, for easier
   manipulation and evaluation.

### Evaluating

1. **Extra Functions Evaluation**: If any extra functions are defined, evaluate
   them using specified decision variables. Store the outcomes in new columns within the
   dataframe, with the symbol of the corresponding extra function as the column
   name.
2. **Objective Functions Evaluation**: Evaluate the objective functions based on
   the decision variables and any values derived from extra functions (already evaluated and stored
   in the dataframe). Store these
   results in separate columns of the dataframe. The new columns are named with the symbol
   defined for each objective function.
3. **Constraints Evaluation**: Evaluate the constraints, if any are present,
   considering the decision variables and any computed extra function values. Store these
   in the dataframe. The new columns are named with the symbol defined for each constraint.
4. **Scalarization Functions Evaluation**: If scalarization functions are
   defined, evaluate them using the values obtained from objective functions and
   extra functions. Store these results in the dataframe in columns named with the
   name of the scalarization function.
5. **Result Compilation**: Compile a pydantic dataclass encapsulating all
   results, including decision variables, values of objective functions,
   constraints, and scalarization functions. Return the instance of the dataclass.

The flow of the parsing logic has been visualized below:

![Flow of the Problem model parsing into polars expressions](../assets/parsing_flow.png "The parsing of the Problem model.")