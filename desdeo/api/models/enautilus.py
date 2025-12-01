"""Models specific to the E-NAUTILUS point method."""

from sqlmodel import JSON, Column, Field, SQLModel


class EnautilusStepRequest(SQLModel):
    """Model of the request to the E-NAUTILUS method."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    # non_dominated points fetched from problem metadata in endpoints
    representative_solutions_id: int | None = Field(default=None)

    current_iteration: int = Field(description="The number of the current iteration.")
    iterations_left: int = Field(description="The number of iterations left.")
    selected_point: dict[str, float] | None = Field(
        sa_column=Column(JSON),
        description=(
            "The selected intermediate point. If first iteration, set this to be the (approximated) nadir point. "
            "If not set, then the point is assumed to be the nadir point of the current approximating set."
        ),
    )
    reachable_point_indices: list[int] = Field(
        description=(
            "The indices indicating the point on the non-dominated set that are "
            "reachable from the currently selected point."
        )
    )
    number_of_intermediate_points: int = Field(description="The number of intermediate points to be generated.")
