# An introduction to interactive multiobjective optimization

This tutorial provides a primer to get anyone with a basic knowledge
on mathematical optimization on board on what interactive multiobjective
optimization is. This is by no means meant to be a comprehensive tutorial,
but rather a gentle introduction to the topic so that the reader can
get a better idea on what DESDEO is about.

We start by defining what a multiobjective optimization problem is in
section [The multiobjective optimization problem](#the-multiobjective-optimization-problem).

## The multiobjective optimization problem

A multiobjective optimization problem is defined by three main components:

1. _objective functions_ $F = \left[f_1, f_2, \dots, f_k\right]$, where $k \geq 2$ denotes the number of objective
functions;
2. _decision variables_ $\mathbf{x} = \left[x_1, x_2, \dots, x_m\right]$, where $m$ denotes the number of decision variables, $\mathbf{x}$ is
known as a _decision vector_; and
3. _constraints_, including _inequality constraints_, such as $g < 0$, and equality constraints $h = 0$; and _box-constraints_,
which denote an upper and lower bound for each decision variable.

The objective functions and constraints are functions of the decision variables, e.g.,
$f_i \to f_i(\mathbf{x})$, where $i \in [1, k]$; $g \to g(\mathbf{x})$, and $h \to h(\mathbf{x})$.

We can put all the above together to define a multiobjective optimization problem as:
\begin{align}
   \operatorname{min}_\mathbf{x}\; F(\mathbf{x}) &= \operatorname{min}_\mathbf{x} \left[ f_1(\mathbf{x}), f_2(\mathbf{x}),\dots, f_k(\mathbf{x})\right], \\
    \text{s.t.}\quad g_j(\mathbf{x}) &< 0\,\forall\,j \in [1, u],\\
    h_l(\mathbf{x}) &= 0\,\forall\,l \in [1, v],\\
    x_i &\leq \text{ub}_i\,\forall\,i \in [1, m],\\
    x_i &\geq \text{lb}_i\,\forall\,i \in [1, m],
\end{align}
where $\operatorname{min}_\mathbf{x}$ denotes _minimization_ subject to the decision variables, $u$ is the number
of inequality constraints, and $v$ the number of equality constraints; and $\text{lb}_i$ and 
$\text{ub}_i$ define the box-constraints of each decision variable $x_i$ for $i$ in $[1, m]$. Notice that
a multiobjective optimization problem might have no constraints, in which case the decision variables can
be unbound. A decision vector is said to be a _feasible solution_ to the multiobjective optimization
problem when it fulfills all the constraints. The feasible solutions belong to the _feasible set_
$S \subset \mathbb{R}^m$, which is defined by the constraints present in a multiobjective optimization problem. This allows
us to use the following shorthand definition for a multiobjective optimization problem:
$$
   \operatorname{min}_{\mathbf{x}\in S}\;\left[ f_1(\mathbf{x}), f_2(\mathbf{x}),\dots, f_k(\mathbf{x})\right].
$$

!!! Note "Minimization vs maximization"
    If an objective function were to be maximized, it can be transformed into its minimization
    equivalent by multiplying it by $-1$. I.e., $\operatorname{max} f_i$ is equivalent to
    $\operatorname{min} -f_i$.

A multiobjective optimization problem can be further characterized by the type
of its variables.  If the variables are all continuous, that is, $\mathbf{x} \in
\mathbb{R}^m$, then the problem is _continuous_. If some of the variables are
instead integer valued, that is, for some $i \in [1, m] x_i \in \mathbb{Z}$,
then the problem is considered to be a _mixed-integer problem_. If all the
variables are integer valued, then the multiobjective optimization problem is an
_integer problem_.

Furthermore, depending on the characteristics of the objective functions, a problem
may be _convex_ or _non-convex_, and _differentiable_ or _non-differentiable_. These
details become important when choosing an appropriate solve to solve, e.g.,
a scalarized version of a multiobjective optimization problem. Scalarization
and scalarized problems will be discussed in the section [Scalatization](#scalarization).

The defining characteristic on a multiobjective optimization problem is that the objective functions
are mutually _conflicting_. This mean that when optimized, the objective functions cannot
reach their optimal value all at the same time. What can then be considered an
_optimal_ solution to a multiobjective optimization problem? We will discuss the optimality of solutions
to multiobjective optimization problems next. 

## Optimality in multiobjective optimization problems

In multiobjective optimization, the optimality of the solutions to multiobjective optimization
problems is defined utilizing the concept of _Pareto optimality_. Pareto optimality is defined
as follows:

!!! Note "Definition: Pareto optimality"
    A feasible solution $\mathbf{x}^*$ to a multiobjective optimization problem is considered Pareto optimal
    if, and only if, there exists no other feasible solution $\mathbf{x}$ such that
    
    - $f_i(\mathbf{x}) \leq f_i(\mathbf{x^*})$ for all $i \in [1, k]$, and
    - $f_j(\mathbf{x}) < f_j(\mathbf{x^*})$ for at leas one $j \in [1, k]$. 

Let us next define the image of a solution to a multiobjective optimization problem
to be an _objective vector_ $\mathbf{z}$, that is, for some solution $\mathbf{x}'$ we have
$\mathbf{z}' = [f_1(x'), f_2(x'), \dots, f_k(x')]$. It then follows from the definition
of Pareto optimality that when comparing two objective vectors $\mathbf{z}^1$ and $\mathbf{z}^2$,
that correspond to Pareto optimal solutions, we cannot switch from one vector to the other
in hopes of improving one objective function's value without having to deteriorate at least
another objective function's value. That is, when comparing the objective vectors corresponding to
Pareto optimal solutions, we have to make _trade-offs_.

If we furthermore define the set of the images of all the feasible solutions to a multiobjective
optimization problem to be $Z$, then we can also define the image set of all Pareto optimal solutions
to be $Z^\text{Pareto}$. We then readily see that $Z^\text{Pareto} \subset Z$. The set of all Pareto
optimal solutions can also be defined as $S^\text{Pareto}$, which is known as the
_Pareto optimal set_. Likewise, the set $Z^\text{Pareto}$ is known as the _Pareto front_. The Pareto
optimal set and the Pareto front are often very large, even uncountable, an they are seldom
fully known for a multiobjective optimization problem.

## Scalarization

## Notation reference

| Name | Notation | Description |
| :----- | :---: | :----------- |
| Objective function | $f_i(\mathbf{x})$ | An objective function of decision variables to be optimized, usually minimized. |
| Objective vector | $\mathbf{z}$ | A vector that consists of the image of objective functions that have been evaluated. |
| Decision variable | $x_i$ | A decision variable that can be used to evaluate objective functions. |
| Decision vector | $\mathbf{x}$ | A vector of decision variable values. |
| Inequality constraint | $g_i(\mathbf{x})$ | A constraint on the decision variables of the form $g_i(\mathbf{x}) < 0$. |
| Equality constraint | $h_i(\mathbf{x})$ | A constraint on the decision variables of the form $h_i(\mathbf{x}) = 0$. |
| The feasible set | $S$ | A set of all the feasible decision vectors. |

