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
 
 The mission of DESDEO is to increase awarenss of the benefits of interactive
 methods make interactive methods more easily available and applicable.
 Thanks to the open architecture, interactive methods are easier to be
 utilized and further developed. The framework consists of reusable
 components that can be utilized for implementing new methods or modifying
 the existing methods. The framework is released under a permissive open
 source license.
 
 **TODO: MORE ABOUT EMO AND OTHER MISSING STUFF**

The Research Projects Behind DESDEO
-----------------------------------
 
 ** TODO **

 - Tell about the Multiobjective Optimization Group
 - Tell about the DESDEO research project
 - Tell about DAEMON

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

.. _publications: https://desdeo.misitano.xyz/publications/