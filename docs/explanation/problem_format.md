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
`Problem` model and the models container therein has been visualized below:

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

and an example of the JSON object corresponding to the schema looks like:

```json
{
  "name": "constant example",
  "symbol": "c",
  "value": 42.1
}
```

### Variable

The `Variable` model defines a decision variable with a name, symbol, variable type, lower and upper
bounds, and an initial values. ITs JSON schema looks as follows:
