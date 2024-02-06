"""Router for NIMBUS."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/nimbus")


class NIMBUSResponse(BaseModel):
    """The response from most NIMBUS endpoints."""

    objective_names: list[str] = Field(description="The names of the objectives.")
    is_maximized: list[bool] = Field(description="Whether the objectives are to be maximized or minimized.")
    lower_bounds: list[float] = Field(description="The lower bounds of the objectives.")
    upper_bounds: list[float] = Field(description="The upper bounds of the objectives.")
    previous_preference: list[float] = Field(description="The previous preference used.")
    current_solutions: list[list[float]] = Field(description="The current solutions.")
    saved_solutions: list[list[float]] = Field(description="The saved solutions.")
    all_solutions: list[list[float]] = Field(description="All the solutions.")


class FakeNIMBUSResponse(BaseModel):
    """fake response for testing purposes."""

    message: str = Field(description="A simple message.")


class NIMBUSIterateRequest(BaseModel):
    """The request to iterate the NIMBUS algorithm."""

    problem_id: int = Field(description="The ID of the problem to be solved.")
    preference: list[float] = Field(
        description=(
            "The preference as a reference point. Note, NIMBUS uses classification preference,"
            " we can construct it using this reference point and the reference solution."
        )
    )
    reference_solution: list[float] = Field(
        description="The reference solution to be used in the classification preference."
    )
    num_solutions: int | None = Field(
        description="The number of solutions to be generated in the iteration.", default=1
    )


class SaveRequest(BaseModel):
    """The request to save the solutions."""

    problem_id: int = Field(description="The ID of the problem to be solved.")
    solutions: list[list[float]] = Field(description="The solutions to be saved.")


@router.post("/initialize")
def initialize(problem_id: int, initial_solution: list[float] | None = None) -> NIMBUSResponse | FakeNIMBUSResponse:
    """Initialize the NIMBUS algorithm.

    Args:
        problem_id: The ID of the problem to be solved.
        initial_solution: The initial solution to start the algorithm from.

    Returns:
        The response from the NIMBUS algorithm.
    """
    # Do database stuff here.
    # Do NIMBUS stuff here.
    # Do database stuff again.
    return FakeNIMBUSResponse(message="NIMBUS initialized.")


@router.post("/iterate")
def iterate(request: NIMBUSIterateRequest) -> NIMBUSResponse | FakeNIMBUSResponse:
    """Iterate the NIMBUS algorithm.

    Args:
        request: The request body for a NIMBUS iteration.

    Returns:
        The response from the NIMBUS algorithm.
    """
    # Do database stuff here.
    # Do NIMBUS stuff here.
    # Do database stuff again.
    return FakeNIMBUSResponse(message="NIMBUS iterated.")


@router.post("/intermediate")
def intermediate(
    problem_id: int, solution1: list[float], solution2: list[float], num_solutions: int | None = 1
) -> NIMBUSResponse | FakeNIMBUSResponse:
    """Get solutions between two solutions using NIMBUS.

    Args:
        problem_id: The ID of the problem to be solved.
        solution1: The first solution to be used.
        solution2: The second solution to be used.
        num_solutions: The number of solutions to be generated between the two solutions.

    Returns:
        The response from the NIMBUS algorithm.
    """
    # Do database stuff here.
    # Do NIMBUS stuff here.
    # Do database stuff again.
    return FakeNIMBUSResponse(message="NIMBUS intermediate solutions generated.")


@router.post("/save")
def save(request: SaveRequest) -> NIMBUSResponse | FakeNIMBUSResponse:
    """Save the solutions to the database.

    Args:
        request: The request body for saving solutions.

    Returns:
        The response from the NIMBUS algorithm.
    """
    # Do database stuff here.
    # Do NIMBUS stuff here.
    # Do database stuff again.
    return FakeNIMBUSResponse(message="Solutions saved.")


@router.post("/choose")
def choose(problem_id: int, solution: list[float]) -> NIMBUSResponse | FakeNIMBUSResponse:
    """Choose a solution as the final solution for NIMBUS.

    Args:
        problem_id: The ID of the problem to be solved.
        solution: The solution to be chosen.

    Returns:
        The response from the NIMBUS algorithm.
    """
    # Do database stuff here.
    # Do NIMBUS stuff here.
    # Do database stuff again.
    return FakeNIMBUSResponse(message="Solution chosen.")
