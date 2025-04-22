# Parsing and evaluating problems

In DESDEO, the problem format (c.f., section [The Problem Format](./problem_format.md))
can be parsed into other formats and evaluated. The purpose of evaluating is to
allow different solvers, discussed in section [Solvers](./solvers.md), to solve
the modeled multiobjective optimization problem. 

Here, we will first discuss the parsing and the parsers found in DESDEO in
section [Parsing and parsers](#parsing-and-parsers). Then, we will discuss the
evaluators available in DESDEO for evaluating multiobjective optimization
problems in section [Evaluating and evaluators](#evaluating-and-evaluators).
After these sections, the reader should have a basic understanding on how 
the problems defined in DESDEO are evaluated.

## Parsing and parsers

### From the problem format to other formats
The most central parsers in DESDEO are those that allow parsing the problem
format from the MathJSON format discussed in section [The MathJSON
format](./problem_format.md#the-mathjson-format) to other formats that different
solvers (i.e., optimizers)
can understand. These kind of parsers can be found in the [JSON parser][desdeo.problem.json_parser]
module.

The [MathParser][desdeo.problem.json_parser.MathParser] handles parsing of the problem format
into a polars format, a pyomo format, a sympy format, or a gurobipy format.
In the polars and sympy formats, the problem is represented by polars and sympy expressions.
Likewise, in the pyomo and gurobipy formats, the problem is represented as a pyomo or gurobipy model.
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

### The generic evaluator

The [`GenericEvaluator`][desdeo.problem.evaluator.GenericEvaluator]
is for evaluating problems to be solved with solvers that expect the
problem to be defined as Python functions. It can be utilized in two modes:
`variables` or `discrete`. In the first mode, the problem is expected to be 
evaluated with a given set of decision variable vectors. In the discrete mode,
the problem is evaluated based on its discrete representation (c.f., 
[DiscreteRepresentation][desdeo.problem.schema.DiscreteRepresentation]).

If the `variables` mode is used, then a polars evaluator is utilized. As the
name suggests, the polars evaluator utilizes polars dataframes to represent a
problem and evaluate it. The function expression found in the problem are parsed
to polars expression. This allows any Python-based solver to evaluate the
problem with given decision variable values. The polars evaluator currently
supports variables that are either scalar valued or 2D-vector valued
(basically one dimensional TensorVariables).
Higher dimensions on the decision variables are not supported.

If the `discrete` mode is used, then the problem is expected to be completely
defined by decision and objective vector pairs. When the problem is then
evaluated with a given set of decision variable vectors, the closest vectors are
searched for in the problem's discrete representation, and the corresponding
objective function values are then returned. The discrete evaluator only
supports scalar valued variables, not TensorVariables, at the moment.

The generic evaluator is utilized by solvers that do not expect, or require, the
exact formulation of the problem. That is, heuristics based and gradient-free
solvers. At the moment, these solvers implemented in DESDEO are
the [`Scipy solvers`][desdeo.tools.scipy_solver_interfaces] and
the [`ProximalSolver`][desdeo.tools.proximal_solver].

!!! Info
    For more info about polars, see [the polars documentation](https://pola.rs/).


### The pyomo evaluator

The [`PyomoEvaluator`][desdeo.problem.pyomo_evaluator.PyomoEvaluator] transforms
a problem into a pyomo model. This enables the usage of many external solvers,
such as the ones found in the [COIN-OR project](https://www.coin-or.org/) to be
utilized in DESDEO.
Unlike the generic evaluator, the pyomo evaluator does not
expect decision variables, instead, it provides a pyomo model that external
solvers can then utilize to solve the original problem.
The pyomo solvers implemented in DESDEO can be found in the
[pyomo solver interfaces][desdeo.tools.pyomo_solver_interfaces]. The pyomo evaluator
supports variables that are higher dimensional tensors (TensorVariables) as well.

!!! Note
    Currently, the pyomo evaluator utilized only concrete pyomo models (ConcreteModel).

!!! Info
    For more info about pyomo, see [the pyomo documentation](https://pyomo.readthedocs.io/en/stable/).

### The sympy evaluator

TODO.

### The gurobipy evaluator

The [`GurobipyEvaluator`][desdeo.problem.gurobipy_evaluator.GurobipyEvaluator]
transforms a problem into a Gurobipy model. This model is then used in optimization
through the [`GurobipySolver`][desdeo.tools.gurobipy_solver_interfaces]. The gurobipy evaluator
supports variables that are higher dimensional tensors (TensorVariables) as well.

!!! Info
    For more info about gurobi, see [the gurobi documentation](https://www.gurobi.com/documentation/).

### The evaluator for simulator and surrogate based problems

The [`Evaluator`][desdeo.problem.simulator_evaluator.Evaluator] adds support for simulator and surrogate
based objectives, constraints and extra functions. This is done by collecting the simulators and surrogates
in the evaluator and calling them by providing the decision variables and parameters needed.
The connection to simulators happens via [simulator files](./simulator_support.md#simulator-file).
The surrogate models are loaded from disk and then evaluated with the given decision variable values.
This evaluator also handles analytical functions by calling the [PolarsEvaluator](#the-generic-evaluator).

#### Evaluating simulator and surrogate based problems

[`Evaluator`][desdeo.problem.simulator_evaluator.Evaluator] can be used to evaluate any problems with
analytical, simulator and surrogate based objectives, constraints and extra functions.
In what follows, it is explained, how the evaluator works.
[Here](../howtoguides/problem.md#example-simulation-based-problem)
is an example of defining a simulator based in DESDEO.

First, we need to initialize the problem we are solving:

```python
problem = problem_w_simulator_and_surrogate()
```

The problem we defined has at least some simulator or surrogate based objectives,
constraints or extra functions. Therefore, we should use `Evaluator` to evaluate it.
To use the evaluator, we first need to initialize it. When initializing the
evaluator, we give the problem as an argument. We can also give the valuator some
optional additional arguments:

- `params`: Some parameters for the simulators as a python dict of dicts. For example,

```python
{
    "s_1": {
        "alpha": 0.1,
        "beta": 0.2
    },
    "s_2": {
        "epsilon": 10,
        "gamma": 20
    }
}
```

where `s_1` and `s_2` are symbols of two simulator and the corresponding values
are dicts with some parameters values for the corresponding simulators.
These parameter values are passed to the simulators.

- `surrogate_paths`: Paths to surrogate files stored on disk. Given as a python dict
with objective, constraint or extra function symbols as keys and the corresponding
surrogate paths as values of the dict. The surrogate file path can be given as
either a string of the path or a `pathlib.Path` object. This is an optional argument
and if not defined, the evaluator uses surrogate models in the problem
object, if available.

With these arguments we can then import and initialize the evaluator.

```python
from desdeo.problem import Evaluator

evaluator = Evaluator(
    problem=problem,
    params={
        "s_1": {
            "alpha": 0.1,
            "beta": 0.2
        },
        "s_2": {
            "epsilon": 10,
            "gamma": 20
        },
    }
    surrogate_paths={
        "f_1": f"{path_to_surrogate_model_1}",
        "f_2": f"{path_to_surrogate_model_2}"
    }
)
```

As the evaluator is initialized, it calls the `_load_surrogates` method
that loads the surrogate models from the disk. If no surrogate paths
are passed to the evaluator, it takes the surrogate paths from the
problem, if possible.

Now that the evaluator is initilized, we can call its `evaluate` method.
The method takes one argument `xs` that is a dict that has the problem's
decision variables and some values for them that we would like to
evaluate the problem with. Say we have three decision variables and we
would like to evaluate four samples. Then, the dict of decision variables
would have the decision variable symbols as keys and the corresponding
values would be lists of decision variable values with a single value for
each sample (length of each list in this example would be four).
Then we would define the decision variable dict and call the evaluate method as follows.

!!! NOTE
    All the decision variable value lists should be the same length, i.e.,
    same number of samples given of each decision variable.

```python
xs = {
    "x_1": [0.2, 0.5, 0.7, 0.1],
    "x_2": [-1.1, -2.1, -3.1, -4.1],
    "x_3": [3, 4, 2, 6]
}

results = evaluator.evaluate(xs)
```

The evaluator returns a polars Dataframe with each decision variable, objective,
constraint and extra function as their own column.

## Where to go next?

You can keep studying the various parsers found
in the modules [JSON parser][desdeo.problem.json_parser] and [Infix parser][desdeo.problem.infix_parser],
and the evalutors found in the modules [Generic evaluator][desdeo.problem.evaluator],
[Pyomo evaluator][desdeo.problem.pyomo_evaluator],
[GurobipyEvaluator][desdeo.problem.gurobipy_evaluator],
and [Evaluator][desdeo.problem.simulator_evaluator]. If you are interested in how to
solve a multiobjective optimization problem, then the section [Scalarization](./scalarization.md)
is a good place to check out.
