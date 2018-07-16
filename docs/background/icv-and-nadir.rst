Estimates of the ICV and Nadir
==============================

    The result of the optimization is a vector, where the components are the
    values of the objective functions. When optimizing the functions
    individually and creating the vector of these values, we get the `ICV
    <../helps/terminology.html>`__; that is, the Ideal Criterion Vector.

    The ICV tells us the best solution that exists for each objective, when the
    functions are treated independently. However, the ICV vector is infeasible
    because it is usually impossible to get the best of everything at the same
    time - one must make compromises. For minimized functions ICV represents
    the lower bounds in the set of Pareto optimal solutions and the values are
    shown on the x-axis of the bar graph. For maximized functions ICV
    represents the upper bounds in the Pareto optimal set and the values can be
    found at the top of the bars. If the problem is complicated (that is,
    nonconvex) the actual components of ICV are difficult to calculate. Thus,
    to make sure, we refer to ICV as an *estimated ICV*.

    The `nadir <../helps/terminology.html>`__ is in some sense the opposite of the
    ICV. It consists of component values for the 'worst case' solution
    vector. For minimized functions Nadir represents the upper bounds in
    the set of Pareto optimal solutions and the values can be found at
    the top of the bars. For maximized functions Nadir represents the
    lower bounds in the Pareto optimal set and the values are shown on
    the x-axis of the bar graph. In practise, the Nadir vector is only
    an estimation because it is also difficult (even impossible, in the
    general case) to calculate.

    The estimated components of the ICV and the Nadir vector are updated during
    the calculations, whenever the solver founds improved values. If you know
    the exact values or better estimates of the ICV and Nadir vectors, you can
    correct the estimates of the system by setting the `ideal` and `nadir`
    properties of your subclass of :py:class:`desdeo.problem.PythonProblem`.
