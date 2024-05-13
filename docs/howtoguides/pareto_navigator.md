# How to use the Pareto Navigator method

## Introduction

Information.

## Setting up the problem

The implemented Pareto Navigator method is to be used used with a problem with a known approximation of the Pareto front.
This is because the method assumes a set of Pareto optimal solutions to get started.

To set up a problem, you can start with a problem object as described in ["How to define a problem"](./problem.md). Then you can add the approximation of the Pareto front as follows:

```python
from desdeo.problem.schema import DiscreteDefinition

dis_def = DiscreteDefinition(
    variable_values={
        "var_1_data": list_of_var_1_values,
        "var_2_data": list_of_var_2_values
        },
    objective_values={
        "obj_1_data": list_of_obj_1_values,
        "obj_2_data": list_of_obj_2_values
        },
)
```

You are now ready to use the Pareto Navigator method.

## Using the method

### Step 1: Import the relevant methods:

- `calculate_adjusted_speed` to determine the speed (step length) of the navigation. This method takes a list of allowed speeds, the desired speed and optionally a value to scale the speed. It returns an adjusted speed.
- `calculate_all_solutions` to compute a set number of solutions in the current direction. Takes the problem object, the currently navigated solution, the current speed, the number of solutions to compute, and preference information as either a reference point or classification.

```python

from desdeo.mcdm.pareto_navigator import (
    calculate_adjusted_speed,
    calculate_all_solutions
)
```

### Step 2: Initialization:

First define a list of allowed speeds and the desired speed to calculate the adjusted speed by calling `calculate_adjusted_speed`, and set the starting point, provided by the DM.

```python
allowed_speeds = [1, 2, 3, 4, 5]
speed = 1
adjusted_speed = calculate_adjusted_speed(allowed_speeds, speed)

# Set the starting point
current_solution = {
    "SomeObj": 1.38,
    "SomeOtherObj": 0.62,
    "YetAnotherObj": -35.33
}
```

### Step 3: Run the method:

Get preference information from the DM as either a reference point or classification, where `<` means the objective function value should improve, `>` means the objective function value may worsen and `=` means the objective function value should remain the same.
Run the method by calling `calculate_all_solutions` with the problem object, the currently navigated solution, the current speed, the number of solutions to compute, and the preference information.

```python
# Set parameters and preferences as classification
total_solutions = 200
preference_information = {
    "classification": {
        "SomeObj": "<",
        "SomeOtherObj": ">",
        "YetAnotherObj": "="
    }
}

# Run the method
solutions = calculate_all_solutions(problem, current_solution, adjusted_speed, num_solutions, preference_information)
```