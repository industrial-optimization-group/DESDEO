How to get your multi-objective optimization problem working with DESDEO
========================================================================

This section describes the different ways you can get your data, model or
simulation corresponding to a multi-objective optimization problem working with
DESDEO. Currently, there are three approaches to adding a new problem: creating
the model in Python, importing a list of solutions as data from a CSV, or
interfacing to another language via Thrift.

Creating the model in Python
----------------------------

This approach is based around the classes in
:py:mod:`desdeo.problem.porcelain`. This section walks through the process of defining the cylinder problem:
:py:class:`desdeo.problem.toy.CylinderProblem`. You can work through
:ref:`the cylinder problem notebook </nimbus-cylinder.ipynb>` to gain
familiarity with the cylinder problem.

.. code-block:: python

    from desdeo.problem.porcelain import Objective, PorcelainProblem, Variable

    class CylinderProblem(PorcelainProblem):
       """
       A description of the problem goes here.
       """
..

The first step is to import the classes we need and create a new class which
inherits from :py:class:`desdeo.problem.porcelain.PorcelainProblem`. You should
always add a docstring describing the problem so it can be displayed in the
notebook interface.

.. code-block:: python
   :dedent: 0

       r = Variable(low=5, high=15, start=10, name="Radius")
       h = Variable(low=5, high=25, start=10, name="Height")
..

Next, we can define variables using the
:py:class:`desdeo.problem.porcelain.Variable` class. Here, two variables `r`
and `h` are defined as the radius and height and given a range of acceptable
values, a starting value and a display name.

.. code-block:: python
   :dedent: 0

       @Objective("Volume", maximized=True)
       def volume(r, h):
           return math.pi * r ** 2 * h
..

Now we define one of the objectives: maximizing the volume of the cylinder.
First we define a function that takes all variables `r` and `h` in the form we
have just named them. The body of the function is the formula for the volume of
a cylinder :math:`\pi r^2  h`, translated to Python code. The function is then
decorated with the :py:class:`desdeo.problem.porcelain.Objective` class where
it is given a display name and the direction (maximized versus minimized) is
chosen.

.. code-block:: python
   :dedent: 0

       @Objective("Surface Area", maximized=False)
       def surface_area(r, h):
           return 2 * math.pi * r ** 2 + 2 * math.pi * r * h

       @Objective("Height Difference", maximized=False)
       def height_diff(r, h):
           return abs(h - 15.0)
..

We now define the other objectives, setting `maximized=False` to define them as
minimization problems.

.. code-block:: python
   :dedent: 0

       class Meta:
           name = "Cylinder Problem"
..

Lastly, we define the inner class `Meta` which is where extra settings are
stored. Here, we just define the display name for the problem.

Importing a list of solutions as data
-------------------------------------

In this approach, you start by generating a list of solutions and write out
their corresponding objective values to a `CSV file
<https://en.wikipedia.org/wiki/Comma-separated_values>`. DESDEO can then by
used to find the row corresponding to the best solution according to some
preferences.

The main class involved here is
:py:class:`desdeo.problem.PreGeneratedProblem`. Usage is simple, just pass in
a `filename` parameter:

.. code-block:: python

   PreGeneratedProblem(
      filename="/path/to/my/file.csv")
   )
..

`PreGeneratedProblem` only works with the
:py:class:`desdeo.optimization.PointSearch` (single-objective) optimization
method. So a full example using ENAUTILUS would look like:

.. code-block:: python

    ENAUTILUS(
        PreGeneratedProblem(
            filename="/path/to/my/file.csv"
        ),
        PointSearch,
    )
..

Interfacing to another language via Thrift
------------------------------------------

In some cases, your multi-objective optimization problem may be defined in
terms of simulation software you already have available. In order to transfer
information from the simulation to DESDEO, a Thrift interface is provided.

(Coming soon)
