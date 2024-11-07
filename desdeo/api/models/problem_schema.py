"""."""

import json
from pathlib import Path
from types import UnionType

from pydantic import BaseModel, create_model
from sqlalchemy.types import String, TypeDecorator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from desdeo.problem.schema import (
    Constant,
    Constraint,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    ScalarizationFunction,
    Tensor,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableType,
)


class PathType(TypeDecorator):
    """SQLAlchemy custom type to convert Path to string (credit to @strfx on GitHUb!)."""

    impl = String

    def process_bind_param(self, value, dialect):
        """Path to string."""
        if isinstance(value, Path):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        """String to Path."""
        if value is not None:
            return Path(value)
        return value


class PathListType(TypeDecorator):
    """SQLAlchemy custom type to convert list[Path] to JSON."""

    impl = String

    def process_bind_param(self, value, dialect):
        """list[Path] to JSON."""
        if isinstance(value, list) and all(isinstance(item, Path) for item in value):
            return json.dumps([str(item) for item in value])
        return value  # Handle as a normal string if not a list of Paths

    def process_result_value(self, value, dialect):
        """JSON to list[Path]."""
        # Deserialize JSON back to a list of Path objects
        if value is not None:
            path_strings = json.loads(value)
            return [Path(item) for item in path_strings]
        return None


def from_pydantic(
    model_class: BaseModel,
    name: str,
    union_type_conversions: dict[type, type] | None = None,
    base_model: SQLModel = SQLModel,
) -> SQLModel:
    """Creates an SQLModel class from a pydantic model.

    Args:
        model_class (BaseClass): the pydantic class to be converted.
        name (str): the name given to the class.
        union_type_conversions (dict[type, type], optional): union type conversion table. This is needed, because
            SQLAlchemy expects all table columns to have a specific value. For example, a field with a type like
            `int | float | bool` cannot be stored in a database table because the field's type
            is ambiguous. In this case, storing whichever value originally stored in a the field as a
            `float` will suffice (because `int` and `bool` can be represented by floats).
            Therefore, a type conversion, such as `{int | float | bool: float}` is expected.
            Defaults to `None`.
        base_model (SQLModel, optional): a base SQLModel to override problematic fields in the `model_class`, such
            as lists or derived nested types. The base class may have custom validators to help convert
            these values into something more suitable to be stored in a database. Often storing the JSON
            representation of the problematic types is enough. If the `model_class` consists of only
            fields with primitive types, this argument can be left to its default value. Defaults to SQLModel.

    Raises:
        TypeError: one or more type conversions are missing for union types.

    Returns:
        SQLModel: the SQLModel corresponding to `model_class`.
    """
    # collect field in the base model, if defined, do not try to convert the type
    base_fields = base_model.model_fields

    if union_type_conversions is None:
        union_type_conversions = {}

    field_definitions = {}
    for field_name, field_info in model_class.model_fields.items():
        if field_name in base_fields:
            annotation = base_fields[field_name].annotation
            field_definitions[field_name] = (annotation, base_fields[field_name])
            continue

        if type(field_type := field_info.annotation) is UnionType:
            if field_type not in union_type_conversions:
                raise TypeError("Missing Union type conversion")

            annotation = union_type_conversions[field_type]
        else:
            annotation = field_info.annotation

        field_definitions[field_name] = (annotation, field_info)

    return create_model(name, __base__=base_model, **field_definitions)


class ProblemDB(SQLModel, table=True):
    """."""

    id: int | None = Field(primary_key=True, default=None)
    owner: int | None = Field(foreign_key="user.id")

    # Populated by other models
    constants: list["ConstantDB"] = Relationship(back_populates="problem")
    tensor_constants: list["TensorConstantDB"] = Relationship(back_populates="problem")
    variables: list["VariableDB"] = Relationship(back_populates="problem")
    tensor_variables: list["TensorVariableDB"] = Relationship(back_populates="problem")
    objectives: list["ObjectiveDB"] = Relationship(back_populates="problem")
    constraints: list["ConstraintDB"] = Relationship(back_populates="problem")
    scalarization_funcs: list["ScalarizationFunctionDB"] = Relationship(back_populates="problem")
    extra_funcs: list["ExtraFunctionDB"] = Relationship(back_populates="problem")
    discrete_representation: "DiscreteRepresentationDB" = Relationship(back_populates="problem")

    # name: str
    # description: str
    # objectives: list[Objective]
    # constraints: list[Constraint] | None
    # extra_funcs: list[ExtraFunction] | None
    # scalarization_funcs: list[ScalarizationFunction] | None
    # discrete_representation: DiscreteRepresentation | None
    # scenario_keys: list[str] | None


class _TensorConstant(SQLModel):
    """Helper class to override the field types of nested and list types."""

    values: Tensor = Field(sa_column=Column(JSON))
    shape: list[int] = Field(sa_column=Column(JSON))


_BaseTensorConstantDB = from_pydantic(
    TensorConstant,
    "_BaseTensorConstantDB",
    union_type_conversions={VariableType | None: float | None},
    base_model=_TensorConstant,
)


