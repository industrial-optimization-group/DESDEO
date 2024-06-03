# Scalarization-based methods
In DESDEO, scalarization-based methods are implemented in a modular fashion.
This means that no method is provided _per se_, but instead the different
components required to build the method are provided. This idea is best illustrated
by examples.

## Example: The achievement scalarizing function method
In the achievement scalarizing function (ASF) method, a scalarization function is solved
iteratively with new preference information provided by a decision maker. The 
preference information consists in this case of a reference point containing
aspiration levels.

Suppose we have an instance of `Problem` defined as `problem`:

```python
problem: Problem = Problem(...)
```

Now, to "implement" the  ASF method, we first need preference information
for the decisoin maker. Suppose `z_pref` is a list of aspiration levels.

```python
# aspiration levels in a reference point
z_pref = [...]
```

The ASF is defined as follows:

$$
    S_\text{AS}(F(\mathbf{x}); \mathbf{\bar{z}}, \mathbf{z}^\star, \mathbf{z}^\text{nad}) = 
    \underset{i=1,\ldots,k}{\text{max}}
    \left[
    \frac{f_i(\mathbf{x}) - \bar{z}_i}{z^\text{nad}_i - (z_i^\star - \delta)}
    \right]
    + \rho\sum_{i=1}^{k} \frac{f_i(\mathbf{x})}{z_i^\text{nad} - (z_i^\star - \delta)},
$$

where the variables \(F(\mathbf{x}) = [f_1(\mathbf{x}),\dots,f_k(\mathbf{x})], \mathbf{z}^\star, \mathbf{z}^\text{nad}\)
are assumed to be available through the instance of `problem`. The variable \(\mathbf{\bar{z}}\) is our reference point,
which is provided by a decisoin maker.

Now, to create the ASF method, we first create the ASF and then add it to the instance of `problem`:

!!! TODO
    fix this

```python
# the achievement scalarizing function
problem = create_asf(problem=problem, symbol="s_asf", ref_point=z, delta=1e-6, rho=1e-6)
```

In the above example, we create an instance of the ASF where the variables of the function have been replaced by the
correspoinding variables found in the instance of `problem`. When creating scalarization functions of any type, at least
the problem and a symbol must be supplied. In this example, the argument `z` (reference point) is also
needed. The symbol is important because it is used later in solvers to specify
which scalarization functions should be optimized. In the ASF example, `delta` and `rho` are optional parameters of the
scalarization function. The number of parameters found in scalarization functions varies.

!!! Note
    When creating scalarization functions of any kind, the `tag` argument is very important because it is used
    to specify to solvers which scalarization functions should be optimized. The `tag` must be unique inside
    the instance of probelm, i.e., no other field of a `problem` dataclass should share the same symbol.

To solve the scalarization function, we can use of the solver. For instance, the `scipy_solver` can utilize the
minimizer routine defined in `scipy.optimize.minimize`. To solve the problem utilizing `scipy_solver`, we do:

```python
scipy_solver(problem, objective_tag="s_asf", kwargs={...})
```

As mentinoed, the `tag` defined previously is now important so that we can tell the solver what
to use as an objective when solving scalarization functions. The `kwargs` are optional arguments
to control the internal solver, in this case, the routine `scipy.optimize.minimize`...