What is NIMBUS?
===============

As its name suggests, NIMBUS (Nondifferentiable Interactive Multiobjective BUndle-based optimization System) is a multiobjective optimization system being able to handle even nondifferentiable functions. It will optimize (minimize or maximize) several functions at the same time, creating a group of different solutions. One cannot say which one of them is the best, because the system cannot know the criteria affecting the 'goodness' of the desired solution. The user is the one that makes the decision. Usually, an example is the best way to make things clear:

Mathematical approach
---------------------

Mathematically, all the generated solutions are 'equal', so it is important that the user can influence the solution process. The user may want to choose which of the functions should be optimized most, what are the limits of the objectives, etc. In NIMBUS, this phase is called a 'classification'. We will discuss this procedure later.

Searching for the desired solution means actually finding the best compromise between many separate goals. If we want to get lower values for one function, we must be ready to accept the growth of another function. This is due to the fact that the solutions produced by NIMBUS are Pareto optimal. This means that there is no possibility to achieve better solutions for some component of the problem without worsening some other component(s).

