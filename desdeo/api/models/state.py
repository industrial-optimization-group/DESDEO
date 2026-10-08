"""Defines models for representing the state of various interactive methods."""

import warnings
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
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
    """An interface class for objects that contain results."""

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values of the result."""
        msg = (
            f"Calling the method `result_objective_values`, which has not been implemented "
            f"for the class `{type(self).__name__}`. Returning an empty list..."
        )

        warnings.warn(msg, category=RuntimeWarning, stacklevel=2)

        return []

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values of the result."""
        msg = (
            f"Calling the method `result_variable_values`, which has not been implemented "
            f"for the class `{type(self).__name__}`. Returning an empty list..."
        )

        warnings.warn(msg, category=RuntimeWarning, stacklevel=2)

        return []

    @property
    def num_solutions(self) -> int:
        """Number of solutions in the result."""
        msg = (
            f"Calling the method `num_solutions`, which has not been implemented "
            f"for the class `{type(self).__name__}`. Returning a zero."
        )

        warnings.warn(msg, category=RuntimeWarning, stacklevel=2)

        return 0


class RPMState(SQLModel, table=True):
    """Reference Point Method (k+1 candidates)."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    # inputs
    preferences: ReferencePoint = Field(sa_column=Column(PreferenceType))
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))


class DistrictHeatingIterationState(SQLModel, table=True):
    """District Heating System: one round of scenario-robust reference-point matching.

    Reads a pre-computed candidate pool (see `desdeo.api.routers.district_heating_system_data`);
    never solves a `Problem`. `already_shown_ids`/`solution_number_map` are carried forward from
    iteration to iteration (mirroring the module-level state in `the_DM_session.ipynb`) so a design
    is never re-matched once shown.
    """

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    # inputs
    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    max_solutions: int | None = None
    note: str | None = None

    # running bookkeeping carried forward from the previous iteration state
    already_shown_ids: list[int] = Field(sa_column=Column(JSON), default_factory=list)
    solution_number_map: dict[str, int] = Field(
        sa_column=Column(JSON), default_factory=dict, description="design_id (as str) -> solution number"
    )

    # results: one dict per matched design (design_id, solution_number, matched_by,
    # n_scenarios, rows, worst_case, best_case) — see DistrictHeatingMatchedSolution.
    solutions: list[dict] = Field(sa_column=Column(JSON), default_factory=list)


class DistrictHeatingWishlistState(SQLModel, table=True):
    """District Heating System: a wish-list add/remove action."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    wish_list: list[int] = Field(sa_column=Column(JSON), default_factory=list)


class DistrictHeatingRobustIterationState(SQLModel, table=True):
    """District Heating System — Robust: one round of live robust-solve matching.

    Unlike `DistrictHeatingIterationState`, this builds and solves a real `Problem` on every
    iteration (see `desdeo.api.routers.district_heating_robust_data`) — designs can never be
    excluded once shown (only flagged as a repeat), since every scalarizer variant re-solves
    live each time. `design_registry`/`solution_number_map` are carried forward from iteration
    to iteration (mirroring the module-level state in `multi_scenario_DM_session.ipynb`).
    """

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    # inputs
    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    note: str | None = None
    iteration_number: int = 1

    # running bookkeeping carried forward from the previous iteration state. Each design_registry
    # entry: {"signature": list[int], "first_iteration": int, "robust_vals": dict, "strategic_vals":
    # dict, "breakdown": list[dict]} — "signature" round-trips through JSON as a list, not a tuple;
    # convert back to tuple before comparing against a freshly computed signature.
    design_registry: dict[str, dict] = Field(
        sa_column=Column(JSON), default_factory=dict, description="design_id (as str) -> registry entry"
    )
    solution_number_map: dict[str, int] = Field(
        sa_column=Column(JSON), default_factory=dict, description="design_id (as str) -> solution number"
    )

    # results: one dict per matched design this round — see DistrictHeatingRobustMatchedSolution.
    solutions: list[dict] = Field(sa_column=Column(JSON), default_factory=list)


