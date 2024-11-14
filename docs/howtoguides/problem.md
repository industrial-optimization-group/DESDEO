# Defining multiobjective optimization problems
There are multiple types of problems that may be defined in DESDEO. Here,
examples on how to define each type of problem are provided. To understand
how problems are modelled in DESDEO, please refer to
[the problem format explanation](../explanation/problem_format.md).

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

## Example: simulation-based problem (WIP)

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

!!! NOTE
    Since there are no function expressions that are given to an optimizer,
    simulator based objectives do not need linearity, convexity or differentiability
    to have the value `True` in any case.

Similarly, we can define constraints and extra functions.
