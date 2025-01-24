# How to use the NAUTILI method

## Introduction

NAUTILI is a trade-off-free interactive method developed for supporting multiple decision makers with conflicting preferences in solving multiobjective optimization problems.

## Setting up the problem

todo lang
While the implemented NAUTILI can be used for any kind of problem (analytical, data-based, etc.), it
is recommended to consider the computational complexity of the objective functions would not be too high as the whole group must wait each iteration for the computations. Other option is to use  
other methods in this framework to find an approximation of the Pareto front. This approximation can be used to make iterations faster.

To set up a problem, you can start with a problem object as described in ["How to define a problem"](./problem.md). Or you can use any of the existing test problems in DESDEO. Let us say that we have a group of five forest experts that wish to decide together how they want to manage their jointly owned forest holding. The problem is simulation based and therefore, to ease the computational costs, we use an approximation of the Pareto front. Very conveniently for our forest owners, this problem already exists as a testproblem in DESDEO:

Before starting the solution process, 
the group has to agree upon the number of steps they wish to conduct and how many votes are required to conduct a step backwards. For the sake of the example, the group wishes to take 3 steps and majority (3) is required to take a step backwards. 
```python
from desdeo.problem.testproblems import forest_problem_discrete
TODO: update this
forest_problem = forest_problem_discrete() # or use forest_problem()
total_steps = 5
```


The problem has 3 objective functions. Objective 1 is called "stock" for the volume of wood stock in the forest. Objective 2 is called "harvest_value", meaning the value in euros that will be gained by harvesting the forest according to the plan.
Objective 3 is "npv", meaning net percent value of the currently standing forest.
You are now ready to use the NAUTILI method.

## Using the method

### Step 1: Import the relevant methods:

- `nautili_init` to initialize the method. This method takes the problem object and creates the initial reachable ranges.
- `nautili_all_steps` to run the method until the Pareto front is reached. This method takes the problem object, the return value of `nautili_init`, the number of steps to take, and reference points from all DMs. It returns information about all the steps taken as a list of `NAUTILI_Response` objects.
- `NAUTILUS_Response` is the object that contains information about the step taken. It is returned by `nautili_init` (single object) and `nautili_all_steps` (as a list). It contains the following fields:
    - `step_number`: The step number.
    - `distance_to_front`: The relative distance to the Pareto front at the end of the step. This is calculated as the ratio of the distance between the `navigation_point` and `reachable_solution` and the distance between the `navigation_point` and the `nadir point`.
    - `navigation_point`: The point from which the lower and upper reachable bounds are calculated for the current step.
    - `reachable_solution`: The reachable solution at the end of the current path.
    - `reachable_bounds`: The reachable ranges at the current step.
    - `reference_points`: The reference points used in the step.
    - `improvement_directions`: The improvement directions for each DM.
    - `group improvement direction`
```python

from desdeo.mcdm.nautili import (
    nautili_init,
    nautili_all_steps,
    NAUTILI_Response,  # You don't actually need to import this, but it is useful to know the structure of the return value of nautili_all_steps
)

from desdeo.mcdm.nautilus_navigator import (
    step_back_index, # we need this utility function
)

```

### Step 2: Initialize the method:

Initialize the method by calling `nautili_init` with the problem object.

```python
initial_response = nautili_init(problem)
```

At this point, the analyst may use the `initial_response` to visualize the reachable ranges and the reachable solutions to the DMs. Get the aspiration levels from the DMs as a dictionary with a key to indicate each DM's dictionary containing objective names as keys and the aspiration levels as values.

### Step 3: Run the method:

Run the method by calling `nautili_all_steps` with the problem object, the return value of `nautili_init`, the number of steps to take, and the aspiration levels. You can also provide your preferred solver, using the BaseSolver class.

```python
# Set preferences and parameters
reference_points = {
  "DM1": {
    "stock": 0.5,
    "harvest_value": 200.5,
    "npv": -22,
  },
  "DM2": {
    "stock": 0.5,
    "harvest_value": 200.5,
    "npv": -22,
  },
  "DM3": {
    "stock": 0.5,
    "harvest_value": 200.5,
    "npv": -22,
  },
  "DM4": {
    "stock": 0.5,
    "harvest_value": 200.5,
    "npv": -22,
  },
  "DM5": {
    "stock": 0.5,
    "harvest_value": 200.5,
    "npv": -22,
  },
}
total_steps = 5

# Run the method
all_responses: list[NAUTILI_Response] = nautili_all_steps(
    forest_problem,
    total_steps,
    reference_points,
    [initial_response] # Note that this is a list of NAUTILI_Response objects
)

# Append the responses to the archive of responses
all_responses = [initial_response, *all_responses]
```

