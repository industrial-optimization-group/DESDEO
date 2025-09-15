"""Models specific to the nimbus method."""

from pydantic import ConfigDict
from sqlmodel import JSON, Column, Field, SQLModel

from desdeo.emo.options.templates import TemplateOptions, PreferenceOptions


class EMOIterateRequest(SQLModel):
    """Model of the request to iterate an EMO method."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    problem_id: int
    """Database ID of the problem to solve."""
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    """State ID of the parent state, if any. Should be None if this is the first state in a session."""

    template_options: list[TemplateOptions] | None = Field(default=None)
    """Options for the template to use. A list of options can be given if multiple templates are used in parallel."""
    preference_options: PreferenceOptions | None = Field(default=None)
    """Options for the preference handling."""


class EMOFetchRequest(SQLModel):
    """Model of the request to fetch solutions from an EMO method."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    problem_id: int
    """Database ID of the problem to solve."""
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    """State ID of the parent state, if any. Should be None if this is the first state in a session."""

    num_solutions: int = Field(default=0)
    """Number of solutions to fetch. If 0, fetch all solutions."""


class EMOSaveRequest(SQLModel):
    """Request model for saving solutions from any method's state."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    problem_id: int
    """Database ID of the problem to solve."""
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    """State ID of the parent state, if any. Should be None if this is the first state in a session."""

    solution_ids: list[int] = Field()
    """List of solution IDs to save."""
    solution_names: list[str | None] | None = Field(default=None)
    """List of names for the solutions to save. If None, no names are given."""


class EMOScoreRequest(SQLModel):
    """Request model for getting SCORE bands visualization data from state."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    problem_id: int
    """Database ID of the problem to solve."""
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    """State ID of the parent state, if any."""

    solution_ids: list[int] = Field()
    """List of solution IDs to score."""


class EMOIterateResponse(SQLModel):
    """Model of the response to an EMO iterate request."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    method_ids: list[str]
    """IDs of the EMO methods using websockets to get/send updates."""
    client_id: str
    """Client ID to use when connecting to the websockets."""
    state_id: int
    """The state ID of the newly created state."""


class Solution(SQLModel):
    solution_id: int
    """ID of the solution"""
    objective_values: dict[str, list[float]]
    """Values of the objectives. Each inner list corresponds to a solution."""
    constraint_values: dict[str, list[float]] | None = None
    """Values of the constraints. Each inner list corresponds to a solution."""
    variable_values: dict[str, list[float | int | bool]]
    """Values of the decision variables. Each inner list corresponds to a solution."""
    extra_func_values: dict[str, list[float]] | None = None
    """Values of the extra functions. Each inner list corresponds to a solution."""


class EMOFetchResponse(SQLModel):
    """Model of the response to an EMO fetch request."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    state_id: int
    """The state ID of the newly created state."""
    objective_values: dict[str, list[float]]
    """Values of the objectives. Each inner list corresponds to a solution."""
    constraint_values: dict[str, list[float]] | None = None
    """Values of the constraints. Each inner list corresponds to a solution."""
    variable_values: dict[str, list[float | int | bool]]
    """Values of the decision variables. Each inner list corresponds to a solution."""
    extra_func_values: dict[str, list[float]] | None = None
    """Values of the extra functions. Each inner list corresponds to a solution."""


class EMOScoreResponse(SQLModel):
    """Model of the response to an EMO score request."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    state_id: int
    """The state ID of the newly created state."""
