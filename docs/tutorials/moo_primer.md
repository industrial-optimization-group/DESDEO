# A primer on interactive multiobjective optimization

This tutorial provides a primer to get anyone with a basic knowledge
on mathematical optimization on board on what interactive multiobjective
optimization is. This is by no means meant to be a comprehensive tutorial,
but rather a gentle introduction to the topic so that the reader can
get a better idea on what DESDEO is about.

We start by defining what a multiobjective optimization problem is in
section [The multiobjective optimization problem](#the-multiobjective-optimization-problem).

## The multiobjective optimization problem

!!! question "Why and where is this relevant in DESDEO?"
    Understanding the definition of a multiobjective optimization problem is
    important when defining problems in DESDEO and to understand how problems are modeled. 
    See [The problem format](../explanation/problem_format.md#the-problem-format).

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
<span id="def:moo"></span>
!!! Note "Definition: a multiobjective optimization problem"
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
and scalarized problems will be discussed in the section [Scalarization](#scalarization).

The defining characteristic on a multiobjective optimization problem is that the objective functions
are mutually _conflicting_. This mean that when optimized, the objective functions cannot
reach their optimal value all at the same time. What can then be considered an
_optimal_ solution to a multiobjective optimization problem? We will discuss the optimality of solutions
to multiobjective optimization problems next. 

## Optimality in multiobjective optimization problems

!!! question "Why and where is this relevant in DESDEO?"
    It is important to understand what an optimal solution is in multiobjective optimization when
    choosing a solver. See [Solvers and solver interfaces](../explanation/solvers.md#solvers-and-solver-interfaces).

    In evolutionary multiobjective optimization, the discussed concept of dominance plays a key role, and understanding
    it is important when operating evolutionary methods. See TOBEADDED!

In multiobjective optimization, the optimality of the solutions to multiobjective optimization
problems is defined utilizing the concept of _Pareto optimality_. Pareto optimality is defined
as follows:

<span id="def:pareto_optimality"></span> 
!!! Note "Definition: Pareto optimality"
    A feasible solution $\mathbf{x}^*$ to a multiobjective optimization problem is considered Pareto optimal
    if, and only if, there exists no other feasible solution $\mathbf{x}$ such that
    
    - $f_i(\mathbf{x}) \leq f_i(\mathbf{x^*})$ for all $i \in [1, k]$, and
    - $f_j(\mathbf{x}) < f_j(\mathbf{x^*})$ for at leas one $j \in [1, k]$. 

Let us next define the image of a solution to a multiobjective optimization problem
to be an _objective vector_ $\mathbf{z}$, that is, for some solution $\mathbf{x}'$ we have
$\mathbf{z}' = [f_1(x'), f_2(x'), \dots, f_k(x')] = [z'_1, z'_2, \dots, z'_k]$. It then follows from the definition
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
optimal set and the Pareto front are often very large, often uncountable, and they are
therefore seldom fully known for a multiobjective optimization problem. As
such, the Pareto optimal solution set and the Pareto front should be understood as
theoretical concepts.

There are two more useful definitions that can help characterize the Pareto optimal
set and front. These are the

- _ideal point_: $\mathbf{z}^\star = [z^\star_1, z^\star_2, \dots, z^\star_k]$
and the 
- _nadir point_: $\mathbf{z}^\text{nad} = [z^\text{nad}_1, z^\text{nad}_2, \dots, z^\text{nad}_k]$.

The ideal point consists of the _best_ objective function values of each individual objective
function on the Pareto optimal front, while the nadir point consists of the _worst_
objective function values on the front. Computing the ideal point amounts to
optimizing each objective function individually and taking their optimal values,
which then correspond to the elements of the ideal point. On the other hand, the
nadir point is less trivial to compute, and is therefore often approximated.

A concept similar to Pareto optimality is _dominance_. Dominance is usually
defined using objective vectors as:

<span id="def:dominance"></span> 
!!! Note "Definition: dominance"
    An objective vector $\mathbf{z}^1$ is said to dominate another objective
    vector $\mathbf{z}^2$ if, and only if,

    - $z^1_i \leq z^1_i\,\forall i \in [1, k]$, and
    - $z^1_j < z^1_j$ for at least one $j \in [1,k]$.
    
To notate domination, the following syntax can be used: $\mathbf{z}^1 \succ \mathbf{z}^2$,
which means that $\mathbf{z}^1$ dominates $\mathbf{z}^2$. Domination is an especially useful
concept when studying solution sets, and their images, to a multiobjective optimization
problem that are not necessarily Pareto optimal.
It allows the identification of solutions that fulfill the properties of Pareto
optimality _in the solution set_ being studied. Domination is a central concept when
generating approximations and representations of Pareto optimal solution sets and their
images. We will return to this topic when discussing about evolutionary multiobjective 
optimization in the section
[Evolutionary multiobjective optimization](#evolutionary-multiobjective-optimization).

## Preference information

!!! question "Why and where is this relevant in DESDEO?"
    Preference information plays a key role in interactive multiobjective 
    optimization methods found throughout DESDEO. 

We now have an idea what an optimal solution to a [multiobjective optimization problem](#def:moo)
is, and we know that there are [many such solutions](#def:pareto_optimality). But which
of the Pareto optimal solutions is the _best_?

Without any further information, it is not possible to fully order Pareto optimal solutions.
One way to break away from this ambiguity on which solution is the best, is to utilize
_preference information_. Preference information is usually supplied by a _decision maker_
who is an expert, and consequently has adequate domain expertise, in the application
domain of a considered multiobjective optimization problem. This preference
information can then be utilized to find the solution that best matches it
among the Pareto optimal solutions to a multiobjective optimization problem.

There are a couple of important assumptions that are made when considering
preference information from a decision maker. First, we assume that a decision
maker will always prefer a Pareto optimal solution over a non-Pareto optimal one,
or consequently a [non-dominated solution](#def:dominance) over a dominated when. Second,
we assume the decision maker to provide their preferences in such a way that they can be
used to identify the decision maker's best, or most preferred, solution.

As an example of what preference information can consists of, consider the
_reference point_. A reference point is a vector consisting of
_aspiration levels_. These aspiration levels are objective function
values that a decision maker wishes, or aspires, to achieve when searching
for a solution to a multiobjective optimization problem. An aspiration
level is defined as $\mathbf{q} = [q_1, q_2, \dots, q_k]$, where the
aspiration levels $q_1, \dots, q_k$ are often assumed to be bounded by
a problem's ideal and nadir points.

Naturally, utilizing preferences provided by a decision maker causes the _best_
solution to be very subjective. This observation underlines that multiobjective 
optimization, at its core, is about _decision-support_. In other words,
many of the methods developed for multiobjective optimization utilize preference
information in one form or another, and their goal is to support a decision maker
in finding their most preferred solution. In the following sections, we will
see examples on how preference information can be used in multiobjective optimization
to support decision maker's in finding their most preferred solution.

## Scalarization

!!! question "Why and where is this relevant in DESDEO?"
    Scalarization plays a central role in many of the methods found in DESDEO.
    Especially the introduced reference points are a recurring element in many scalarization
    functions. See [Scalarization](../explanation/scalarization.md#scalarization).

Thus far, we have only defined what optimal solutions to multiobjective optimization problems are.
However, we have not yet discussed how to find these solutions. We will next discuss one such
approach, which utilizes _scalarization_.

By scalarizing a [multiobjective optimization problem](#def:moo), we transform it from
a multiobjective optimization problem to a single-objective optimization problem. 
Formally, we can define a scalarization function to be be a mapping:
$\mathcal{S}:\,\mathbb{R}^k \to \mathbb{R}$. We can then define a _scalarized problem_
to be:

<span id="def:scalarized_problem"></span>
!!! Note "Definition: scalarized problem"
    $$
    \operatorname{min}_{\mathbf{x}\in S} \mathcal{S}(F(\mathbf{x}); \mathbf{p}),
    $$
    where $\mathbf{p}$ is a vector of parameters utilized by the scalarization
    function $\mathcal{S}$. The parameters $\mathbf{p}$ can also be empty.

As an example of the scalarization function, consider the _achievement scalarizing function_
defined as:

<span id="def:asf"></span>
!!! Note "Definition: the achievement scalarizing function"
    $$
    \mathcal{S}_\text{ASF}(F(\mathbf{x}); \mathbf{q}, \mathbf{z}^\star, \mathbf{z}^\text{nad}) = 
    \underset{i=1,\ldots,k}{\text{max}}
    \left[
    \frac{f_i(\mathbf{x}) - q_i}{z^\text{nad}_i - (z_i^\star - \delta)}
    \right]
    + \rho\sum_{i=1}^{k} \frac{f_i(\mathbf{x})}{z_i^\text{nad} - (z_i^\star - \delta)},
    $$
    where $\delta$ and $\rho$ are small scalar values.

By minimizing, e.g., solving, the achievement scalarizing function, we can find
Pareto optimal solutions that are close to the provided reference point $\mathbf{q}$.

Another example of a scalarization function is the _epsilon-constraints scalarization_
defines as:

<span id="def:epsilon"></span>
!!! note "Definition: the epsilon-constraints scalarization"
    \begin{equation}
        \begin{aligned}
        & \operatorname{min}_{\mathbf{x} \in S}
        & & f_t(\mathbf{x}) \\
        & \text{s.t.}
        & & f_j(\mathbf{x}) \leq \epsilon_j \text{ for all } j = 1, \ldots ,k, \; j \neq t,
        \end{aligned}
    \end{equation}
    where $\epsilon_j$ are the epsilon bounds used in the epsilon constraints $f_j(\mathbf{x}) \leq \epsilon_j$,
    and $k$ is the number of objective functions.

In the epsilon-constraints scalarization, one of the objective functions is chosen to be
optimized, while the other objective functions are constrained.

However, it is important to choose and appropriate solver
when solving a [scalarized problem](#def:scalarized_problem). For example, the
[achievement scalarizing function](#def:asf) is not differentiable due to the _max_-term
present in it. This means that when choosing a solver, a solver that does not
require gradient information should be utilized. Alternatively, the achievement scalarizing
function can also be formulated in such a way that is is equivalent to the original formulation, but
retains its differentiability. Of course, this assumes that the original objective functions,
and constraint functions, are also differentiable. In the contrary case, reformulating the
achievement scalarizing function is unnecessary, since we would be utilizing a gradient free
solver in any case. The [epsilon-constraints scalarization](#def:epsilon), on the other
hand, retains the differentiability of the objective functions, but it introduced
constraints, which requires then a solver than can handle them.

There are other considerations to be made when choosing an appropriate solver, such as the type
of the variables (continuous or integer), the convexity of the objective functions and constraints; and the
linearity of the objective functions and constraints. All of these are important to keep in mind when
choosing an appropriate solver to guarantee the Pareto optimality of the solution found.
This primer will not delve deeper into these topics, but leaves the finer
details to other literature[^1][^2].

## Types of multiobjective optimization methods

!!! question "Why and where is this relevant in DESDEO?"
    It is important to understand what interactive multiobjective optimization
    methods are, and how they differ from other types of multiobjective optimization methods.
    DESDEO specialized in interactive methods, which are found throughout
    the framework. See the section HOWTO for examples on how to
    implement and utilize various interactive multiobjective optimization methods.

Multiobjective optimization methods can be categorized into different
types based on _when_ preference information is incorporated in the optimization,
i.e., the search of Pareto optimal solutions. To start, methods that do not
use preference information at all are known as _no-preference_ methods, and
will not be discussed further. DESDEO focused on the decision-support
aspect of multiobjective optimization, therefore only methods that make
use of preferences are relevant.

The first type of method that makes use of preference information,
is known as an _a priori_ method. These methods require preference information
to be available _before_ any optimization is done. This means that a
decision maker is required to provide, for instance, a reference point
before any optimization can take place. When preference information is given, then
optimization can take place, and an a priori method then terminates after
one or more solutions to a multiobjective optimization problem have been found
based on the provided preferences.

The second type of method that makes use of preference information is known
as an _a posteriori_ method. In these methods, preference information is utilized
_after_ optimization has taken place. Many evolutionary multiobjective optimization
methods, discusses later in the section
[Evolutionary multiobjective optimization methods](#evolutionary-multiobjective-optimization-methods),
are a posteriori methods, because they are capable of generating non-dominated solution
sets, which approximate Pareto optimal solutions. Therefore, in an a posteriori method, it is
often the case that a large number of solutions is generated first, then the preferences of
a decision maker are utilized to explore the solutions and find the solution that is
most preferred by the decision maker.

The third type method, and the most relevant type of method in DESDEO, is
known as an _interactive method_. In interactive methods, preferences are provided
by the decision maker, and utilized in the method, _during_ optimization. This means
that the decision maker iteratively provides preference information, which is then utilized
to compute new solution. The decision maker can then inspect these solutions, and provide
further preferences, which are again utilized to compute further new solutions.

While all the types of method discussed have their own pros and cons, interactive methods
shine especially in their ability to _support_ a decision maker to learn about
the solutions available to a multiobjective optimization problem. For example,
interactive methods can support a decision maker to learn about the trade-offs
between Pareto optimal solutions to a problem. Moreover, interactive methods
can also support the decision maker in learning about the feasibility of their
preferences, and therefore allows a decision maker to change and fine-tune their
preferences to find more interesting solutions. 
However, interactive methods are challenging to implement because of their
interactive nature. The methods often require specialized user interfaces to be
able to shine.

DESDEO focuses on interactive multiobjective optimization, and provides tools
and means to implement some of the most popular interactive methods, and allows
users to also implement their own. Because of DESDEO, there is no need to 
reinvent the wheel when it comes to interactive methods. Instead, components of
existing methods can be re-used and combined to create new methods, saving
researchers and developers time.

Interactive multiobjective optimization methods can be further classified
into _exact_ and _inexact_ methods, roughly speaking. Exact methods
will be discussed in the section [Exact methods](#exact-methods),
and inexact methods will be introduced in the section [Evolutionary multiobjective optimization methods](#evolutionary-multiobjective-optimization-methods).

## Exact methods

!!! question "Why and where is this relevant in DESDEO?"
    The `desdeo-mcdm` module contains many exact interactive multiobjective optimization methods.
    It is important to know when these methods are appropriate to be used, and what are their
    limitations.

Exact methods, sometimes called _MCDM methods_, are methods that employ [scalarization](#scalarization)
and exact solvers, such as gradient-based optimization. To apply exact methods, it is 
necessary that the problem formulation is known, i.e., the problem is defined
_analytically_. In this case, many exact solvers can exploit the problem's mathematical
properties to guarantee the Pareto optimality of the solutions found. Hence, the term
_exact methods_.

!!! note
    The name _MCDM method_ comes from the field of _multiple criteria decision making_.
    MCDM methods in interactive multiobjective optimization have been inspired
    by methods employed in MCDM, hence, the name.

However, it is important to choose a proper solver even when the problem formulation is
known. For instance, utilizing a linear solver, such as coin-or/cbc, to solve a non-linear problem,
will lead to unreliable results. A more appropriate solver would have been a non-linear solver,
such as coin-or/bonmin.

In the case that a problem cannot be defined analytically,
for example when one or more of the objective functions is a black-box,
then exact methods cannot be used.
A more suitable approach would be to utilize heuristics-based methods. One such
category of methods is evolutionary multiobjective optimization, which will
be discussed next.

## Evolutionary multiobjective optimization

TODO

## Evolutionary multiobjective optimization methods

TODO

## Notation summary


| Name | Notation | Description |
| :----- | :---: | :----------- |
| Number of objective functions | $k$ | The number of objective functions in a multiobjective optimization problem.|
| Number of decision variables | $m$ | The number of decision variables in a multiobjective optimization problem.|
| Objective function | $f_i(\mathbf{x})$ | An objective function of decision variables to be optimized, usually minimized. Here $i$ ranges between $1$ and $k$.|
| Objective vector | $\mathbf{z} = [z_1, \dots, z_k]$ | A vector that consists of the image of objective functions that have been evaluated.|
| Decision variable | $x_i$ | A decision variable that can be used to evaluate objective functions. |
| Decision vector | $\mathbf{x} = [x_1, \dots, x_m]$ | A vector of decision variable values. |
| Inequality constraint | $g(\mathbf{x})$ | A constraint on the decision variables of the form $g(\mathbf{x}) < 0$. |
| Equality constraint | $h(\mathbf{x})$ | A constraint on the decision variables of the form $h(\mathbf{x}) = 0$. |
| Feasible set | $S$ | A set of all the feasible decision vectors. |
| Image of the feasible set | $Z$ | A set of all the images of the feasible decision vectors. |
| Pareto optimal solution set | $S^\text{Pareto}$ | A set of all the Pareto optimal decision vectors. |
| Pareto front | $Z^\text{Pareto}$ | A set of all the images of the Pareto optimal decision vectors. |
| Ideal point | $\mathbf{z}^\star = [z_1^\star, \dots, z_k^\star]$ | The best objective function values on the Pareto optimal front. |
| Nadir point | $\mathbf{z}^\text{nad} = [z_1^\text{nad}, \dots, z_k^\text{nad}]$ | The best objective function values on the Pareto optimal front. |
| Reference point | $\mathbf{q} = [q_1, \dots, q_2]$ | A reference point usually supplied by a decision maker. It consists of the aspiration levels $q_1, \dots, q_k$. |


## Footnotes and references
[^1]: Miettinen, K. 1999. Nonlinear multiobjective optimization. Boston: Kluwer Academic Publishers.
[^2]: Sawaragi, Y., Nakayama, H. & Tanino, T. 1985. Theory of multiobjective optimization. Acedemic Press, Inc.