# How to use the Nonconvex Pareto Navigator method

## Introduction

This is a how-to guide to use the Pareto Navigator method.
The method is implemented according to the description in [1].

## Setting up the problem

The implemented Nonconvex Pareto Navigator method is to be used used with a problem with a known approximation of the Pareto front.
This is because the method assumes a set of Pareto optimal solutions to get started.

## Using the method

To set up a problem, you can start with a problem object as described in ["How to define a problem"](./problem.md). Then you can add the approximation of the Pareto front as follows:

```python
from desdeo.problem import DiscreteDefinition

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

You are now ready to use the Nonconvex Pareto Navigator method.

### Step 1: Import the relevant methods:

- `calculate_adjusted_speed` to determine the speed (step length) of the navigation. This method takes a list of allowed speeds, the desired speed and optionally a value to scale the speed. It returns an adjusted speed.
- `calculate_all_solutions` to compute a set number of solutions in the current direction. Takes the problem object, the currently navigated solution, the current speed, the number of solutions to compute, and preference information as either a reference point or classification.
- `create_milp` to create a surrogate mixed integer linear problem based on a PAINT approximation to be solved instead of the original problem.
- `e_cones` to compute matrix V to be used to form the e-cones to make navigation possible on nonconvex Pareto fronts.
- `get_corrected_solutions` to correct the objective values of the solutions in case some of the objectives are to be maximized.
- `get_paint_approximation` to compute the PAINT approximation.

```python

from desdeo.mcdm.pareto_navigator import (
    calculate_adjusted_speed
)

from desdeo.mcdm.nonconvex_pareto_navigator import (
    calculate_all_solutions,
    create_milp,
    e_cones,
    get_corrected_solutions,
    get_paint_approximation
)
```

### Step 2: Initialization:

First, generate the PAINT approximation and use it to form the surrogate mixed integer linear problem:

```python
approximation = get_paint_approximation(problem)

milp = create_milp(problem, approximation)
```

Use the formed surrogate problem to compute some approximated solutions to compute the e-cones:

```python
starting_point = {
    "SomeObj": 16.1,
    "SomeOtherObj": 421,
    "YetAnotherObj": 42
}
preference_information = {
    "bounds": {
        "SomeObj": 16.1,
        "SomeOtherObj": 452,
        "YetAnotherObj": 49
    },
    "reference_point": {
        "SomeObj": 15.1,
        "SomeOtherObj": 427,
        "YetAnotherObj": 43
    }
}

solutions = calculate_all_solutions(milp, starting_point, preference_information, adjusted_speed, num_solutions=100)
cones = e_cones(milp, solutions)
```

Then form a new surrogate problems in which the e-cones are utilized:

```python
milp = create_milp(milp, approximation, cones)
```

Then, to initialize the navigation itself, define a list of allowed speeds and the desired speed to calculate the adjusted speed by calling `calculate_adjusted_speed`, and set the starting point, provided by the DM.

```python
allowed_speeds = [1, 2, 3, 4, 5]
speed = 1
adjusted_speed = calculate_adjusted_speed(allowed_speeds, speed)

# Set the starting point
current_solutions = {
    "SomeObj": 16.1,
    "SomeOtherObj": 421,
    "YetAnotherObj": 42
}
```

### Step 3: Run the method:

Get preference information from the DM as either a reference point and bounds. The DM may choose for which objectives they would like to set (upper) bounds. The DM can also choose not to set any bounds. Run the method by calling `calculate_all_solutions` with the surrogate problem object, the currently navigated solution, the preference information, the current speed, and the number of solutions to compute. If some of the objectives are to be maximized, run the `get_corrected_solutions` method.

```python
# Set parameters and preferences as classification
total_solutions = 200
preference_information = {
    "bounds": {
        "SomeObj": 16.1,
        "SomeOtherObj": 452,
        "YetAnotherObj": 49
    },
    "reference_point": {
        "SomeObj": 15.1,
        "SomeOtherObj": 427,
        "YetAnotherObj": 43
    }
}

# Run the method
solutions = calculate_all_solutions(milp, current_solution, preference_information, adjusted_speed, num_solutions=100)

# In case some objectives are to be maximized, use the original problem
corrected_solutions = get_corrected_solutions(problem, solutions)
```

## References

[1]: Hartikainen, M., Miettinen, K., & Klamroth, K. (2019). Interactive nonconvex pareto navigator for multiobjective optimization. European Journal of Operational Research, 275(1), 238-251.