from sqlmodel import JSON, Column, Field, SQLModel


class NautilusState(SQLModel, table=True):
    """Concrete NAUTILUS Navigator state stored for a single interaction step.

    This model stores the full algorithmic state returned by the
    NAUTILUS Navigator after either initialization or a navigation step.

    The instance is linked to a base `StateDB` entry, which defines the
    problem context and state type (e.g. "nautilus.initialize" or
    "nautilus.navigate"). This table contains only the algorithm-specific
    data required to reconstruct the navigation process at that step.

    Attributes:
        id (int | None): Primary key of this NAUTILUS state entry.
        objective_symbols (list[str]): Short symbolic names of the objectives.
        objective_long_names (list[str]): Descriptive names of the objectives.
        units (list[str] | None): Units of the objectives, if defined. None if unitless.
        is_maximized (list[bool]): Boolean flags indicating whether each objective
            is to be maximized (True) or minimized (False).
        ideal (list[float]): Ideal objective values of the problem.
        nadir (list[float]): Nadir objective values of the problem.
        lower_bounds (dict[str, list[float]]): Lower bounds of the reachable region per objective
            across navigation steps.
        upper_bounds (dict[str, list[float]]): Upper bounds of the reachable region per objective
            across navigation steps.
        preferences (dict[str, list[float]]): Preference values provided by the decision maker
            for each navigation step.
        bounds (dict[str, list[float]]): Bound preferences provided by the decision maker
            for each navigation step.
        total_steps (int): Total number of steps allowed in this NAUTILUS session.
        current_step (int): Current navigation step index.
        remaining_steps (int): Number of steps remaining in the navigation process.
        reachable_solution (dict[str, float]): The objective values of the currently reachable solution.
    """

    __tablename__ = "nautilus_states"

    id: int | None = Field(default=None, primary_key=True)

    # Problem meta
    objective_symbols: list[str] = Field(sa_column=Column(JSON))
    objective_long_names: list[str] = Field(sa_column=Column(JSON))
    units: list[str] | None = Field(default=None, sa_column=Column(JSON))
    is_maximized: list[bool] = Field(sa_column=Column(JSON))

    # Problem bounds
    ideal: list[float] = Field(sa_column=Column(JSON))
    nadir: list[float] = Field(sa_column=Column(JSON))

    # Navigation data
    lower_bounds: dict[str, list[float]] = Field(sa_column=Column(JSON))
    upper_bounds: dict[str, list[float]] = Field(sa_column=Column(JSON))
    preferences: dict[str, list[float]] = Field(sa_column=Column(JSON))
    bounds: dict[str, list[float]] = Field(sa_column=Column(JSON))

    total_steps: int
    current_step: int
    remaining_steps: int

    # Final reachable solution
    reachable_solution: dict[str, float] = Field(sa_column=Column(JSON))
