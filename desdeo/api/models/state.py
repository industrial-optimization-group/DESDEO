"""Defines models for representing the state of various interactive methods."""

import warnings
from typing import TYPE_CHECKING

from sqlalchemy.types import TypeDecorator
from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    SQLModel,
)

from desdeo.emo.options.templates import PreferenceOptions, TemplateOptions
from desdeo.mcdm import ENautilusResult
from desdeo.problem import Tensor, VariableType
from desdeo.tools import SolverResults
from desdeo.tools.score_bands import SCOREBandsResult

from .preference import PreferenceType, ReferencePoint

if TYPE_CHECKING:
    from .problem import RepresentativeNonDominatedSolutions
    from .state_table import UserSavedSolutionDB


class ResultsType(TypeDecorator):
    """SQLAlchemy custom type to convert a `SolverResults` and similar to JSON and back."""

    impl = JSON

    def process_bind_param(self, value, dialect):
        """`SolverResults` to JSON."""
        if value is None:
            return None

        if isinstance(value, list):
            return [x.model_dump() if hasattr(x, "model_dump") else x for x in value]

        if hasattr(value, "model_dump"):
            return value.model_dump()

        msg = f"No JSON serialization set for '{type(value)}'."
        print(msg)

        return value

    def process_result_value(self, value, dialect):
        """JSON to `SolverResults` or similar."""
        # Stupid way to to this, but works for now. Needs to add field
        # to the corresponding models so that they may be identified in dict form.
        # TODO: see above
        if "closeness_measures" in value:  # noqa: SIM108
            model = ENautilusResult
        else:
            model = SolverResults

        if value is None:
            return None
        if isinstance(value, list):
            return [model.model_validate(x) for x in value]

        return model.model_validate(value)


class ResultInterface:
    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        msg = (
            f"Calling the method `result_objective_values`, which has not been implemented "
            f"for the class `{type(self).__name__}`. Returning an empty list..."
        )

        warnings.warn(msg, category=RuntimeWarning, stacklevel=2)

        return []

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        msg = (
            f"Calling the method `result_variable_values`, which has not been implemented "
            f"for the class `{type(self).__name__}`. Returning an empty list..."
        )

        warnings.warn(msg, category=RuntimeWarning, stacklevel=2)

        return []

    @property
    def num_solutions(self) -> int:
        msg = (
            f"Calling the method `num_solutions`, which has not been implemented "
            f"for the class `{type(self).__name__}`. Returning a zero."
        )

        warnings.warn(msg, category=RuntimeWarning, stacklevel=2)

        return 0


class RPMState(SQLModel, table=True):
    """Reference Point Method (k+1 candidates)."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    # inputs
    preferences: ReferencePoint = Field(sa_column=Column(PreferenceType))
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))


class NIMBUSClassificationState(ResultInterface, SQLModel, table=True):
    """NIMBUS: classification / solve candidates."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    preferences: ReferencePoint = Field(sa_column=Column(PreferenceType))
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    current_objectives: dict[str, float] = Field(sa_column=Column(JSON), default_factory=dict)
    num_desired: int | None = 1
    previous_preferences: ReferencePoint = Field(sa_column=Column(PreferenceType))

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        return len(self.solver_results)


class NIMBUSSaveState(ResultInterface, SQLModel, table=True):
    """NIMBUS: save solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    solutions: list["UserSavedSolutionDB"] = Relationship(
        sa_relationship_kwargs={
            # tell SQLA which FK on the child points back to THIS parent
            "foreign_keys": "[UserSavedSolutionDB.origin_state_id]",
            "primaryjoin": "NIMBUSSaveState.id == UserSavedSolutionDB.origin_state_id",
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        }
    )

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        return [x.objective_values for x in self.solutions]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        return [x.variable_values for x in self.solutions]

    @property
    def num_solutions(self) -> int:
        return len(self.solutions)


class NIMBUSInitializationState(ResultInterface, SQLModel, table=True):
    """NIMBUS: initialization."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    reference_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    # Results
    solver_results: "SolverResults" = Field(sa_column=Column(ResultsType), default_factory=list)

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        return [self.solver_results.optimal_objectives]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        return [self.solver_results.optimal_variables]

    @property
    def num_solutions(self) -> int:
        return 1


class NIMBUSFinalState(ResultInterface, SQLModel, table=True):
    """NIMBUS: The Final State.

    NOTE: Despite this being the "final" state, I think the user should
    still be allowed to use this as a basis for new iterations. Therefore
    I think this should behave/have necessary elements for that to be the case.
    """
    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    solver_results: "SolverResults" = Field(sa_column=Column(ResultsType), default_factory=list) # the final solution
    reference_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None) # the reference point that led to the final solution

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        return [self.solver_results.optimal_objectives]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        return [self.solver_results.optimal_variables]

    @property
    def num_solutions(self) -> int:
        return 1


