Classification in NIMBUS
========================

    The solution process with NIMBUS is iterative. Since there is
    usually not only one absolutely right solution, you are asked to
    'guide the solver to a desired direction'. The classification is a
    process in which the desires of the user are expressed. You can
    choose which of the function values should be decreased from the
    current level and which of the functions are less important (i.e.
    their values can be increased).

Classification background
-------------------------

    In NIMBUS, preferences are expressed by choosing a class for each of the
    objective functions.

    When considering minimization, the class alternatives are:

        +-----------------------------------+-----------------------------------+
        | **<**                             | The value should be minimized.    |
        +-----------------------------------+-----------------------------------+
        | **<=**                            | The value should be minimized     |
        |                                   | until the specified limit is      |
        |                                   | reached.                          |
        +-----------------------------------+-----------------------------------+
        | **=**                             | The current value is OK.          |
        +-----------------------------------+-----------------------------------+
        | **>=**                            | Value can be increased. Value     |
        |                                   | should be kept below the          |
        |                                   | specified upper bound.            |
        +-----------------------------------+-----------------------------------+
        | **<>**                            | Value can change freely.          |
        +-----------------------------------+-----------------------------------+

    For maximization, directional signs are inverted:

        +-----------------------------------+-----------------------------------+
        | **>**                             | The value should be maximized.    |
        +-----------------------------------+-----------------------------------+
        | **>=**                            | The value should be maximized     |
        |                                   | until the specified limit is      |
        |                                   | reached.                          |
        +-----------------------------------+-----------------------------------+
        | **=**                             | The current value is OK.          |
        +-----------------------------------+-----------------------------------+
        | **<=**                            | Value can be decreased. Value     |
        |                                   | should be kept above the          |
        |                                   | specified lower bound.            |
        +-----------------------------------+-----------------------------------+
        | **<>**                            | Value can change freely.          |
        +-----------------------------------+-----------------------------------+

    If the second or the fourth alternative is selected, you are asked to
    specify the limits: an :ref:`aspiration level <gloss-aspiration-level>` or
    an :ref:`upper/lower bound <gloss-upper-lower-bound>` respectively for the
    function values;.

    -  **Aspiration level** defines a desired value for the objective
       function.
    -  **Upper/lower bound** defines the limit value that the function
       should not exceed, if possible.

    Since we are dealing with :ref:`Pareto optimal <gloss-pareto-optimal>`
    solutions (compromises) we must be willing to give up something in order to
    improve some other objective. That is why the **classification is feasible
    only if at least one objective function is in the first two classes and at
    least one objective function is in the last two classes.**

    In other words, you must determine at least one function whose value
    should be made better. However that can not be done if there are no
    functions whose value can be worsened.

Classification using the widget
-------------------------------

    The current solution is shown graphically as a parallel coordinate plot.
    The classification can be made by either clicking points on the axes, or by
    manually adjusting the classification selection boxes and limit fields.

    By default, maximization is interpreted as minimization. This means the
    function is negated. If you wish to view maximizations in their original
    form, click settings and then uncheck *Reformulate maximization as
    minimization*. To change the default, add the following to the beginning of
    your notebooks:

.. code-block:: python

    from desdeo_vis.conf import conf
    conf(max_as_min=False)
..

    Let us assume that the function under classification should be minimized.
    When you click on the corresponding axis, the system considers the axis
    value at the point you clicked on as a new limit value and inserts the
    numerical data into the limit field automatically. Selecting the point
    below the current solution means that function should be minimized (**<=**)
    until that limit is reached. If the point is selected above the current
    solution, we allow the function value to increase (**>=**) to that limit.
    Clicking a point below the whole bar means that the function should be
    minimized as much as possible (**<**). Correspondingly, if the value is
    selected above the whole bar, the function value can change freely (**<>**).
    If the current value of some function is satisfactory (**=**), you can
    express it by clicking the numeric value beside the bar.

    In the case of maximization, the logic above is reversed. For example, if
    you click a point above the current solution, it indicates that the
    function should be maximized as much as possible. The desired extreme point
    of each function is indicated by a small black triangle inside the top or
    the bottom of each bar.

    You can refine the graphical classification by changing the class of each
    objective function using the selection box or adjusting the value in its
    limit field.

Classifying the cylinder problem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The first solution we get from NIMBUS is reasonable. However, we may decide
    at this point that we want to increase the cylinder's volume as much as
    possible, while still keeping the surface area and height difference low.

    To do this, we check the rightmost ( **>** ) radiobutton from the line
    describing the current solutions, because we allow (for now) the volume to
    be varied freely. The next line describes the solution for the surface area
    function. We want to know how much the volume will be when the surface area
    is 1900, so we choose the second button from the right ( **>=** ). For
    height difference we check the second radiobutton from the left ( **<=** ).

    After submitting this information a new page appears asking for the
    aspiration functions of the third function and boundary values of the
    second function. The desired level defines a desired value for the
    objective function. The value must be lower than the current solution, but
    greater than the :ref:`ICV vector (lowest solution) <gloss-icv>`. In this
    case, the number is 2. The upper bound is the largest allowable objective
    function value. This value must be greater than the current solution, but
    lower than the :ref:`Nadir vector (highest solution)
    <gloss-upper-lower-bound>`. In this case, the number is 1900.

Classification without the widget
---------------------------------

    It is also possible to make a classification without the widget. Possibly
    reasons you might do this are because you are constructing an artificial
    decision maker, you are making your own preference selection widget, or
    because you are unable to use Jupyter notebook. In this case, maximizations
    are always reformulated as minimizations.

    The preference information is specified using a Python object called
    :py:class:`desdeo.preference.NIMBUSClassification`. If we wanted to make
    the same classification as above, it can be done like so:
    
.. code-block:: python

   classification = NIMBUSClassification(method, [
      ('>=', 1205.843),
      ('<=', 378.2263),
      ('=', 0.0)]
   )

Specifying subproblems
----------------------

    We can specify the maximum number of new solutions generated by the
    classification given. It's also possible to specify particular
    scalarization functions. See
    :py:meth:`desdeo.method.NIMBUS.next_iteration` for more information.
