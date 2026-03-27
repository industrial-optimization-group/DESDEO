from sqlalchemy import JSON, Column, ForeignKey, Integer
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

    # Primary key referencing the base State entry.
    # state_id: int | None = Field(
    #     sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True)
    # )
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

    # Primary key referencing the base State entry
    id: int | None = Field(
        default=None,
        primary_key=True,
        foreign_key="states.id",
    )

    # Foreign key referencing base State entry
    # state_id: int | None = Field(
    #     sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True)
    # )
    steps_remaining: int
    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    bounds: dict[str, float] | None = Field(default=None, sa_column=Column(JSON))
    previous_responses: list[dict] = Field(sa_column=Column(JSON))
    navigator_results: list[dict] = Field(sa_column=Column(JSON))
    parent_state_id: int | None = Field(default=None)