At this point, the analyst may use the `all_responses` to visualize the reachable ranges and the reachable solutions of each step to each of the DMs. Even though all steps have been evaluated at this point, the analyst (or the GUI) should only visualize this steps one at a time, at a certain rate (say, 1 step per second). This will allow the DM to think that they are navigating the solution space without it consuming too much time.
Note, that according to the NAUTILI assumptions, we do not share the prefeferences of any DM to any other DM. HOwever, if sharing of preference information is reasonable in you problem scenario, the analyst can share them e.g., via the GUI as a separate visualization. 

One way to get the information to be visualized: 

```python

lower_bounds = pl.DataFrame(
    [response.reachable_bounds["lower_bounds"] for response in all_responses]
)
upper_bounds = pl.DataFrame(
    [response.reachable_bounds["upper_bounds"] for response in all_responses]
)
reference_point = pl.DataFrame(
    [response.reference_points for response in all_responses[1:]]
)

print(f"lower, upper bounds {lower_bounds}, {upper_bounds} and reference_point {reference_point}")

```

This will give you the lower and upper bounds of the reachable ranges and the reference points used in each step as a DataFrame.

> !!! Note
> Maximization is already handled in all of these steps. You should provide the real (meaningful) values of the objectives to the method. The method will handle the maximization internally. Similarly, the returned values are already the true objective values and can be visualized to the DM as directly.


The analyst can also access the group improvement directions from the NAUTILI_Response:


### Step 4: Take a step back

At any iteration (except the first one), the DMs have the option to begin a vote for taking a step backwards in the method. After a vote has been initiated, every DM can vote for it or against it. The voting can be implemented in the GUI or the analyst can manually gather the votes from the DMs.
Let us say that in our case, 4 DMs wish to take a step backwards, hence, according to the majority threshold set earlier, we take a step backwards. 

It does not matter when they make this choice, the `all_responses` list already contains all possible steps. The analyst should copy the response from the step that the group wants to go back to and append it to the `all_responses` list. Then, `nautili_all_steps` can be called with the new aspiration levels and the number of remaining steps. All DMs who wish to change their preferences can do so, and if any DM do not wish to change their preference, the earlier preference of that DM can be used instead.
```python
go_back_to = 3
steps_remaining = total_steps - go_back_to

# Set preferences and parameters
reference_points = {
  "DM1": {
    "stock": 2800,
    "harvest_value": 30000,
    "npv": 80000,
  },
  "DM2": {
    "stock": 3000,
    "harvest_value": 25200.5,
    "npv": 76500,
  },
  "DM3": {
    "stock":2900,
    "harvest_value": 50005,
    "npv": 90000,
  },
  "DM4": {
    "stock": 3100,
    "harvest_value": 22000,
    "npv": 90000,
  },
  "DM5": {
    "stock": 3200,
    "harvest_value": 29000,
    "npv": 76000,
  },
}

all_responses = [
    *all_responses,
    all_responses[step_back_index(all_responses, go_back_to)],
]

new_responses = nautili_all_steps(
    forest_problem, steps_remaining, reference_points, all_responses, #create_proximal_solver
)

all_responses = [*all_responses, *new_responses]


```

Note, as all responses are appended to the same list, finding out the index of the step to go back to is not trivial. The `step_back_index` function can be used to find the index of the step to go back to. It finds all responses that have a `step_number` equal to the `go_back_to` and returns the index of the last such response. This is because the last such response is the one that was appended to the `all_responses` list most recently.

Moreover, the `get_current_path` function can be used to get the current path of the method. This is useful for visualizing the current path to each DM. # TODO: this could be useful

```python
current_path = get_current_path(all_responses)
responses_to_visualize = [all_responses[i] for i in current_path]
```


The next iteration after we changed preferences contains the group group_improvement_direction that is used for all subsequent iterations as the DMs do not change their preferences:

```
gid2 = all_responses[step_back_index(all_responses, go_back_to)+1].group_improvement_direction
print(f"Group improvement direction {gid2}")
```


Moreover, the Pareto optimal solution reached can be found from the NAUTILI_Response:

```
fs = all_responses[-1].reachable_solution
print(f"Final reachable solution {fs}")```

```

