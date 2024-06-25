# Solvers

While DESDEO is a framework for interactive multiobjective 
optimization, it does not implement any optimizers _per se_.
Instead, DESDEO provides interfaces to many existing solvers.
How these interfaces work in general is explained in the 
section [Solver interfaces](#solver-interfaces), while
a couple of examples on how to use the solvers are
given in the section [Solver examples](#solver-examples).

## Solver interfaces

The solver interfaces rely internally heavily on the evaluators discussed
in the section [Parsing and evaluating](./parsing_and_evaluating.md). It is
the evaluators that make sure the `Problem` being solved is in a format that
can be evaluated by a solver. The solver interfaces discussed here are
in charge of making sure that when an outside solver evaluates a problem, the information
from the solver is passed to the evaluator in a correct format, and that the
output of the solver is then processed in a way that it can be utilized elsewhere
in DESDEO. The interfaces also pass information from DESDEO to solvers
in a compatible format. To put it simply, the solver interfaces are translators between the
evaluators in DESDEO and the solvers found outside of DESDEO.

## Solver examples

How solvers can be utilized in practice is best illustrated with examples. We provide
here a few examples on how to utilize different solvers through the solver interfaces
available in DESDEO.

### Scipy solvers

The Scipy solvers in desdeo, found in the module [Scipy solver
interfaces][desdeo.tools.scipy_solver_interfaces] can be used to interface with
the optimization routines found in the Scipy library. There are interfaces to
the solvers
[`minimize`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html)
and [`differential_evolution`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html).

First, to illustrate the usage of the `minimize` interface, and the interfaces in general, consider the following
example:

```python
from desdeo.tools import create_scipy_minimize_solver

problem: Problem  # a problem with the objectives f_1, f_2, and f_3 to be minimized

solver = create_scipy_minimize_solver(problem)

results: SolverResults = solver("f_1")
```

In the above example, we consider an arbitrary `Problem` with three objectives.
We then create a solver by calling [create_scipy_minimize_solver][desdeo.tools.scipy_solver_interfaces.create_scipy_minimize_solver]
and supplying it the problem we want to solve. This makes all the necessary setups for the solver and then
returns another function, which we have stored in `solver`. To run the solver, we call the `solver` function
with the symbol of the function defined in the problem we wish to minimize. Then, the solver returns a pydantic
dataclass of type [SolverResults][desdeo.tools.generics.SolverResults] with the results of the optimization. It
is important to know that whichever function we request the solver to optimize, will be minimized. Therefore,
in the example, if `f_1` was to be maximized instead, we should have called `solver` with the argument `f_1_min`.
The results contained in SolverResults will then correspond to the original maximized function `f_1`. It is
the jobs of the evaluators to make sure that `f_1_min` is available. Likewise, if we have
[Scalarized](./scalarization.md) the problem, we can give the solver the symbol of the added
scalarization function.

!!! note
    Whichever function we request a solver to optimize, it will be minimized.

### Proximal solver

The [proximal solver][desdeo.tools.proximal_solver.create_proximal_solver] is useful when a `Problem` has been defines such that all of
its objective functions have been defined with a
[DiscreteRepresentation][desdeo.problem.schema.DiscreteRepresentation]. The
proximal solver takes a symbol to optimize, and will return the decision
variable values that correspond to the lowest value found for the symbol in the
data. It works identically to the scipy solver in the previous example:

```python
from desdeo.tools import create_proximal_solver

problem: Problem  # a problem with the objectives f_1, f_2, and f_3, and a discrete definition available

solver = create_proximal_solver(problem)

results: SolverResults = solver("f_1")
```

### Pyomo solvers

WIP.

### Summary of Solvers

TODO.