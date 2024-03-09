# Scalarization

One approach to solve multiobjective optimization problems is to
_scalarize_ them. Scalarization transforms a multiobjective
optimization problem into a single-objective optimization
problem, which can be solved with one of the many existing
optimizers. DESDEO has interfaces to existing
optimizers, which are discussed in the section [Solvers](./solvers.md).

Here, we will first explain how scalarization is implemented in DESDEO
in the section [Scalarizing problems](#scalarizing-problems),
and we will then provide a couple of illustrative examples of
scalarization in the section [Scalarization examples](#scalarization-examples).

## Scalarizing problems

The core idea of scalarization in DESDEO is that scalarization functions
are added to an existing [Problem][desdeo.problem.schema.Problem], and they are
stored in its [scalarization_funcs][desdeo.problem.schema.Problem.scalarization_funcs] field.
When a scalarization function is added to a problem, it does not modify the original
problem, instead, functions that add scalarizations return always a copy of the
problem with the added scalarization, and possibly other elements, such as constraints.

When adding scalarization functions, it is very important to keep track of the added
scalarization's [symbol][desdeo.problem.schema.ScalarizationFunction.symbol]. This
is utilized, later on, in solver, and must be supplied to the solver so that
it is aware of the function it should optimize. This is why the functions that
add scalarizations return also the symbol that has been used when defining
the [ScalarizationFunction][desdeo.problem.schema.ScalarizationFunction] that
has been added to the problem.

There is one last important note about scalarization functions. All scalarization
functions are defines with the assumption that all of the objective functions,
and elements related to the objective function values, e.g., the ideal and the nadir point,
a possible reference point, have been defined such that the objective functions
are to be minimized. This means that the scalarization function implementation
will refer to objective functions with the `_min` post-fix. E.g., a scalarization
function will refer to an objective function `f_1` as `f_1_min`. __It is 
the responsibility of the evaluators found in DESDEO to make sure that the
reference to `f_1_min` is available at time of evaluation.__
This naturally means that scalarizations should be added to a problem _before_
they are evaluated and solved.

!!! note
    Scalarization functions assume that each objective function is to be minimized.
    This should be reflected in any other values that depend on whether an objective
    is to be maximized or minimized, such as the ideal and nadir points, or a 
    reference point!

## Scalarization examples

Here, we will showcase how adding scalarization function to a problem
looks like in practice in DESDEO.

### The non-differentiable achievement scalarizing function

To add the non-differentiable variant of the
[achievement scalarizing function](../tutorials/moo_primer.md/#def:asf),
we invoke the following code:

```python
from desdeo.tools import add_asf_nondiff

# a Problem with the objectives 'f_1', 'f_2', 'f_3'
problem: Problem 
# a reference point with an aspiration level for each objective function
reference_point = {"f_1": 5.9, "f_2": 4.2, "f_3": -1.6}

problem_w_asf, target = add_asf_nondiff(
    problem,
    symbol="target",
    reference_point=reference_point
    )
```

In the above example, we have assumed that `Problem` has three objective functions
named `f_1, f_2`, and `f_3`. We have also provided a reference point for the sake
of example. The pattern of providing a reference point as a `dict` is a recurring
theme when supplying any information with elements that correspond to individual
objective functions. As for the arguments passed to `add_asf_nondiff`, the
first argument is the problem the scalarization should be added to, the second
is the symbol given to the added scalarization function, and the reference point
contains the aspiration levels to be used in the scalarization. The function
then returns a copy of the original problem, `problem_w_asf` that contains
now the added scalarization. It also returns the symbol of the added scalarization
function, which in this case is just `target`.

It is important to keep track of the symbol given to the scalarization function added,
because it will be needed when solving the problem. For this reason, the symbol
is returned as well, even though it may seem redundant. Naming the symbol
of an added scalarization function to be the `target` is a good pattern to follow, since
we often add just a single scalarization function to a problem, and then solve it.
The name `target` reminds us that it is the function we wish to optimize once we
have scalarized the problem.

One last note on the example given. Here, we have utilized the _non-differentiable_
variant of the achievement scalarizing function. This means that it will contain
a `max` term, which is generally not differentiable. One should therefore
exercise caution when utilizing the non-differentiable variant, because if the
scalarized problem would otherwise be differentiable, we lose this property if we
use a non-differentiable scalarization function.

!!! warning
    When adding scalarization functions to problems, be mindful of the mathematical
    properties of the functions defined in the problem (e.g., the objective functions
    and constraints) and those of the scalarization function itself. Using an improper
    scalarization can lead to a scalarized problem that has lost some "nice"
    properties of the original problem, such as differentiability.

### The epsilon-constraints scalarization

As a more complicated example on how scalarizations might have to be added,
consider the epsilon-constraints scalarization. Here, we have to also
add constraint functions to the problem. Luckily, in practice, this
is quite straight-forward, as illustrated below:

```python
from desdeo.tools import add_epsilon_constraints

# a Problem with the objectives 'f_1', 'f_2', 'f_3'
problem: Problem 
# a reference point with an aspiration level for each objective function
epsilons = {"f_1": 5.9, "f_2": 4.2, "f_3": -1.6}
epsilon_symbols = {"f_1": "eps_1", "f_2": "eps_2", "f_3": "eps_3"}

problem_w_eps, target, constraint_symbols = add_epsilon_constraints(
    problem,
    symbol="target",
    constraint_symbols=epsilon_symbols,
    objective_symbol="f_2",
    epsilons=epsilons
)
```

In the above code example, we have the same problem as before, but now we have
also the epsilon bounds for each objective function in `epsilons`, and the
symbols to be given to the added constraints in `epsilon_symbols` (the argument
in `constraint_symbols` in `add_epsilon_constraint`). Since the bounds and
constraint symbols are related to the objective functions, they have been given
in a `dict` with the keys being the symbols of the respective objective
functions. The objective function to be actually minimized in the epsilon-constraints
scalarization is passed as `objective_symbol`, which in this case if `f_2`.
Therefore, there will be no constraint for the objective `f_2`, and the entries
with the key `f_2` in `epsilons` and `epsilon_symbols` will be ignored. The
symbol of `f_2` will be now `target` since it is the objective of the scalarization.

As for the return value of `add_epsilon_constraints`, the first value is a copy
of the original problem with the added scalarization, the second value is the 
symbols of the scalarization objective, and the last one, `constraint_symbols`,
are the symbols of the newly added constraints. In the case of the above example
the would be `["eps_1", "eps_3"]`, because the objective of the scalarization,
`f_2`, does not require a constraint.

The epsilon constraint method, unlike the non-differentiable variant of the
achievement scalarizing function, retains the differentiability and linearity
of the objective functions. However, it does add constraints, which means a
solver must be able to support constrained problems. As many things in life,
adding scalarization functions comes with trade-offs.

## Where to go next?
You can study the available scalarization functions found in the
[scalarization module][desdeo.tools.scalarization]. If you are interested
in how a scalarized problem can be solved, you can proceed to the
section [Solvers](./solvers.md).