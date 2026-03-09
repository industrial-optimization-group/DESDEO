from sqlmodel import JSON, Column, Field, SQLModel


class NautilusNavigatorInitializationState(SQLModel, table=True):
    """State storing the inputs and outputs of the NAUTILUS Navigator initialization.

    This state corresponds to the execution of the `navigator_init` function in the
    NAUTILUS Navigator core algorithm. It stores both the request provided by the
    user and the resulting initialization information returned by the algorithm.

    The state is linked to a base `StateDB` entry which defines the interaction
    type (`StateKind.NAUTILUS_INITIALIZE`) and stores the session hierarchy.

    The purpose of storing this information is to allow the API to:
        1. Retrieve previously computed initialization results without re-running
           the algorithm.
        2. Reconstruct the algorithm state if the function must be re-evaluated.

    Attributes:
        state_id (int): Foreign key referencing the base `StateDB` entry.

        request (dict): Serialized request data passed to `navigator_init`.
        response (dict): Serialized response returned by `navigator_init`.

        objective_symbols (list[str]): Short symbolic names of the objectives.
        objective_long_names (list[str]): Descriptive names of the objectives.
        units (list[str] | None): Units of the objectives if defined, otherwise None.
        is_maximized (list[bool]): Boolean flags indicating whether each objective
            is to be maximized (True) or minimized (False).

        ideal (list[float]): Ideal objective values of the problem.
        nadir (list[float]): Nadir objective values of the problem.

        total_steps (int): Total number of navigation steps specified for the session.
    """

    __tablename__ = "nautilus_navigator_initialization_states"

    state_id: int = Field(foreign_key="state.id", primary_key=True)

    # Stored request/response
    request: dict = Field(sa_column=Column(JSON))
    response: dict = Field(sa_column=Column(JSON))

    # Problem meta
    objective_symbols: list[str] = Field(sa_column=Column(JSON))
    objective_long_names: list[str] = Field(sa_column=Column(JSON))
    units: list[str] | None = Field(default=None, sa_column=Column(JSON))
    is_maximized: list[bool] = Field(sa_column=Column(JSON))

    # Problem bounds
    ideal: list[float] = Field(sa_column=Column(JSON))
    nadir: list[float] = Field(sa_column=Column(JSON))

    # Navigator configuration
    total_steps: int


class NautilusNavigatorNavigationState(SQLModel, table=True):
    """State storing the inputs and outputs of a NAUTILUS Navigator navigation step.

    This state corresponds to the execution of the `navigator_all_steps` function
    in the NAUTILUS Navigator algorithm. Each navigation step produces a new
    reachable solution and updated bounds based on the decision maker's
    preferences.

    The state stores both the user input and the algorithm output so that:
        1. The navigation history can be inspected without recomputing results.
        2. The algorithm can be re-evaluated if needed.

    The state is linked to a base `StateDB` entry which defines the interaction
    type (`StateKind.NAUTILUS_NAVIGATE`) and the parent state relationship.

    Attributes:
        state_id (int): Foreign key referencing the base `StateDB` entry.

        request (dict): Serialized navigation request provided by the decision maker.
        response (dict): Serialized response returned by the navigator algorithm.

        current_step (int): Current step index in the navigation process.
        remaining_steps (int): Number of remaining navigation steps.

        preferences (dict[str, list[float]]): Preference values provided by the
            decision maker for each objective.

        bounds (dict[str, list[float]]): Bound preferences provided by the
            decision maker.

        lower_bounds (dict[str, list[float]]): Lower bounds of the reachable
            objective region after the navigation step.

        upper_bounds (dict[str, list[float]]): Upper bounds of the reachable
            objective region after the navigation step.

        reachable_solution (dict[str, float]): Objective values of the currently
            reachable solution produced by the navigation step.
    """

    __tablename__ = "nautilus_navigator_navigation_states"

    state_id: int = Field(foreign_key="state.id", primary_key=True)

    # Stored request/response
    request: dict = Field(sa_column=Column(JSON))
    response: dict = Field(sa_column=Column(JSON))

    # Navigation progress
    current_step: int
    remaining_steps: int

    # Decision maker input
    preferences: dict[str, list[float]] = Field(sa_column=Column(JSON))
    bounds: dict[str, list[float]] = Field(sa_column=Column(JSON))

    # Reachable region bounds
    lower_bounds: dict[str, list[float]] = Field(sa_column=Column(JSON))
    upper_bounds: dict[str, list[float]] = Field(sa_column=Column(JSON))

    # Resulting solution
    reachable_solution: dict[str, float] = Field(sa_column=Column(JSON))