class DistrictHeatingRobustWishlistState(SQLModel, table=True):
    """District Heating System — Robust: a wish-list add/remove action."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    wish_list: list[int] = Field(sa_column=Column(JSON), default_factory=list)


class DistrictHeatingCombinedIterationState(SQLModel, table=True):
    """District Heating System — Combined multi-scenario: one ASF solve over per-cell aspirations.

    Separate from `DistrictHeatingRobustIterationState` because the preference itself lives in a
    different key space: this method's `reference_point` is keyed by combined-problem symbol (one
    per (objective, scenario) cell), not by base objective symbol. Storing both in one table would
    make that key space ambiguous to anything reading the state back.

    One solve per iteration means one design per iteration, so there is no scalarizer-variant
    matching to record — but a design can still resurface in a later round, so
    `design_registry`/`solution_number_map` are carried forward the same way, keyed by the
    first-stage design's signature.
    """

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    # inputs
    reference_point: dict[str, float] = Field(sa_column=Column(JSON))
    note: str | None = None
    iteration_number: int = 1

    # running bookkeeping carried forward from the previous iteration state. Each entry:
    # {"signature": list[int], "first_iteration": int, "strategic_vals": dict, "breakdown":
    # list[dict], "objective_values": dict} — "signature" round-trips through JSON as a list, not a
    # tuple; convert back before comparing against a freshly computed signature.
    design_registry: dict[str, dict] = Field(
        sa_column=Column(JSON), default_factory=dict, description="design_id (as str) -> registry entry"
    )
    solution_number_map: dict[str, int] = Field(
        sa_column=Column(JSON), default_factory=dict, description="design_id (as str) -> solution number"
    )

    # results of this round
    alpha: float = 0.0
    all_reached: bool = False
    design_id: int = 0
    solution_number: int = 0
    repeat: bool = False
    cell_results: list[dict] = Field(sa_column=Column(JSON), default_factory=list)
    strategic_values: dict[str, float] = Field(sa_column=Column(JSON), default_factory=dict)
    breakdown: list[dict] = Field(
        sa_column=Column(JSON),
        default_factory=list,
        description="Per-scenario objective rows for this round's design, in base objective symbols.",
    )
    max_solutions: int | None = Field(
        default=None, description="Cap the DM asked for on how many designs to show this round; null means all."
    )
    solutions: list[dict] = Field(
        sa_column=Column(JSON),
        default_factory=list,
        description=(
            "Every distinct design this round produced, one per entry, in scalarizer priority "
            "order (balanced first). Each entry mirrors the single-design columns above plus "
            "`matched_by` (which scalarizer variants landed on it). Empty on rows written before "
            "this method solved more than one variant — read the single-design columns instead."
        ),
    )


class DistrictHeatingCombinedWishlistState(SQLModel, table=True):
    """District Heating System — Combined multi-scenario: a wish-list add/remove action."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    wish_list: list[int] = Field(sa_column=Column(JSON), default_factory=list)


class NIMBUSClassificationState(ResultInterface, SQLModel, table=True):
    """NIMBUS: classification / solve candidates."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    preferences: ReferencePoint = Field(sa_column=Column(PreferenceType))
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    current_objectives: dict[str, float] = Field(sa_column=Column(JSON), default_factory=dict)
    num_desired: int | None = 1
    previous_preferences: ReferencePoint = Field(sa_column=Column(PreferenceType))
    filtered_lagrange_multipliers: list[dict[str, float] | None] | None = Field(
        sa_column=Column(JSON),
        default=None,
    )
    tradeoffs_matrix: list[dict[str, dict[str, float]] | None] | None = Field(
        sa_column=Column(JSON),
        default=None,
    )

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values of the result."""
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values of the result."""
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        """Number of solutions in the result."""
        return len(self.solver_results)


class NIMBUSSaveState(ResultInterface, SQLModel, table=True):
    """NIMBUS: save solutions."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    solutions: list["UserSavedSolutionDB"] = Relationship(
        sa_relationship_kwargs={
            # tell SQLA which FK on the child points back to THIS parent
            "foreign_keys": "[UserSavedSolutionDB.save_state_id]",
            "primaryjoin": "NIMBUSSaveState.id == UserSavedSolutionDB.save_state_id",
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        }
    )

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values of the saved solutions."""
        return [x.objective_values for x in self.solutions]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values of the saved solutions."""
        return [x.variable_values for x in self.solutions]

    @property
    def num_solutions(self) -> int:
        """Number of solutions in the result."""
        return len(self.solutions)


class NIMBUSInitializationState(ResultInterface, SQLModel, table=True):
    """NIMBUS: initialization."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    reference_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    # Results
    solver_results: "SolverResults" = Field(sa_column=Column(ResultsType), default_factory=list)

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values stored in the state."""
        return [self.solver_results.optimal_objectives]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values stored in the state."""
        return [self.solver_results.optimal_variables]

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        return 1


class NIMBUSFinalState(ResultInterface, SQLModel, table=True):
    """NIMBUS: The Final State.

    NOTE: Despite this being the "final" state, I think the user should
    still be allowed to use this as a basis for new iterations. Therefore
    I think this should behave/have necessary elements for that to be the case.
    """

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    solution_origin_state_id: int = Field(description="The state from which the solution originates.")
    solution_result_index: int = Field(description="The index within that state.")

    solver_results: "SolverResults" = Field(sa_column=Column(ResultsType), default_factory=list)

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values stored in the state."""
        return [self.solver_results.optimal_objectives]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values stored in the state."""
        return [self.solver_results.optimal_variables]

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        return 1


class CumulusClassificationState(ResultInterface, SQLModel, table=True):
    """CUMULUS: classification / solve candidates."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    preferences: ReferencePoint = Field(sa_column=Column(PreferenceType))
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    current_objectives: dict[str, float] = Field(sa_column=Column(JSON), default_factory=dict)
    scalarizations: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    original_problem_id: int | None = Field(default=None)
    scenario_model_id: int | None = Field(default=None)

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values of the result."""
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values of the result."""
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        """Number of solutions in the result."""
        return len(self.solver_results)


