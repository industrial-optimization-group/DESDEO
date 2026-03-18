from typing import Literal

from pydantic import BaseModel, Field


class NautilusStep(BaseModel):
    """Represents a single NAUTILUS step result."""

    step_number: int
    navigation_point: dict[str, float]

    lower_bounds: dict[str, float]
    upper_bounds: dict[str, float]

    reachable_solution: dict[str, float] | None
    reference_point: dict[str, float] | None
    bounds: dict[str, float] | None

    distance_to_front: float

# Requests
class NautilusInitRequest(BaseModel):
    """Request to initialize a NAUTILUS Navigator session for a specific problem."""

    problem_id: int = Field(..., description="The ID of the problem to navigate.")
    total_steps: int = Field(100, description="The total number of steps in the NAUTILUS Navigator.")

class NautilusNavigateRequest(BaseModel):
    """Request to navigate a NAUTILUS Navigator session."""

    problem_id: int = Field(..., description="The ID of the problem to navigate.")
    reference_point: dict[str, float] = Field(..., description="Reference point provided by the decision maker.")
    bounds: dict[str, float] | None = Field(
        default=None,
        description="The bounds preference of the DM for each objective."
    )
    go_back_step: int = Field(..., description="The step index to go back in the navigation history.")
    steps_remaining: int = Field(..., description="The number of steps remaining in the navigation process.")

# Responses
class NautilusInitialResponse(BaseModel):
    """Response returned by navigator_init."""

    state_id: int = Field(..., description="The ID of this navigation state.")
    response_type: Literal["nautilus.initialize"] = "nautilus.initialize"
    parent_state_id: int | None = Field(None, description="Parent state ID.")

    navigation_point: dict[str, float] = Field(..., description="Initial navigation point (nadir point).")

    lower_bounds: dict[str, float] = Field(..., description="Lower bounds of reachable region.")
    upper_bounds: dict[str, float] = Field(..., description="Upper bounds of reachable region.")

    step_number: int = Field(..., description="Step number (always 0 at initialization).")
    distance_to_front: float = Field(..., description="Distance to Pareto front.")

class NautilusNavigateResponse(BaseModel):
    """Response returned by navigator_all_steps (list of computed navigation steps)."""

    state_id: int
    response_type: Literal["nautilus.navigate"] = "nautilus.navigate"
    parent_state_id: int | None = None

    steps: list[NautilusStep]
