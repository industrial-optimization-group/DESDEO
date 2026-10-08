"""Models for storing ScenarioModel instances in the database."""

from typing import TYPE_CHECKING

from sqlalchemy.types import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

from desdeo.problem.scenario import Scenario, ScenarioModel
from desdeo.problem.schema import (
    Constant,
    Constraint,
    ExtraFunction,
    Objective,
    Problem,
    ScalarizationFunction,
    TensorConstant,
    TensorVariable,
    Variable,
)

from .problem import (
    ConstantDB,
    ConstraintDB,
    ExtraFunctionDB,
    ObjectiveDB,
    ScalarizationFunctionDB,
    TensorConstantDB,
    TensorVariableDB,
    VariableDB,
)

if TYPE_CHECKING:
    from .problem import ProblemDB
    from .user import User

_EXCLUDE = {"id", "problem_id", "scenario_model_id"}


def _reinterleave(layout: list[str] | None, scalars: list, tensors: list) -> list:
    """Rebuild one combined pool list in its original scalar/tensor interleaving order.

    `layout` is a list like ["tensor", "scalar", "tensor", ...], one entry per original pool
    element, as recorded by `ScenarioModelDB.from_scenario_model`. Without a layout (rows
    persisted before `pool_layout` existed), falls back to the old scalars-then-tensors
    concatenation — correct only when the original pool was already single-typed.
    """
    if not layout:
        return [*scalars, *tensors]
    scalar_iter = iter(scalars)
    tensor_iter = iter(tensors)
    return [next(tensor_iter) if kind == "tensor" else next(scalar_iter) for kind in layout]


