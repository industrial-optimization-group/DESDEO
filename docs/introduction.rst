Introduction
============

About DESDEO
------------

 DESDEO is an open source framework for interactive multiobjective
 optimization methods. DESDEO contains implementations of some interactive
 methods and modules that can be utilized to implement further methods.
 
 In multiobjective optimization, several conflicting objective functions are
 to be optimized simultaneously. Because of the conflicting nature of the
 objectives, it is not possible to obtain individual optima of the objectives
 simulatneously but one must trade-off between the objectives. Interactive
 methods are iterative by nature where a decision maker (who has substance
 knowledge) can direct the solution process with one's preference information
 to find the most preferred balance between the objectives. In interactive
 methods, the amount of information to be considered at a time is limited
 and, thus, the cognitive load set on the decision maker is not too
 demanding. Furthermore, the decision maker learns about the
 interdependencies among the objectives and also the feasibility of one's
 preferences.
  
 Evolutionary algorithms (EAs) are optimization algorithms which emulate the process of
 evolution via natural selection to find optimal solutions to single- or multiobjective
 optimization problems (MOPs).
 This is achieved by taking a *population* of candidate solutions, known as
 *individuals*.
 The individuals mix and match their properties with other individuals in a process
 called *crossover* to form a new batch of candidate solutions, known as *offsprings*.
 The process also involves a random change in the properties of the offsprings, which
 occurs via a process called *mutation*.
 Finally, there is a culling step, called *selection*, which kills the individuals which
 are considered not optimal according to a *fitness* criteria.
 The surviving members of the population then undergo the same steps as mentioned above,
 and slowly converge towards optimality as determined by the fitness criteria used in the
 selection step.
 Different EAs differ in the way they handle the population; conduct crossover, mutation,
 and selection; and calculate the fitness criteria.

 The mission of DESDEO is to increase awarenss of the benefits of interactive
 methods make interactive methods more easily available and applicable.
 Thanks to the open architecture, interactive methods are easier to be
 utilized and further developed. The framework consists of reusable
 components that can be utilized for implementing new methods or modifying
 the existing methods. The framework is released under a permissive open
 source license.


 **TODO: MORE ABOUT OTHER MISSING STUFF**

The Research Projects Behind DESDEO
-----------------------------------
 
About the Multiobjective Optimization Group
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Multiobjective Optimization Group developes theory, methodology and
open-source computer implementations for solving real-world decision-making
problems. Most of the research concentrates on multiobjective optimization
(MO) in which multiple conflicting objectives are optimized simultaneously
and a decision maker (DM) is supported in finding a preferred compromise.

About the DESDEO research project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

DESDEO contains implementations of some interactive methods and modules that
can be utilized to implement further methods. DESDEO brings interactive
methods closer to researchers and practitioners world-wide, by providing them
with implementations of interactive methods.

Interactive methods are useful tools for decision support in finding the most
preferred balance among conflicting objectives. They support the decision
maker in gaining insight in the trade-offs among the conflicting objectives.
The decision maker can also conveniently learn about the feasibility of one's
preferences and update them, if needed.

DESDEO is part of DEMO (Decision analytics utilizing causal models and
multiobjective optimization) which is the thematic research area of the
University of Jyväskylä (jyu.fi/demo).

We welcome you to utilize DESDEO and develop it further with us.

About DAEMON
^^^^^^^^^^^^

The mission of DAEMON is method and software development for making better
data-driven decisions. The project considers data and decision problems from
selected fields as cases to inspire the research and demonstrate the added
value.

In DAEMON, we support optimizing conflicting objectives simultaneously by
applying interactive multiobjective optimization methods, where a decision
maker (DM) incorporates one’s domain expertise and preferences in the
solution process. Overall, we model and formulate optimization problems based
on data, so that DMs can identify effective strategies to better understand
trade-offs and balance between conflicting objectives. In this, we
incorporate machine learning tools, visualize trade-offs to DMs and consider
uncertainties affecting the decisions.

Publications Related to DESDEO
------------------------------

See publications_.

Glossary
--------

.. glossary::

   decision maker, DM
      A domain expert with adequate expertise related to an optimization
      problem able to provide preference information.

   Pareto optimal solution
      A feasible solution to a multiobjective optimization problem which
      corresponds to an objective vector that cannot be exchanged for any
      other objective vector resulting from some other feasible solution
      wihtout having to make a trade-off in at least one objective value.

   Pareto front
      The set of Pareto optimal solutions.

   nadir (point)
      The worst possible objective values of a Pareto front.

   ideal (point)
      The best possible objective values of a Pareto front.

.. _publications: https://desdeo.it.jyu.fi/publications/