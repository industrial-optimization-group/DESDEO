# Defining multiobjective optimization problems
There are multiple types of problems that may be defined in DESDEO. Here,
examples on how to define each type of problem are provided. To understand
how problems are modelled in DESDEO, please refer to
[the problem format explanation](../explanation/problem_format.md).
Problems with different types of objectives, constraints and extra functions
can also be defined. For example, the same problem can have analytical and simulator
and surrogate based objectives. These types of problems can be evaluated
using the [`Evaluator`][desdeo.problem.simulator_evaluator.Evaluator]
that has methods to evaluate simulator and surrogate based objectives,
constraints and extra functions and the evaluator also utilizes
the [`PolarsEvaluator`][desdeo.problem.evaluator.PolarsEvaluator] to
evaluate the analytical ones.

## Example: analytical problem
Problems where we know the explicit formualtion of the problem
are known as *analytical problems* in DESDEO. There problems are
straight-forward to define. As an example, consider the
*river pollution problem* with five objectives:

\begin{equation}
    \begin{array}{rll}
    \text{min}  & f_1({\mathbf{x}}) =& - 4.07 - 2.27 x_1 \\ 
    \text{min}  & f_2({\mathbf{x}}) =& - 2.60 - 0.03 x_1  - 0.02 x_2 \\
    &&\quad - \frac{0.01}{1.39 - x_1^2} - \frac{0.30}{1.39 - x_2^2} \\ 
    \text{min}  & f_3({\mathbf{x}}) =& - 8.21 + \frac{0.71}{1.09 - x_1^2} \\ 
    \text{min}  & f_4({\mathbf{x}}) =& - 0.96 + \frac{0.96}{1.09 - x_2^2} \\ 
    \text{min}  & f_5({\mathbf{x}}) =& \max\{|x_1 - 0.65|, |x_2 - 0.65|\} \\ 
    &&\\
    \text{s.t.}  && 0.3 \leq x_1, x_2 \leq 1.0, \\
    \end{array}
\end{equation}

Before we define the objective functions, we can define the two variables of the
problem: `x_1` and `x_2`. We define them as:

```python
{{ get_river_snippet("variables") }}
```

Before defining the objectives as instances of `Object`, we can write the objective
functions utilizing standard infix notation:

```python
{{ get_river_snippet("infix_objectives") }}
```

!!! Warning
    When defining objective functions, or any function expression, it is important
    that the variables match the symbols used in the overall definition of `Problem`.
    Otherwise, evaluating the problem will result in incorrect results.

We may then use the infix notation to define the objectives as:

```python
{{ get_river_snippet("objectives") }}
```

And this is all we need to define the problem:

```python
{{ get_river_snippet("problem") }}
```

The full definition of the problem in JSON format then looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```json
{{ river_problem_example() }}
```

</details>
</br>

And we are done! We have now defined an analytical problem in DESDEO.

## Example: data-based problem (WIP)
WIP.

## Example: simulation based problem

Simulation based problems are problems with objectives, constraints
and extra functions whose values are simulated during the solution process.
Here is an example of defining a simulation based problem in DESDEO:

First, we define the decision variables.
In this case, we have two variables with symbols `x_1` and `x_2`.

```python
variables = [
    Variable(
        name="Variable 1",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=float("-inf"),
        upperbound=float("inf"),
        initial_value=0
    ),
    Variable(
        name="Variable 2",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=float("-inf"),
        upperbound=float("inf"),
        initial_value=0
    )
]
```

!!! NOTE
    Even though the decision variables used in the simulators are passed to the simulator as lists,
    the variables are defined here as instances of `Variable` (instead of `TensorVariable`). The list
    elements represent the value (a scalar) of the variable in the corresponding sample. The variables
    can also be TensorVariables with each element of the TensorVariable also a list of samples.

