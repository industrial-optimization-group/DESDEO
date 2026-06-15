# Scenarios

[Download as Jupyter notebook](https://raw.githubusercontent.com/industrial-optimization-group/DESDEO/master/notebooks/scenarios.ipynb)

One way of modeling uncertainty in decision making is using _scenarios_. A scenario in optimization context is typically a set of parameters or constraints that describes what our optimization problem might look like in a plausible future.

In DESDEO scenarios are described by a [ScenarioModel](../api/desdeo_problem.md#desdeo.problem.scenario.ScenarioModel). It contains base_problem that is a [Problem](../api/desdeo_problem.md#desdeo.problem.schema) object. The base_problem is then modified by the different [Scenario](../api/desdeo_problem.md#desdeo.problem.scenario.Scenario)s which are stored in a dict called scenarios. How different scenarios flow into one another is described by scenario_tree dict. The scenarios can also be assigned probabilities, which are stored in the scenario_probabilities dict.

## Building a ScenarioModel

We will take a look at how a [ScenarioModel](../api/desdeo_problem.md#desdeo.problem.scenario.ScenarioModel) is constructed with the help of an example. The first thing our ScenarioModel needs is a base_problem that will be modified by the different scenario.

We will use the [summer_cabin_electricity](../api/desdeo_problem.md#desdeo.problem.testproblems.summer_cabin_battery_problem) Problem as our base_problem. It is a MILP-problem with a few thousand variables. We will use the split version of the problem, where the decision variables relating to electricity usage have been split into three time periods. The reason for this will become apparent later.

```python
from pprint import pprint

from desdeo.problem.testproblems import summer_cabin_battery_problem_split

base = summer_cabin_battery_problem_split(initial_soc=0, n_panels_max=50)
pprint({i: base.objectives[i].name for i in range(len(base.objectives))})
```

```
{0: 'Electricity cost', 1: 'Investment cost'}
```

The problem is about choosing what kind of investments should be done in to the electricity supply of the summer cabin. The options are installing a battery with a capacity of 14-42 kWh or installing a number of solar panels that produce up to 160W of power each depending on the weather and the time of day.

### Defining scenarios

The type of uncertainty we want to introduce is the possibility of losing the connection to the power grid because of a storm. We have two storms that each may or may not cause an electricity outage for 4 hours.

To describe the scenarios arising from these possible events, we write a scenario_tree and put the scenario_probabilities in a dict.

```python
scenario_tree = {
    "ROOT": ["S1", "S2"],
    "S1": ["S1a", "S1b"],
    "S2": ["S2a", "S2b"],
    "S1a": [],
    "S1b": [],
    "S2a": [],
    "S2b": [],
}
scenario_probabilities = {
    "S1": 0.9,
    "S2": 0.1,
    "S1a": 0.81,
    "S1b": 0.09,
    "S2a": 0.09,
    "S2b": 0.01,
}

# Including the leaf nodes in the scenario tree is optional,
# so we can also define the scenario tree as follows:
scenario_tree = {
    "ROOT": ["S1", "S2"],
    "S1": ["S1a", "S1b"],
    "S2": ["S2a", "S2b"],
}
```

The `scenario_tree` is a dict, where the keys represent scenarios, and the values are lists that show which scenarios follow them. Leaf scenarios have an empty list, because there is no scenario following them. You can leave the leaf scenarios out of your scenario tree keys if you want.

The tree above shows that first either scenario `S1` or `S2` happens. They can then be followed by second stage scenarios `S1a` or `S1b` and `S2a` or `S2b` respectively.

If all of your scenarios would happen at the same time (from the perspective of the mathematical model), you would only have the `ROOT` scenario followed by a list of your scenarios. In that case, you could just provide the list of scenario names to the ScenarioModel instead a dict containing the tree.

The `scenario_probabilities` dict assigns a probability to every scenario in the `scenario_tree`. The ScenarioModel validates that the probabilities of child scenarios sum up to the probability of their parent.

### Describing the effects of the scenarios

We also need to describe how the scenarios change our `base_problem`. [ScenarioModel](../api/desdeo_problem.md#desdeo.problem.scenario.ScenarioModel) handles this by having lists of constants, variables, objectives, constraints, extra functions, and scalarization functions, which are then assigned to scenarios as need be. It works like this, because it is often desirable to use, for example, same constraints in multiple different scenarios, and having them all be drawn from a single lists saves space is computer memory and database.

We wanted to describe an electricity outage, so let's define constraints that say we cannot buy or sell electricity at specified times. We put one of these outages at the start of slices 2 and 3 of our timeseries variables.

```python
from desdeo.problem import Constraint, ConstraintTypeEnum

con_pool: list[Constraint] = []
con_idx: dict[str, int] = {}

H = 4  # hours of grid outage
for k in (2, 3):  # start of timeseries slices 2 and 3 are the outage periods
    c = Constraint(
        name=f"Outage no-trade s{k} t=1..{H}",
        symbol=f"outage_trade_s{k}",
        func=["Add", ["Extract", f"buy_s{k}", ["Tuple", 1, H]], ["Extract", f"sell_s{k}", ["Tuple", 1, H]]],
        cons_type=ConstraintTypeEnum.EQ,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
    con_idx[c.symbol] = len(con_pool)
    con_pool.append(c)
```

The summer cabin is not primarily a business, so the real impact of the electricity outages is not really measured in how they affect the costs associated. What is more important, is having access to electricity at the cabin.

### Adding objectives

To see, how for how many hours the cabin does not have enough electricity to meet the normal consumption, we are going to introduce a new objective function, that counts the hours when electricity demand is not met by either solar panels or battery storage.

```python
from desdeo.problem import Objective


def _f3(segments: tuple[int, ...]) -> Objective:
    z_terms = [["Sum", f"z_s{k}"] for k in segments]
    return Objective(
        name="Hours with unserved electricity demand",
        symbol="f_3",
        func=z_terms[0] if len(z_terms) == 1 else ["Add", *z_terms],
        unit="h",
        maximize=False,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )

obj_pool: list[Objective] = []
obj_idx: dict[str, int] = {}  # scenario name → pool index
for scenario_name, segs in [("S2a", (2,)), ("S1b", (3,)), ("S2b", (2, 3))]:
    obj_idx[scenario_name] = len(obj_pool)
    obj_pool.append(_f3(segs))
obj_idx["S1a"] = len(obj_pool)
obj_pool.append(
    Objective(
        name="Hours with unserved electricity demand",
        symbol="f_3",
        func=["Multiply", 0, "y"],  # always 0 — no outage possible in this scenario
        unit="h",
        maximize=False,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
)
```

The objective function has different values for all four scenarios. Of course, it would be possible in this problem to use the same objective function formulation for all scenarios, but that would require us to define the `z_sk` variables for all scenarios, and we do not really want to do that to keep the problem size smaller.

### Adding variables

Of course, we also need to add the variables `z_sk` that appear in the objective functions.

```python
from desdeo.problem import TensorVariable, Variable, VariableTypeEnum

var_pool: list[Variable] = []
var_idx: dict[str, int] = {}

for k in (2, 3):
    v = TensorVariable(
        name=f"Demand unserved indicator s{k}",
        symbol=f"z_s{k}",
        shape=[H],
        variable_type=VariableTypeEnum.binary,
        lowerbounds=0,
        upperbounds=1,
        initial_values=0,
    )
    var_idx[v.symbol] = len(var_pool)
    var_pool.append(v)
```

To have variables `z_sk` to actually indicate whether there is enough electricity or not, we are also going to need additional variables and constraints that implement that logic.

```python
_M_UNMET = 15.0  # kWh upper bound for big-M constraints (exceeds any single-hour load)

for k in (2, 3):
    v = TensorVariable(
        name=f"Unmet demand s{k} (kWh)",
        symbol=f"unmet_s{k}",
        shape=[H],
        variable_type=VariableTypeEnum.real,
        lowerbounds=0.0,
        upperbounds=None,
        initial_values=0.0,
    )
    var_idx[v.symbol] = len(var_pool)
    var_pool.append(v)

for k in (2, 3):
    c = Constraint(
        name=f"Energy balance s{k} t=1..{H} (with unmet slack)",
        symbol=f"energy_bal_out_s{k}",
        func=[
            "Add",
            ["Extract", f"d_s{k}", ["Tuple", 1, H]],           # discharging from battery
            ["Negate", ["Extract", f"c_s{k}", ["Tuple", 1, H]]],  # charging battery
            ["Multiply", "n", ["Extract", f"sol_s{k}", ["Tuple", 1, H]]],  # solar generation
            f"unmet_s{k}",                                      # unmet demand
            ["Negate", ["Extract", f"l_s{k}", ["Tuple", 1, H]]],  # load
        ],
        cons_type=ConstraintTypeEnum.EQ,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
    con_idx[c.symbol] = len(con_pool)
    con_pool.append(c)

for k in (2, 3):
    c = Constraint(
        name=f"Big-M unmet indicator s{k} t=1..{H}",
        symbol=f"bigm_s{k}",
        func=["Subtract", f"unmet_s{k}", ["Multiply", _M_UNMET, f"z_s{k}"]],
        cons_type=ConstraintTypeEnum.LTE,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
    con_idx[c.symbol] = len(con_pool)
    con_pool.append(c)
```

### Changing constraints

We also need to update the energy balance constraint for the scenarios where we have an outage. It does not include the unmet demand component and would lead to model infeasibility when electricity cannot be bought or sold and the battery and solar are not enough.

By using a same symbol that already exist in the base_problem for the Constraint (or any other Problem component), we are overwriting that constraint in the base problem. This only affects the scenarios that we include the constraint in.

```python
for k in (2, 3):
    c = Constraint(
        name=f"Energy balance s{k} t={H}+1.. (no unmet slack)",
        symbol=f"energy_bal_s{k}",
        func=[
            "Add",
            ["Exclude", f"buy_s{k}", ["Tuple", 1, H]],
            ["Negate", ["Exclude", f"sell_s{k}", ["Tuple", 1, H]]],
            ["Exclude", f"d_s{k}", ["Tuple", 1, H]],
            ["Negate", ["Exclude", f"c_s{k}", ["Tuple", 1, H]]],
            ["Multiply", "n", ["Exclude", f"sol_s{k}", ["Tuple", 1, H]]],
            ["Negate", ["Exclude", f"l_s{k}", ["Tuple", 1, H]]],
        ],
        cons_type=ConstraintTypeEnum.EQ,
        is_linear=True,
        is_convex=True,
        is_twice_differentiable=True,
    )
    con_idx[c.symbol] = len(con_pool)
    con_pool.append(c)
```

### Constructing the scenarios

Now we are ready to construct the [Scenario](../api/desdeo_problem.md#desdeo.problem.scenario.ScenarioModel) objects that describe which Variables, Constraints, and Objectives should be used in which scenario.

```python
from desdeo.problem import Scenario

# Dict mapping scenario names to the segments that are outaged in that scenario
_outage_segs: dict[str, tuple[int, ...]] = {"S1a": (), "S2a": (2,), "S1b": (3,), "S2b": (2, 3)}

scenarios: dict[str, Scenario] = {}
for name, segs in _outage_segs.items():
    variables: dict[str, int] = {}
    constraints: dict[str, int] = {}
    for k in segs:
        variables[f"unmet_s{k}"] = var_idx[f"unmet_s{k}"]
        variables[f"z_s{k}"] = var_idx[f"z_s{k}"]
        constraints[f"energy_bal_s{k}"] = con_idx[f"energy_bal_s{k}"]
        constraints[f"energy_bal_out_s{k}"] = con_idx[f"energy_bal_out_s{k}"]
        constraints[f"bigm_s{k}"] = con_idx[f"bigm_s{k}"]
        constraints[f"outage_trade_s{k}"] = con_idx[f"outage_trade_s{k}"]
    scenarios[name] = Scenario(
        variables=variables,
        objectives={"f_3": obj_idx[name]},
        constraints=constraints,
    )
```

### Defining anticipation stop

The last thing we need to define in our [ScenarioModel](../api/desdeo_problem.md#desdeo.problem.scenario.ScenarioModel) is anticipation stop. It describes which scenarios are allowed to affect values of the listed Variables. The scenario under which the Variable is listed is the last scenario that can affect the value of the Variable. Thus, Variables listed under `"ROOT"` must have the same values in all scenarios. Variables listed under `"S2"` must have the same value in all scenarios that follow `"S2"`, and so on.

In this summer cabin electricity problem, the decisions associated with time before the first possible electricity outage must all have the same values in all scenarios. The decision variables that follow the first potential outage can have their values depend on whether that outage happened, but they cannot depend on the second outage happening.

```python
investments = ["y", "E", "n"]
s1_sched = ["c_s1", "d_s1", "soc_s1", "buy_s1", "sell_s1"]
s2_sched = ["c_s2", "d_s2", "soc_s2", "buy_s2", "sell_s2"]
s2_unmet = ["unmet_s2", "z_s2"]

anticipation_stop = {
    "ROOT": [*investments, *s1_sched],
    "S1": s2_sched,  # no unmet demand variables since no outage in S1
    "S2": [*s2_sched, *s2_unmet],
}
```

### Ready scenario model

Now we just put the scenario model together.

```python
from desdeo.problem.scenario import ScenarioModel

summer_cabin_scenarios = ScenarioModel(
    scenario_tree=scenario_tree,
    scenario_probabilities=scenario_probabilities,
    base_problem=base,
    variables=tuple(var_pool),
    objectives=tuple(obj_pool),
    constraints=tuple(con_pool),
    scenarios=scenarios,
    anticipation_stop=anticipation_stop,
)
```

# Using scenario models

Currently, there are two ways of using scenario models withing DESDEO: constructing Problems corresponding to individual scenarios and building aggregate problems consisting of multiple scenarios.

You can construct individual scenario problems by calling the `get_scenario_problem` function. This is unlikely to be that useful on its own, but can be useful for sanity checks or for constructing more complex methods.

```python
from desdeo.tools import guess_best_solver

scenario_2b = summer_cabin_scenarios.get_scenario_problem("S2b")
results = guess_best_solver(scenario_2b)(scenario_2b).solve("f_1")
pprint(results.optimal_objectives)
```

```
{'f_1': -170.38648708994592, 'f_2': 25020.0, 'f_3': 8.0}
```

Likely a more useful way to utilize scenario models is by using one of the implemented aggregation methods that combine multiple scenarios into a single multiobjective optimization problem.

```python
import inspect
import desdeo.tools.stochastic as mod

for name, obj in inspect.getmembers(mod, inspect.isfunction):
    if obj.__module__ == mod.__name__:
        pprint(f"{name}")

import desdeo.tools.robust as mod

for name, obj in inspect.getmembers(mod, inspect.isfunction):
    if obj.__module__ == mod.__name__:
        pprint(f"{name}")

del mod
```

```
'add_conditional_value_at_risk'
'add_expected_asf'
'add_expected_value'
'add_weighted_scenarios'
'add_worst_case_robust'
```

The way these aggregation functions work is they construct one big scenario model using [build_combined_scenario_problem](../api/desdeo_tools.md#desdeo.tools.scenarios.build_combined_scenario_problem) and then add aggregation functions that combine the values from multiple scenarios into a single function expression.

Let us look at the [add_expected_value](../api/desdeo_tools.md#desdeo.tools.stochastic.add_expected_value) as an example.

```python
from desdeo.tools import add_expected_value

# We want to compute the expected value of all three objectives across the scenarios
combined_ev_problem, new_symbols = add_expected_value(
    scenario_model=summer_cabin_scenarios, symbols=["f_1", "f_2", "f_3"])

pprint([o.name for o in combined_ev_problem.objectives])
```

```
['Hours with unserved electricity demand (S1a_f_3)',
 'Hours with unserved electricity demand (S2b_f_3)',
 'Hours with unserved electricity demand (S1b_f_3)',
 'Hours with unserved electricity demand (S2a_f_3)',
 'Electricity cost (S1a_f_1)',
 'Electricity cost (S2b_f_1)',
 'Electricity cost (S1b_f_1)',
 'Electricity cost (S2a_f_1)',
 'Investment cost (f_2)',
 'Expected value of f_1',
 'Expected value of f_2',
 'Expected value of f_3']
```

As we can see, our `combined_ev_problem` has a total of 12 objectives including the expected values of the three original objective functions. It is unlikely anyone is going to care about all these 12 objectives that much, especially considering how similar they are. Thus, to find a solution that a decision maker might be interested in, we are using partial scalarization, that only uses a subset of the objectives.

```python
from desdeo.tools import CVXPYSolver, add_asf_partial_diff, payoff_table_method

# Calculate ideal and nadir values, so that the ASF can be properly scaled
ideal, nadir = payoff_table_method(combined_ev_problem, CVXPYSolver)
combined_ev_problem = combined_ev_problem.update_ideal_and_nadir(ideal, nadir)
pprint(ideal)
pprint(nadir)
```

```
{'E_f_1': -170.2034948424482,
 'E_f_2': 0.0,
 'E_f_3': 0.0,
 'S1a_f_1': -170.2157368877032,
 'S1a_f_3': 0.0,
 'S1b_f_1': -171.05123923339914,
 'S1b_f_3': 0.0,
 'S2a_f_1': -169.55098474424992,
 'S2a_f_3': 0.0,
 'S2b_f_1': -170.38648708994592,
 'S2b_f_3': 0.0,
 'f_2': 0.0}
{'E_f_1': 284.1993394723681,
 'E_f_2': 25020.0,
 'E_f_3': 0.7999999999999998,
 'S1a_f_1': 284.3543099288125,
 'S1a_f_3': 0.0,
 'S1b_f_1': 283.8928728809143,
 'S1b_f_3': 4.0,
 'S2a_f_1': 283.17025631593975,
 'S2a_f_3': 4.0,
 'S2b_f_1': 287.78745536436577,
 'S2b_f_3': 8.0,
 'f_2': 25020.0}
```

```python
reference_point = {'E_f_1': 0, 'E_f_2': 5000.0, 'E_f_3': 0}
asf_problem, symbol = add_asf_partial_diff(combined_ev_problem, symbol="ASF", reference_point=reference_point)

solver = CVXPYSolver(asf_problem)
results = solver.solve(symbol)

pprint(results.optimal_objectives)
```

```
{'E_f_1': 83.92565751178836,
 'E_f_2': 9621.053814752766,
 'E_f_3': 0.09999999999999999,
 'S1a_f_1': 83.86840202796994,
 'S1a_f_3': 0.0,
 'S1b_f_1': 83.37371196251193,
 'S1b_f_3': 1.0,
 'S2a_f_1': 84.65288793569992,
 'S2a_f_3': 0.0,
 'S2b_f_1': 86.98578782937489,
 'S2b_f_3': 1.0,
 'f_2': 9621.053814752766}
```

### Adding multiple aggregation functions

It is also possible add multiple scenario aggregation functions into the same problem. If you want to do that, you need to handle the combined scenario manually, because otherwise the aggregation functions have no way to figure out what is part of the original base problem and what was added later. In the example below we add worst case robust aggregation and expected value aggregation into the summer cabin problem.

```python
from desdeo.tools import add_worst_case_robust, build_combined_scenario_problem

combined_problem, symbol_maps = build_combined_scenario_problem(summer_cabin_scenarios)
combined_problem, added = add_worst_case_robust(
    scenario_model=summer_cabin_scenarios,
    symbols=["f_1", "f_2", "f_3"],
    combined=combined_problem,
    symbol_maps=symbol_maps,
)
combined_problem, added2 = add_expected_value(
    scenario_model=summer_cabin_scenarios,
    symbols=["f_1", "f_2", "f_3"],
    combined=combined_problem,
    symbol_maps=symbol_maps,
)

# Calculate ideal and nadir values, so that the ASF can be properly scaled
ideal, nadir = payoff_table_method(combined_problem, CVXPYSolver)
combined_problem = combined_problem.update_ideal_and_nadir(ideal, nadir)
pprint(ideal)
pprint(nadir)
```

```
{'E_f_1': -170.20349484244818,
 'E_f_2': 0.0,
 'E_f_3': 0.0,
 'S1a_f_1': -170.2157368877032,
 'S1a_f_3': 0.0,
 'S1b_f_1': -171.05123923339914,
 'S1b_f_3': 0.0,
 'S2a_f_1': -169.55098474424992,
 'S2a_f_3': 0.0,
 'S2b_f_1': -170.38648708994592,
 'S2b_f_3': 0.0,
 'f_2': 0.0,
 'robust_f_1': -169.42350644620245,
 'robust_f_2': 0.0,
 'robust_f_3': 0.0}
{'E_f_1': 285.57658537379876,
 'E_f_2': 25020.0,
 'E_f_3': 0.7999999999999998,
 'S1a_f_1': 285.46864783024233,
 'S1a_f_3': 0.0,
 'S1b_f_1': 286.0099468786688,
 'S1b_f_3': 4.0,
 'S2a_f_1': 285.74519421736943,
 'S2a_f_3': 4.0,
 'S2b_f_1': 288.9017932657958,
 'S2b_f_3': 8.0,
 'f_2': 25020.0,
 'robust_f_1': 289.0,
 'robust_f_2': 25020.0,
 'robust_f_3': 8.0}
```

As seen above, the number of objective functions is quite large now. We can once again solve the problem using partial scalarization. Let's say we care about the expected value for the electricity costs, the cost of investments, and the maximum value of hours without electricity.

```python
reference_point = {'E_f_1': 0, 'f_2': 5000.0, 'robust_f_3': 0}
asf_problem, symbol = add_asf_partial_diff(combined_problem, symbol="ASF", reference_point=reference_point)

solver = CVXPYSolver(asf_problem)
results = solver.solve(symbol)

pprint(results.optimal_objectives)
```

```
{'E_f_1': 83.96907117794157,
 'E_f_2': 9609.47341067498,
 'E_f_3': 0.09999999999999999,
 'S1a_f_1': 83.97957085314236,
 'S1a_f_3': 0.0,
 'S1b_f_1': 83.38759433961908,
 'S1b_f_3': 1.0,
 'S2a_f_1': 84.46655061465756,
 'S2a_f_3': 0.0,
 'S2b_f_1': 83.87457410113473,
 'S2b_f_3': 1.0,
 'f_2': 9609.473410674978,
 'robust_f_1': 84.46655061465756,
 'robust_f_2': 9609.473410674978,
 'robust_f_3': 1.0}
```
