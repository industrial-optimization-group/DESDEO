What is NAUTILUS?
=================

Most interactive methods developed for solving multiobjective
optimization problems sequentially generate Pareto optimal solutions
and the decision maker must always trade-off to get a new
solution. Instead, the family of interactive trade-off-free methods
called NAUTILUS starts from the worst possible objective values and
improves every objective function step by step according to the
preferences of the decision maker.

Recently, the NAUTILUS family has been presented as a general NAUTILUS
framework consisting of several modules. To extend the applicability of
interactive methods, it is recommended that a reliable software implementation,
which can be easily connected to different simulators or modelling tools, is
publicly available. In this paper, we bridge the gap between presenting an
algorithm and implementing it and propose a general software framework for the
NAUTILUS family which facilitates the implementation of all the NAUTILUS
methods, and even other interactive methods. This software framework has been
designed following an object-oriented architecture and consists of several
software blocks designed to cover independently the different requirements of
the NAUTILUS framework. To enhance wide applicability, the implementation is
available as open source code.
