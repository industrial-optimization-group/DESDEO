Glossary
========

.. _gloss-pareto-optimal:

Pareto optimality
    A criterion vector z* (consisting of the values of the objective functions at a point x*) is *Pareto optimal* if none of its components can be improved without impairing at least one of the other components. In this case, x* is also called Pareto optimal. Synonyms for Pareto optimality are efficiency, noninteriority and Edgeworth-Pareto optimality.

Weak Pareto optimality
    A criterion vector z* (consisting of the values of the objective functions at a point x*) is *weakly Pareto optimal* if there does not exist any other vector for which all the components are better. In this case, x* is also called weakly Pareto optimal.

.. _gloss-icv:

Ideal criterion vector (ICV)
    The ideal criterion vector consists of the best possible values each objective function can achieve. The ICV represents the lower bounds of the set of Pareto optimal solutions. (That is, Pareto optimal set)

    For minimized functions the ICV is given as the Lowest Value, and for maximized functions as the Highest Value.

Current solution
    Current values of the objective functions.

Nadir vector (or nadir point)
    Estimated upper bounds of the solutions in the Pareto optimal set. The nadir vector represents the worst values that each objective function can attain in the Pareto optimal set.

    For minimized functions the Nadir is given as the Highest Value, and for maximized functions as the Lowest Value.

(Sub)gradient
    A gradient of a function consists of its partial derivatives subject to each variable. A gradient vector exists for differentiable functions. For nondifferentiable functions a more general concept *subgradient* is used.

.. _gloss-aspiration-level:

Aspiration levels
    For each minimized function in the class <= and maximized function in the class >= you must specify an aspiration level. The aspiration level is the value which you desire function value should be decreased or increased to.

    **NOTE: For minimized functions the aspiration level must be between the lowest value and the current value of the objective function. For maximized function the aspiration level must be between the current and highest value of the objective function.**

.. _gloss-upper-lower-bound:

Upper and lower bounds
    For each minimized function in the class >= and maximized function in the
    class <= you must specify a boundary value. The upper or lower bounds are
    the largest or smallest allowable objective function value respectively.

    **NOTE: For minimized function the upper bound value must be between the current and highest value of the objective function. For maximized function the lower bound value must be between the current and lowest value of the objective function.**
