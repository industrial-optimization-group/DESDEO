# How to use the NAUTILUS Navigator method

## Introduction

Information about the method.

## Setting up the problem

While the implemented NAUTILUS Navigator method can be used for any kind of problem (analytical, data-based, etc.), it
is recommended to be used with a data-based problem. More specifically, it is recommended to be used with a problem with
a known approximation of the Pareto front. This is because the method conducts many optimization runs for each step.
While optimization on an approximation of a Pareto front is quick and easy, optimization on simulation based problem or
even just analytical problems can be very time consuming. You can use other methods in this framework to find an
approximation of the Pareto front.

To set up a problem, you can start with a problem object as described in ["How to define a problem"](howtoguides/problem.md). Then you can add the approximation of the Pareto front as follows:

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

You are now ready to use the NAUTILUS Navigator method.

## Using the method

### Step 1: Import the relevant methods:

- `navigator_init` to initialize the method. This method takes the problem object and creates the initial reachable ranges.
- `navigator_all_steps` to run the method until the Pareto front is reached. This method takes the problem object, the return value of `navigator_init`, the number of steps to take, and a reference point. It returns information about all the steps taken as a list of `NAUTILUS_Response` objects.
- `NAUTILUS_Response` is the object that contains information about the step taken. It is returned by `navigator_init` (single object) and `navigator_all_steps` (as a list). It contains the following fields:
    - `step`: The step number.
    - `distance_to_front`: The relative distance to the Pareto front at the end of the step. This is calculated as the ratio of the distance between the `navigation_point` and `reachable_solution` and the distance between the `navigation_point` and the `nadir point`.
    - `navigation_point`: The point from which the lower and upper reachable bounds are calculated for the current step.
    - `reachable_solution`: The reachable solution at the end of the current path.
    - `reachable_bounds`: The reachable ranges at the current step.
    - `reference_point`: The reference point used in the step.
- `step_back_index` and `get_current_path` are explained later.

```python

from desdeo.mcdm.nautilus_navigator import (
    navigator_init,
    navigator_all_steps,
    NAUTILUS_Response,  # You don't actually need to import this, but it is useful to know the structure of the return value of navigator_all_steps
    step_back_index,
    get_current_path
)
```

### Step 2: Initialize the method:

Initialize the method by calling `navigator_init` with the problem object.

```python
initial_response = navigator_init(problem)
```

At this point, the analyst may use the `initial_response` to visualize the reachable ranges and the reachable solutions to the DM. Get the aspiration levels from the DM as a dictionary with the objective names as keys and the aspiration levels as values.

### Step 3: Run the method:

Run the method by calling `navigator_all_steps` with the problem object, the return value of `navigator_init`, the number of steps to take, and the aspiration levels.

```python
# Set preferences and parameters
reference_point = {
    "SomeObj": 0.5,
    "SomeOtherObj": 200.5,
    "YetAnotherObj": -22,
}
total_steps = 100

# Run the method
all_responses: list[NAUTILUS_Response] = navigator_all_steps(
    problem,
    total_steps,
    reference_point,
    [initial_response] # Note that this is a list of NAUTILUS_Response objects
)

# Append the responses to the archive of responses
all_responses = [initial_response, *all_responses]
```

At this point, the analyst may use the `all_responses` to visualize the reachable ranges and the reachable solutions of each step to the DM. Even though all steps have been evaluated at this point, the analyst (or the GUI) should only visualize this steps one at a time, at a certain rate (say, 1 step per second). This will allow the DM to think that they are navigating the solution space without it consuming too much time.

One way to get the information to be visualized:

```python
lower_bounds = pl.DataFrame(
    [response.reachable_bounds["lower_bounds"] for response in all_responses]
)
upper_bounds = pl.DataFrame(
    [response.reachable_bounds["upper_bounds"] for response in all_responses]
)
reference_point = pl.DataFrame(
    [response.reference_point for response in all_responses[1:]]
)
```

This will give you the lower and upper bounds of the reachable ranges and the reference points used in each step as a DataFrame.

> !!! Note
> Maximization is already handled in all of these steps. You should provide the real (meaningful) values of the objectives to the method. The method will handle the maximization internally. Similarly, the returned values are already the true objective values and can be visualized to the DM as directly.

### Step 4: Take a step back

Let's say that the DM wants to take a step back to a previous step. It does not matter when they make this choice, the `all_responses` list already contains all possible steps. The analyst should copy the response from the step that the DM wants to go back to and append it to the `all_responses` list. Then, `navigator_all_steps` can be called with the new aspiration levels and the number of remaining steps.

```python
go_back_to = 3
steps_remaining = total_steps - go_back_to

reference_point = {
    "SomeObj": 4.5,
    "SomeOtherObj": 100.5,
    "YetAnotherObj": -2,
}

all_responses = [
    *all_responses,
    all_responses[step_back_index(all_responses, go_back_to)],
]

new_responses = navigator_all_steps(
    problem, steps_remaining, reference_point, all_responses, create_proximal_solver
)

all_responses = [*all_responses, *new_responses]
```

Note, as all responses are appended to the same list, finding out the index of the step to go back to is not trivial. The `step_back_index` function can be used to find the index of the step to go back to. It finds all responses that have a `step_number` equal to the `go_back_to` and returns the index of the last such response. This is because the last such response is the one that was appended to the `all_responses` list most recently.

Moreover, the `get_current_path` function can be used to get the current path of the method. This is useful for visualizing the current path to the DM.

```python
current_path = get_current_path(all_responses)
responses_to_visualize = [all_responses[i] for i in current_path]
```