class ScenarioModelDB(SQLModel, table=True):
    """Database table model for ScenarioModel."""

    id: int | None = Field(primary_key=True, default=None)
    user_id: int | None = Field(foreign_key="user.id", default=None)
    base_problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    scenario_tree: dict = Field(sa_column=Column(JSON))
    scenarios: dict = Field(sa_column=Column(JSON))
    anticipation_stop: dict = Field(sa_column=Column(JSON), default={})
    scenario_probabilities: dict = Field(sa_column=Column(JSON), default={})
    # `Scenario.constants`/`.variables` index into ONE combined (scalar+tensor) pool list, but
    # this table stores scalars and tensors as two separate relationships. That loses the
    # original interleaving order needed to reconstruct matching indices — this records it as
    # e.g. {"constants": ["tensor", "scalar", ...], "variables": [...]}, one entry per original
    # pool element in order. Empty/missing (old rows) falls back to the pre-existing
    # scalars-then-tensors concatenation, which is only correct for an all-one-type pool.
    pool_layout: dict = Field(sa_column=Column(JSON), default={})

    # Relationships
    user: "User" = Relationship(back_populates="scenario_models")
    base_problem: "ProblemDB" = Relationship(back_populates="scenario_models")

    constants: list["ConstantDB"] = Relationship(
        back_populates="scenario_model", cascade_delete=True, sa_relationship_kwargs={"order_by": "ConstantDB.id"}
    )
    tensor_constants: list["TensorConstantDB"] = Relationship(
        back_populates="scenario_model",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "TensorConstantDB.id"},
    )
    variables: list["VariableDB"] = Relationship(
        back_populates="scenario_model", cascade_delete=True, sa_relationship_kwargs={"order_by": "VariableDB.id"}
    )
    tensor_variables: list["TensorVariableDB"] = Relationship(
        back_populates="scenario_model",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "TensorVariableDB.id"},
    )
    objectives: list["ObjectiveDB"] = Relationship(
        back_populates="scenario_model", cascade_delete=True, sa_relationship_kwargs={"order_by": "ObjectiveDB.id"}
    )
    constraints: list["ConstraintDB"] = Relationship(
        back_populates="scenario_model", cascade_delete=True, sa_relationship_kwargs={"order_by": "ConstraintDB.id"}
    )
    extra_funcs: list["ExtraFunctionDB"] = Relationship(
        back_populates="scenario_model",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "ExtraFunctionDB.id"},
    )
    scalarization_funcs: list["ScalarizationFunctionDB"] = Relationship(
        back_populates="scenario_model",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "ScalarizationFunctionDB.id"},
    )

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
        scalar_constants = [c for c in scenario_model.constants if isinstance(c, Constant)]
        tensor_constants = [c for c in scenario_model.constants if isinstance(c, TensorConstant)]
        scalar_variables = [v for v in scenario_model.variables if isinstance(v, Variable)]
        tensor_variables = [v for v in scenario_model.variables if isinstance(v, TensorVariable)]

        pool_layout = {
            "constants": ["tensor" if isinstance(c, TensorConstant) else "scalar" for c in scenario_model.constants],
            "variables": ["tensor" if isinstance(v, TensorVariable) else "scalar" for v in scenario_model.variables],
        }

        return cls(
            user_id=user.id,
            base_problem_id=base_problem_id,
            scenario_tree=scenario_model.scenario_tree,
            scenarios={name: s.model_dump() for name, s in scenario_model.scenarios.items()},
            anticipation_stop=scenario_model.anticipation_stop,
            scenario_probabilities=scenario_model.scenario_probabilities,
            pool_layout=pool_layout,
            constants=[ConstantDB.model_validate(c) for c in scalar_constants],
            tensor_constants=[TensorConstantDB.model_validate(c) for c in tensor_constants],
            variables=[VariableDB.model_validate(v) for v in scalar_variables],
            tensor_variables=[TensorVariableDB.model_validate(v) for v in tensor_variables],
            objectives=[ObjectiveDB.model_validate(o) for o in scenario_model.objectives],
            constraints=[ConstraintDB.model_validate(c) for c in scenario_model.constraints],
            extra_funcs=[ExtraFunctionDB.model_validate(e) for e in scenario_model.extra_funcs],
            scalarization_funcs=[ScalarizationFunctionDB.model_validate(s) for s in scenario_model.scalarization_funcs],
        )

    def to_scenario_model(self, base_problem: Problem) -> ScenarioModel:
        """Reconstruct a ScenarioModel Pydantic instance from this DB row.

        Args:
            base_problem: the reconstructed base Problem instance (loaded separately
                from the associated ProblemDB row).

        Returns:
            ScenarioModel: the reconstructed instance.
        """
        constants = _reinterleave(
            self.pool_layout.get("constants"),
            scalars=[Constant.model_validate(c.model_dump(exclude=_EXCLUDE)) for c in self.constants],
            tensors=[TensorConstant.model_validate(c.model_dump(exclude=_EXCLUDE)) for c in self.tensor_constants],
        )
        variables = _reinterleave(
            self.pool_layout.get("variables"),
            scalars=[Variable.model_validate(v.model_dump(exclude=_EXCLUDE)) for v in self.variables],
            tensors=[TensorVariable.model_validate(v.model_dump(exclude=_EXCLUDE)) for v in self.tensor_variables],
        )

        return ScenarioModel(
            scenario_tree=self.scenario_tree,
            base_problem=base_problem,
            constants=constants,
            variables=variables,
            objectives=[Objective.model_validate(o.model_dump(exclude=_EXCLUDE)) for o in self.objectives],
            constraints=[Constraint.model_validate(c.model_dump(exclude=_EXCLUDE)) for c in self.constraints],
            extra_funcs=[ExtraFunction.model_validate(e.model_dump(exclude=_EXCLUDE)) for e in self.extra_funcs],
            scalarization_funcs=[
                ScalarizationFunction.model_validate(s.model_dump(exclude=_EXCLUDE)) for s in self.scalarization_funcs
            ],
            scenarios={name: Scenario.model_validate(s) for name, s in self.scenarios.items()},
            anticipation_stop=self.anticipation_stop,
            scenario_probabilities=self.scenario_probabilities,
        )


class ScenarioModelInfo(SQLModel):
    """Response model for a stored ScenarioModel."""

    id: int
    user_id: int
    base_problem_id: int

    scenario_tree: dict
    scenarios: dict
    anticipation_stop: dict
    scenario_probabilities: dict

    constants: list["ConstantDB"]
    tensor_constants: list["TensorConstantDB"]
    variables: list["VariableDB"]
    tensor_variables: list["TensorVariableDB"]
    objectives: list["ObjectiveDB"]
    constraints: list["ConstraintDB"]
    extra_funcs: list["ExtraFunctionDB"]
    scalarization_funcs: list["ScalarizationFunctionDB"]