class GNIMBUSOptimizationState(ResultInterface, SQLModel, table=True):
    """GNIMBUS: classification / solving."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    # Preferences that went in
    reference_points: dict[int, dict[str, float]] = Field(sa_column=Column(JSON))
    # Results that came out
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        return len(self.solver_results)


class GNIMBUSVotingState(ResultInterface, SQLModel, table=True):
    """GNIMBUS: voting."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    # Preferences that went in
    votes: dict[int, int] = Field(sa_column=Column(JSON))
    # Results that came out
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        return 1


class EMOIterateState(ResultInterface, SQLModel, table=True):
    """EMO run (NSGA3, RVEA, etc.)."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    # algorithm flavor
    template_options: list[TemplateOptions] = Field(
        sa_column=Column(JSON)
    )  # TODO: This should probably be ids to another table
    # preferences
    preference_options: PreferenceOptions | None = Field(sa_column=Column(JSON))

    # results
    decision_variables: dict[str, list[VariableType]] | None = Field(
        sa_column=Column(JSON), description="Optimization results (decision variables)", default=None
    )  ## Unlike other methods, we have a very large number of solutions. So maybe we should store them together?
    objective_values: dict[str, list[float]] | None = Field(
        sa_column=Column(JSON), description="Optimization outputs", default=None
    )
    constraint_values: dict[str, list[float]] | None = Field(
        sa_column=Column(JSON), description="Constraint values of the solutions", default=None
    )
    extra_func_values: dict[str, list[float]] | None = Field(
        sa_column=Column(JSON), description="Extra function values of the solutions", default=None
    )

    @property
    def result_objective_values(self) -> dict[str, list[float]]:
        if self.objective_values is None:
            raise ValueError("No objective values stored in this state.")
        return self.objective_values

    @property
    def result_variable_values(self) -> dict[str, list[VariableType]]:
        if self.decision_variables is None:
            raise ValueError("No decision variables stored in this state.")
        return self.decision_variables

    @property
    def result_constraint_values(self) -> dict[str, list[float]] | None:
        return self.constraint_values

    @property
    def result_extra_func_values(self) -> dict[str, list[float]] | None:
        return self.extra_func_values

    @property
    def num_solutions(self) -> int:
        if self.objective_values:
            first_key = next(iter(self.objective_values))
            return len(self.objective_values[first_key])
        return 0


class EMOFetchState(SQLModel, table=True):
    """Request model for fetching EMO solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")
    # More fields can be added here if needed in the future. E.g., number of solutions to fetch, filters, etc.


class EMOSCOREState(SQLModel, table=True):
    """EMO: SCORE iteration."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    result: SCOREBandsResult = Field(sa_column=Column(JSON))


class EMOSaveState(SQLModel, table=True):
    """EMO: save solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    # results
    decision_variables: dict[str, list[VariableType]] = Field(
        sa_column=Column(JSON), description="Optimization results (decision variables)", default_factory=dict
    )  ## Unlike other methods, we have a very large number of solutions. So maybe we should store them together?
    objective_values: dict[str, list[float]] = Field(
        sa_column=Column(JSON), description="Optimization outputs", default_factory=dict
    )
    constraint_values: dict[str, list[float]] | None = Field(
        sa_column=Column(JSON), description="Constraint values of the solutions", default_factory=dict
    )
    extra_func_values: dict[str, list[float]] | None = Field(
        sa_column=Column(JSON), description="Extra function values of the solutions", default_factory=dict
    )
    names: list[str | None] = Field(
        default_factory=list, sa_column=Column(JSON), description="Names of the saved solutions"
    )

    @property
    def result_objective_values(self) -> dict[str, list[float]]:
        return self.objective_values

    @property
    def result_variable_values(self) -> dict[str, list[VariableType]]:
        return self.decision_variables

    @property
    def result_constraint_values(self) -> dict[str, list[float]] | None:
        return self.constraint_values

    @property
    def result_extra_func_values(self) -> dict[str, list[float]] | None:
        return self.extra_func_values

    @property
    def num_solutions(self) -> int:
        if self.objective_values:
            first_key = next(iter(self.objective_values))
            return len(self.objective_values[first_key])
        return 0


class IntermediateSolutionState(SQLModel, ResultInterface, table=True):
    """Generic intermediate solutions requested by other methods."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    context: str | None = Field(
        default=None,
        description="Originating method context (e.g., 'nimbus', 'rpm') that requested these solutions",
    )
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    num_desired: int | None = 1
    reference_solution_1: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    reference_solution_2: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType]]:
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        return len(self.solver_results)


class ENautilusState(SQLModel, table=True):
    """E-NAUTILUS: one stepping iteration."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    non_dominated_solutions_id: int | None = Field(foreign_key="representativenondominatedsolutions.id", default=None)

    current_iteration: int
    iterations_left: int
    selected_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    reachable_point_indices: list[int] = Field(sa_column=Column(JSON), default_factory=list)
    number_of_intermediate_points: int

    enautilus_results: "ENautilusResult" = Field(sa_column=Column(ResultsType))

    non_dominated_solutions: "RepresentativeNonDominatedSolutions" = Relationship()