class CumulusInitializationState(ResultInterface, SQLModel, table=True):
    """CUMULUS: initialization."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    reference_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    original_problem_id: int | None = Field(default=None)
    scenario_model_id: int | None = Field(default=None)

    solver_results: "SolverResults" = Field(sa_column=Column(ResultsType), default_factory=list)

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values stored in the state."""
        return [self.solver_results.optimal_objectives]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values stored in the state."""
        return [self.solver_results.optimal_variables]

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        return 1


class CumulusFinalState(ResultInterface, SQLModel, table=True):
    """CUMULUS: The Final State."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    solution_origin_state_id: int = Field(description="The state from which the solution originates.")
    solution_result_index: int = Field(description="The index within that state.")
    original_problem_id: int | None = Field(default=None)

    solver_results: "SolverResults" = Field(sa_column=Column(ResultsType), default_factory=list)

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values stored in the state."""
        return [self.solver_results.optimal_objectives]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values stored in the state."""
        return [self.solver_results.optimal_variables]

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        return 1


class CumulusSaveState(ResultInterface, SQLModel, table=True):
    """CUMULUS: save solutions."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    original_problem_id: int | None = Field(default=None)

    solutions: list["UserSavedSolutionDB"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[UserSavedSolutionDB.save_state_id]",
            "primaryjoin": "CumulusSaveState.id == UserSavedSolutionDB.save_state_id",
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
            "overlaps": "solutions",
        }
    )

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values of the saved solutions."""
        return [x.objective_values for x in self.solutions]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values of the saved solutions."""
        return [x.variable_values for x in self.solutions]

    @property
    def num_solutions(self) -> int:
        """Number of solutions in the result."""
        return len(self.solutions)


class CumulusModificationState(ResultInterface, SQLModel, table=True):
    """CUMULUS: problem modification — records the new problem created after a modification step."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    problem_id: int = Field(description="ID of the newly created modified problem.")
    original_problem_id: int | None = Field(default=None)
    scenario_model_id: int | None = Field(default=None)
    is_ready: bool = Field(default=False, description="True once the background feasibility check has completed.")
    error: str | None = Field(default=None, description="Error message if the feasibility check failed.")

    @property
    def num_solutions(self) -> int:
        """Problem modification states hold no solutions."""
        return 0


class CumulusObjectiveConstraintState(ResultInterface, SQLModel, table=True):
    """CUMULUS: objective constraints — stores the current set of objective-space constraints."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    problem_id: int | None = Field(default=None, description="Problem these constraints are associated with.")
    original_problem_id: int | None = Field(default=None)
    hard_constraint_ids: list[int] = Field(
        sa_column=Column(JSON),
        default_factory=list,
        description="DB ids of the hard ConstraintDB rows in the current objective constraint list.",
    )
    soft_constraint_ids: list[int] = Field(
        sa_column=Column(JSON),
        default_factory=list,
        description="DB ids of the soft ConstraintDB rows in the current objective constraint list.",
    )

    @property
    def num_solutions(self) -> int:
        """Objective constraint states hold no solutions."""
        return 0


class GNIMBUSOptimizationState(ResultInterface, SQLModel, table=True):
    """GNIMBUS: classification / solving."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    # Preferences that went in
    reference_points: dict[int, dict[str, float]] = Field(sa_column=Column(JSON))
    # Results that came out
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values stored in the state."""
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values stored in the state."""
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        return len(self.solver_results)


class GNIMBUSVotingState(ResultInterface, SQLModel, table=True):
    """GNIMBUS: voting."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    # Preferences that went in
    votes: dict[int, int] = Field(sa_column=Column(JSON))
    # Results that came out
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values stored in the state."""
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values stored in the state."""
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        return 1


class GNIMBUSEndState(ResultInterface, SQLModel, table=True):
    """GNIMBUS: ending. We check if everyone's happy with the solution and end if yes."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    # Preferences that went in
    votes: dict[int, bool] = Field(sa_column=Column(JSON))
    # Success?
    success: bool = Field()
    # Results that came out
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values stored in the state."""
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values stored in the state."""
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        return 1


