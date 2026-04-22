"""Models for storing ScenarioModel instances in the database."""

from typing import TYPE_CHECKING

from sqlmodel import Column, Field, Relationship, SQLModel
from sqlalchemy.types import JSON

from desdeo.problem.scenario import Scenario, ScenarioModel
from desdeo.problem.schema import (
    Constant,
    Constraint,
    ExtraFunction,
    Objective,
    Problem,
    ScalarizationFunction,
    TensorConstant,
    Variable,
)

if TYPE_CHECKING:
    from .problem import ProblemDB
    from .user import User


class ScenarioModelDB(SQLModel, table=True):
    """Database table model for ScenarioModel."""

    id: int | None = Field(primary_key=True, default=None)
    user_id: int | None = Field(foreign_key="user.id", default=None)
    base_problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    scenario_tree: dict = Field(sa_column=Column(JSON))
    scenarios: dict = Field(sa_column=Column(JSON))
    anticipation_stop: dict = Field(sa_column=Column(JSON), default={})

    # Pool elements serialized as JSON lists
    constants: list = Field(sa_column=Column(JSON), default=[])
    variables: list = Field(sa_column=Column(JSON), default=[])
    objectives: list = Field(sa_column=Column(JSON), default=[])
    constraints: list = Field(sa_column=Column(JSON), default=[])
    extra_funcs: list = Field(sa_column=Column(JSON), default=[])
    scalarization_funcs: list = Field(sa_column=Column(JSON), default=[])

    user: "User" = Relationship(back_populates="scenario_models")
    base_problem: "ProblemDB" = Relationship(back_populates="scenario_models")

    @classmethod
    def from_scenario_model(
        cls,
        scenario_model: ScenarioModel,
        user: "User",
        base_problem_id: int,
    ) -> "ScenarioModelDB":
        """Create a ScenarioModelDB from a ScenarioModel Pydantic instance.

        Args:
            scenario_model: the ScenarioModel to persist.
            user: the owning user.
            base_problem_id: the DB id of the base ProblemDB row.

        Returns:
            ScenarioModelDB: the new DB instance (not yet added to a session).
        """
        return cls(
            user_id=user.id,
            base_problem_id=base_problem_id,
            scenario_tree=scenario_model.scenario_tree,
            scenarios={name: s.model_dump() for name, s in scenario_model.scenarios.items()},
            anticipation_stop=scenario_model.anticipation_stop,
            constants=[c.model_dump() for c in scenario_model.constants],
            variables=[v.model_dump() for v in scenario_model.variables],
            objectives=[o.model_dump() for o in scenario_model.objectives],
            constraints=[c.model_dump() for c in scenario_model.constraints],
            extra_funcs=[e.model_dump() for e in scenario_model.extra_funcs],
            scalarization_funcs=[s.model_dump() for s in scenario_model.scalarization_funcs],
        )

    def to_scenario_model(self, base_problem: Problem) -> ScenarioModel:
        """Reconstruct a ScenarioModel Pydantic instance from this DB row.

        Args:
            base_problem: the reconstructed base Problem instance (loaded separately
                from the associated ProblemDB row).

        Returns:
            ScenarioModel: the reconstructed instance.
        """
        constants = [
            TensorConstant.model_validate(c) if "shape" in c else Constant.model_validate(c)
            for c in self.constants
        ]
        return ScenarioModel(
            scenario_tree=self.scenario_tree,
            base_problem=base_problem,
            constants=constants,
            variables=[Variable.model_validate(v) for v in self.variables],
            objectives=[Objective.model_validate(o) for o in self.objectives],
            constraints=[Constraint.model_validate(c) for c in self.constraints],
            extra_funcs=[ExtraFunction.model_validate(e) for e in self.extra_funcs],
            scalarization_funcs=[ScalarizationFunction.model_validate(s) for s in self.scalarization_funcs],
            scenarios={name: Scenario.model_validate(s) for name, s in self.scenarios.items()},
            anticipation_stop=self.anticipation_stop,
        )


class ScenarioModelInfo(SQLModel):
    """Response model for a stored ScenarioModel."""

    id: int
    user_id: int
    base_problem_id: int

    scenario_tree: dict
    scenarios: dict
    anticipation_stop: dict

    constants: list
    variables: list
    objectives: list
    constraints: list
    extra_funcs: list
    scalarization_funcs: list