Next, we can define the simulators that define the problem's objectives, constraints and extra
functions. These simulators are given paths to their [simulator files](../explanation/simulator_support.md#simulator-file)
that connect DESDEO to the simulators. The file path is given as either a string or a pyhton's
pathlib.Path object. Optionally, the simulators can be given some parameters as a dict
as well. These parameters are given to the simulator while evaluating the problem.

!!! NOTE
    The list of simulators has to be defined when initializing the problem as this list
    is used when evaluating the problem. The parameters for the simulators, on the other
    hand, may be given when initializing the evaluator and left empty when defining
    the problem.

```python
simulator = [
    Simulator(
        name="Simulator 1",
        symbol="s_1",
        file=f"{path_to_simulator_file_1}", # either a string path or python's Path object
        parameter_options={
            "alpha": 0.5,
            "beta": 2
        }
    ),
    Simulator(
        name="Simulator 2",
        symbol="s_2",
        file=f"{path_to_simulator_file_2}"
    )
]
```

Next, we define the objectives. This is similar to analytical objectives but instead of a function
expression, the objective has a path to the simulator file used to simulate the objective values.
Here we have two objectives (`f_1`, `f_3`) that get their values from the same simulator file and one that
has a different simulator file. Additionally, objective `f_3` is maximized.

```python
objectives = [
    Objective(
        name="Objective 1",
        symbol="f_1",
        simulator_path=f"{path_to_simulator_file_1}",
        maximize=False,
        objective_type=ObjectiveTypeEnum.simulator
    ),
    Objective(
        name="Objective 2",
        symbol="f_2",
        simulator_path=f"{path_to_simulator_file_2}",
        maximize=False,
        objective_type=ObjectiveTypeEnum.simulator
    ),
    Objective(
        name="Objective 3",
        symbol="f_3",
        simulator_path=f"{path_to_simulator_file_1}",
        maximize=True,
        objective_type=ObjectiveTypeEnum.simulator
    ),
]
```

Similarly, we can define constraints and extra functions.
In this example, we define one constraint `g_1` and one extra function `e_1`.

```python
constraints = [
    Constraint(
        name="Constraint 1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        simulator_path=f"{path_to_simulator_file_1}",
    )
]

extra_functions = [
    ExtraFunction(
        name="e_1",
        symbol="e_1",
        simulator_path=f"{path_to_simulator_file_2}"
    )
]
```

!!! NOTE
    Since there are no function expressions that are given to an optimizer,
    simulator based objectives, constraints and extra functions do not need
    linearity, convexity or differentiability to have the value `True` in any case.

Now we can define the `Problem` object.

```python
problem = Problem(
    name="Example simulator based problem.",
    description="An example of a simulator based problem.",
    variables=variables,
    objectives=objectives,
    constraints=constraints,
    extra_funcs=extra_functions,
    simulators=simulators
)
```

## Example: surrogate based problem

Surrogate based problems are problems with objectives, constraints
and extra functions whose values come from pre-trained surrogate models.
Here is an example of defining a surrogate based problem in DESDEO:

First, we define the decision variables.
In this case, we have two variables with symbols `x_1` and `x_2`.

```python
variables = [
    Variable(
        name="Variable 1",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=float("-inf"),
        upperbound=float("inf"),
        initial_value=0
    ),
    Variable(
        name="Variable 2",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=float("-inf"),
        upperbound=float("inf"),
        initial_value=0
    )
]
```

!!! NOTE
    Even though the decision variables are passed to the surrogate models as lists,
    the variables are defined here as instances of `Variable` (instead of `TensorVariable`). The list
    elements represent the value (a scalar) of the variable in the corresponding sample. The variables
    can also be TensorVariables with each element of the TensorVariable also a list of samples.

Next, we define the objectives. This is similar to analytical objectives but instead of a function
expression, the objective has a path to the surrogate model used to predict the objective values.
Here we have two objectives `f_1` and `f_2` that get their values from the different surrogate models.
The objectives' surrogates are defined as lists of strings or a pyhton's pathlib.Path objects
that are paths to surrogate models that are stored on the disk. The surrogates can be left
empty, in which case when evaluating the problem using the
[`Evaluator`][desdeo.problem.simulator_evaluator.Evaluator], the evaluator needs the paths as
an argument to be able to evaluate the surrogate based objectives.

```python
objectives = [
    Objective(
        name="Objective 1",
        symbol="f_1",
        surrogates=[f"{path_to_surrogate_1_on_disk}"],
        maximize=False,
        objective_type=ObjectiveTypeEnum.surrogate
    ),
    Objective(
        name="Objective 2",
        symbol="f_2",
        surrogates=[f"{path_to_surrogate_2_on_disk}"],
        maximize=False,
        objective_type=ObjectiveTypeEnum.surrogate
    )
]
```

Surrogate based constraints and extra functions are defined similarly:

```python
constraints = [
    Constraint(
        name="Constraint 1",
        symbol="g_1",
        cons_type=ConstraintTypeEnum.LTE,
        surrogates=[f"{path_to_surrogate_3_on_disk}"],
    ),
    Constraint(
        name="Constraint 2",
        symbol="g_2",
        cons_type=ConstraintTypeEnum.LTE,
        surrogates=[f"{path_to_surrogate_4_on_disk}"],
    )
]

extra_functions = [
    ExtraFunction(
        name="Extra function 1",
        symbol="e_1",
        surrogates=[f"{path_to_surrogate_5_on_disk}"],
    ),
    ExtraFunction(
        name="Extra function 2",
        symbol="e_2",
        surrogates=[f"{path_to_surrogate_6_on_disk}"],
    )
]
```

!!! NOTE
    Since there are no function expressions that are given to an optimizer,
    surrogate based objectives, constraints and extra functions do not need
    linearity, convexity or differentiability to have the value `True` in any case.

Now we can define the `Problem` object.

```python
problem = Problem(
    name="Example surrogate based problem.",
    description="An example of a surrogate based problem.",
    variables=variables,
    objectives=objectives,
    constraints=constraints,
    extra_funcs=extra_functions
)
```