class EMOIterateState(ResultInterface, SQLModel, table=True):
    """EMO run (NSGA3, RVEA, etc.)."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

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
        """Objective values stored in the state."""
        if self.objective_values is None:
            raise ValueError("No objective values stored in this state.")
        return self.objective_values

    @property
    def result_variable_values(self) -> dict[str, list[VariableType]]:
        """Variable values stored in the state."""
        if self.decision_variables is None:
            raise ValueError("No decision variables stored in this state.")
        return self.decision_variables

    @property
    def result_constraint_values(self) -> dict[str, list[float]] | None:
        """Constraint values stored in the state."""
        return self.constraint_values

    @property
    def result_extra_func_values(self) -> dict[str, list[float]] | None:
        """Extra function values stored in the state."""
        return self.extra_func_values

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        if self.objective_values:
            first_key = next(iter(self.objective_values))
            return len(self.objective_values[first_key])
        return 0


class EMOFetchState(SQLModel, table=True):
    """Request model for fetching EMO solutions."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))
    # More fields can be added here if needed in the future. E.g., number of solutions to fetch, filters, etc.


class EMOSCOREState(SQLModel, table=True):
    """EMO: SCORE iteration."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    result: SCOREBandsResult = Field(sa_column=Column(JSON))


class EMOSaveState(SQLModel, table=True):
    """EMO: save solutions."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

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
        """Objective values stored in the state."""
        return self.objective_values

    @property
    def result_variable_values(self) -> dict[str, list[VariableType]]:
        """Variable values stored in the state."""
        return self.decision_variables

    @property
    def result_constraint_values(self) -> dict[str, list[float]] | None:
        """Constraint values stored in the state."""
        return self.constraint_values

    @property
    def result_extra_func_values(self) -> dict[str, list[float]] | None:
        """Extra function values stored in the state."""
        return self.extra_func_values

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        if self.objective_values:
            first_key = next(iter(self.objective_values))
            return len(self.objective_values[first_key])
        return 0


class IntermediateSolutionState(SQLModel, ResultInterface, table=True):
    """Generic intermediate solutions requested by other methods."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

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
        """Objective values stored in the state."""
        return [x.optimal_objectives for x in self.solver_results]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType]]:
        """Variable values stored in the state."""
        return [x.optimal_variables for x in self.solver_results]

    @property
    def num_solutions(self) -> int:
        """Number of solutions store in the state."""
        return len(self.solver_results)


class ENautilusState(SQLModel, table=True):
    """E-NAUTILUS: one stepping iteration."""

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    non_dominated_solutions_id: int | None = Field(foreign_key="representativenondominatedsolutions.id", default=None)

    current_iteration: int
    iterations_left: int
    selected_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    reachable_point_indices: list[int] = Field(sa_column=Column(JSON), default_factory=list)
    number_of_intermediate_points: int

    enautilus_results: "ENautilusResult" = Field(sa_column=Column(ResultsType))

    non_dominated_solutions: "RepresentativeNonDominatedSolutions" = Relationship()


class ENautilusFinalState(ResultInterface, SQLModel, table=True):
    """E-NAUTILUS: The final selected solution.

    Created when the DM selects their final solution from the last iteration
    (when iterations_left == 0). The selected intermediate point is projected
    to the nearest point on the representative Pareto front.
    """

    id: int | None = Field(sa_column=Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True))

    # Reference to the step state from which the final solution was selected
    origin_step_state_id: int = Field(description="The E-NAUTILUS step state from which the solution was selected.")
    # Index of the selected intermediate point in that state
    selected_point_index: int = Field(description="Index of the selected intermediate point.")
    # The intermediate point that was selected (for reference)
    selected_intermediate_point: dict[str, float] = Field(
        sa_column=Column(JSON),
        description="The intermediate point selected by the DM.",
    )

    # The projected solution on the representative Pareto front.
    # NOTE: This is the nearest point on the REPRESENTATIVE set, not the true Pareto front.
    # A true Pareto optimal solution dominating this point likely exists but would require
    # additional optimization to find. For problems with expensive evaluations, this
    # representative solution is used as a practical approximation.
    solver_results: SolverResults = Field(
        sa_column=Column(ResultsType),
        description=(
            "The final solution projected to the representative Pareto front. "
            "Note: This is the nearest point on the representative set; a true Pareto "
            "optimal solution dominating this point may exist."
        ),
    )

    @property
    def result_objective_values(self) -> list[dict[str, float]]:
        """Objective values stored in the state."""
        return [self.solver_results.optimal_objectives]

    @property
    def result_variable_values(self) -> list[dict[str, VariableType | Tensor]]:
        """Variable values stored in the state."""
        return [self.solver_results.optimal_variables]

    @property
    def num_solutions(self) -> int:
        """Number of solutions stored in the state."""
        return 1
