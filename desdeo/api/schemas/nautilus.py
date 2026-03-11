from typing import Literal

from pydantic import BaseModel, Field


# Requests
class NautilusInitRequest(BaseModel):
    """Request to initialize a NAUTILUS Navigator session for a specific problem."""

    problem_id: int = Field(..., description="The ID of the problem to navigate.")
    total_steps: int = Field(100, description="The total number of steps in the NAUTILUS Navigator.")

class NautilusNavigateRequest(BaseModel):
    """Request to navigate a NAUTILUS Navigator session."""

    problem_id: int = Field(..., description="The ID of the problem to navigate.")
    reference_point: dict[str, float] = Field(..., description="Reference point provided by the decision maker.")
    bounds: dict[str, float] = Field(..., description="The bounds preference of the DM for each objective.")
    go_back_step: int = Field(..., description="The step index to go back in the navigation history.")
    steps_remaining: int = Field(..., description="The number of steps remaining in the navigation process.")

# Responses
class NautilusInitialResponse(BaseModel):
    """Response returned by the NAUTILUS Navigator when initialized."""

    state_id: int = Field(..., description="The ID of this navigation state.")
    response_type: Literal["nautilus.initialize"] = "nautilus.initialize"
    parent_state_id: int | None = Field(None, description="Parent state ID, if this is a child step.")

    objective_symbols: list[str] = Field(..., description="The symbols of the objectives.")
    objective_long_names: list[str] = Field(..., description="Long/descriptive names of the objectives.")
    units: list[str] | None = Field(None, description="The units of the objectives, empty if unitless.")
    is_maximized: list[bool] = Field(..., description="Whether each objective is to be maximized.")
    ideal: list[float] = Field(..., description="The ideal values of the objectives.")
    nadir: list[float] = Field(..., description="The nadir values of the objectives.")
    total_steps: int = Field(..., description="The total number of steps in this NAUTILUS session.")


class NautilusNavigateResponse(BaseModel):
    """Response returned by the NAUTILUS Navigator during navigation (modern ENautilus style)."""

    state_id: int = Field(..., description="The ID of this navigation state.")
    response_type: Literal["nautilus.navigate"] = "nautilus.navigate"
    parent_state_id: int | None = Field(None, description="Parent state ID, if this is a child step.")

    objective_symbols: list[str] = Field(..., description="The symbols of the objectives.")
    objective_long_names: list[str] = Field(..., description="Long/descriptive names of the objectives.")
    units: list[str] | None = Field(None, description="The units of the objectives, empty if unitless.")
    is_maximized: list[bool] = Field(..., description="Whether each objective is to be maximized.")
    ideal: list[float] = Field(..., description="The ideal values of the objectives.")
    nadir: list[float] = Field(..., description="The nadir values of the objectives.")

    lower_bounds: dict[str, list[float]] = Field(..., description="Lower bounds of the reachable region per objective.")
    upper_bounds: dict[str, list[float]] = Field(..., description="Upper bounds of the reachable region per objective.")

    reference_point: dict[str, float] = Field(..., description="Preferences used in each step per objective.")
    bounds: dict[str, float] | None = Field(
        default=None,
        description="Bounds used in each step per objective."
    )

    total_steps: int = Field(..., description="The total number of steps in the current navigation path.")
    reachable_solution: dict[str, float] = Field(..., description="The solution reached at the end of navigation.")
