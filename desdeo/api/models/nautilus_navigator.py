"""Models specific to the NAUTILUS Navigator method."""

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class NautilusNavigatorInitializationState(SQLModel, table=True):
    """State representing initialization of a NAUTILUS Navigator session.

    This state corresponds to the execution of the `navigator_init` function
    in the NAUTILUS Navigator algorithm.

    The initialization currently requires no explicit parameters from the API
    since the required information (problem and solver) is obtained from the
    surrounding application context. Therefore, this state only stores the
    primary key linking it to the base `State` entry.

    Future versions may include additional fields such as
    `non_dominated_solutions_id` if the algorithm later supports explicitly
    supplying these.
    """

    __tablename__ = "nautilus_navigator_initialization_states"

    id: int | None = Field(
        default=None,
        primary_key=True,
        foreign_key="states.id",
    )


class NautilusNavigatorNavigationState(SQLModel, table=True):
    """State representing one execution of the NAUTILUS Navigator navigation step.

    This state corresponds to a call to the `navigator_all_steps` function in
    the NAUTILUS Navigator algorithm.

    The design follows the standard pattern used in DESDEO method states:

        - Fields correspond to the input arguments of the algorithm function
        - A single field stores the result returned by the function

    This allows the API to:
        1. Retrieve previously computed navigation results without
           re-running the algorithm.
        2. Re-evaluate the algorithm if necessary, since the original
           input parameters are stored.

    Notes:
        The parameters `problem` and `solver` are not stored in the state,
        as they are provided by the surrounding application context.

    Stored Inputs (arguments to `navigator_all_steps`):
        steps_remaining:
            Number of navigation steps to perform.

        reference_point:
            The reference point provided by the decision maker.

        previous_responses:
            The list of previous NAUTILUS responses representing the
            navigation history up to this point.

        bounds:
            Optional bounds specified by the decision maker.

    Stored Output:
        navigator_results:
            The list of responses returned by `navigator_all_steps`.
            Each entry corresponds to one computed navigation step.
    """

    __tablename__ = "nautilus_navigator_navigation_states"

    id: int | None = Field(
        default=None,
        primary_key=True,
        foreign_key="states.id",
    )

    steps_remaining: int
    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    bounds: dict[str, float] | None = Field(default=None, sa_column=Column(JSON))
    previous_responses: list[dict] = Field(sa_column=Column(JSON))
    navigator_results: list[dict] = Field(sa_column=Column(JSON))


class NautilusNavigatorInitRequest(SQLModel):
    """Request to initialize a NAUTILUS Navigator session."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)


class NautilusNavigatorNavigateRequest(SQLModel):
    """Request to perform NAUTILUS Navigator navigation steps."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    reference_point: dict[str, float] = Field(
        sa_column=Column(JSON),
        description="Reference point provided by the decision maker.",
    )
    bounds: dict[str, float] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="The bounds preference of the DM for each objective.",
    )
    steps_remaining: int = Field(description="The number of steps remaining in the navigation process.")


class NautilusNavigatorStep(SQLModel):
    """A single NAUTILUS Navigator step result."""

    step_number: int
    navigation_point: dict[str, float] = Field(sa_column=Column(JSON))
    lower_bounds: dict[str, float] = Field(sa_column=Column(JSON))
    upper_bounds: dict[str, float] = Field(sa_column=Column(JSON))
    reachable_solution: dict[str, float] | None = Field(default=None, sa_column=Column(JSON))
    reference_point: dict[str, float] | None = Field(default=None, sa_column=Column(JSON))
    bounds: dict[str, float] | None = Field(default=None, sa_column=Column(JSON))
    distance_to_front: float


class NautilusNavigatorInitResponse(SQLModel):
    """Response from NAUTILUS Navigator initialization."""

    state_id: int | None = Field(description="The id of the state created by this initialization.")
    navigation_point: dict[str, float] = Field(sa_column=Column(JSON), description="Initial navigation point.")
    lower_bounds: dict[str, float] = Field(sa_column=Column(JSON), description="Lower bounds of reachable region.")
    upper_bounds: dict[str, float] = Field(sa_column=Column(JSON), description="Upper bounds of reachable region.")
    step_number: int = Field(description="Step number (always 0 at initialization).")
    distance_to_front: float = Field(description="Distance to Pareto front.")


class NautilusNavigatorNavigateResponse(SQLModel):
    """Response from NAUTILUS Navigator navigation."""

    state_id: int | None = Field(description="The id of the state created by this navigation step.")
    steps: list[NautilusNavigatorStep] = Field(description="The computed navigation steps.")