class TensorConstantDB(_BaseTensorConstantDB, table=True):
    """The SQLModel equivalent to `TensorConstant`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(default=None, foreign_key="problemdb.id")

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="tensor_constants")


_ConstantDB = from_pydantic(Constant, "_ConstantDB", union_type_conversions={VariableType: float})


class ConstantDB(_ConstantDB, table=True):
    """The SQLModel equivalent to `Constant`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="constants")


_VariableDB = from_pydantic(
    Variable, "_VariableDB", union_type_conversions={VariableType: float, VariableType | None: float | None}
)


class VariableDB(_VariableDB, table=True):
    """The SQLModel equivalent to `Variable`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="variables")


class _TensorVariable(SQLModel):
    """Helper class to override the field types of nested and list types."""

    initial_values: Tensor | None = Field(sa_column=Column(JSON))
    lowerbounds: Tensor | None = Field(sa_column=Column(JSON))
    upperbounds: Tensor | None = Field(sa_column=Column(JSON))
    shape: list[int] = Field(sa_column=Column(JSON))


_TensorVariableDB = from_pydantic(
    TensorVariable,
    "_TensorVariableDB",
    union_type_conversions={VariableType: float, VariableType | None: float | None},
    base_model=_TensorVariable,
)


class TensorVariableDB(_TensorVariableDB, table=True):
    """The SQLModel equivalent to `TensorVariable`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="tensor_variables")


class _Objective(SQLModel):
    """Helper class to override the fields of nested and list types, and Paths."""

    func: list = Field(sa_column=Column(JSON))
    scenario_keys: list[str] | None = Field(sa_column=Column(JSON), default=None)
    surrogates: list[Path] | None = Field(sa_column=Column(PathListType), default=None)
    simulator_path: Path | None = Field(sa_column=Column(PathType), default=None)


_ObjectiveDB = from_pydantic(
    Objective,
    "_ObjectiveDB",
    union_type_conversions={str | None: str | None, float | None: float | None},
    base_model=_Objective,
)


class ObjectiveDB(_ObjectiveDB, table=True):
    """The SQLModel equivalent to `Objective`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="objectives")


class _Constraint(SQLModel):
    """Helper class to override the fields of nested and list types, and Paths."""

    func: list = Field(sa_column=Column(JSON))
    scenario_keys: list[str] | None = Field(sa_column=Column(JSON), default=None)
    surrogates: list[Path] | None = Field(sa_column=Column(PathListType), default=None)
    simulator_path: Path | None = Field(sa_column=Column(PathType), default=None)


_ConstraintDB = from_pydantic(
    Constraint,
    "_ConstraintDB",
    union_type_conversions={str | None: str | None, float | None: float | None},
    base_model=_Constraint,
)


class ConstraintDB(_ConstraintDB, table=True):
    """The SQLModel equivalent to `Constraint`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="constraints")


class _ScalarizationFunction(SQLModel):
    """Helper class to override the fields of nested and list types, and Paths."""

    func: list = Field(sa_column=Column(JSON))
    scenario_keys: list[str] = Field(sa_column=Column(JSON))


_ScalarizationFunctionDB = from_pydantic(
    ScalarizationFunction,
    "_ScalarizationFunctionDB",
    union_type_conversions={str | None: str | None},
    base_model=_ScalarizationFunction,
)


class ScalarizationFunctionDB(_ScalarizationFunctionDB, table=True):
    """The SQLModel equivalent to `ScalarizationFunction`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="scalarization_funcs")


class _ExtraFunction(SQLModel):
    """Helper class to override the fields of nested and list types, and Paths."""

    func: list = Field(sa_column=Column(JSON))
    scenario_keys: list[str] | None = Field(sa_column=Column(JSON), default=None)
    surrogates: list[Path] | None = Field(sa_column=Column(PathListType), default=None)
    simulator_path: Path | None = Field(sa_column=Column(PathType), default=None)


_ExtraFunctionDB = from_pydantic(
    ExtraFunction, "_ExtraFunctionDB", union_type_conversions={str | None: str | None}, base_model=_ExtraFunction
)


class ExtraFunctionDB(_ExtraFunctionDB, table=True):
    """The SQLModel equivalent to `ExtraFunction`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="extra_funcs")


class _DiscreteRepresentation(SQLModel):
    """Helper class to override the fields of nested and list types, and Paths."""

    variable_values: dict[str, list[VariableType]] = Field(sa_column=Column(JSON))
    objective_values: dict[str, list[float]] = Field(sa_column=Column(JSON))


_DiscreteRepresentationDB = from_pydantic(
    DiscreteRepresentation, "_DiscreteRepresentation", base_model=_DiscreteRepresentation
)


class DiscreteRepresentationDB(_DiscreteRepresentationDB, table=True):
    """The SQLModel equivalent to `DiscreteRepresentation`."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: ProblemDB | None = Relationship(back_populates="discrete_representation")
