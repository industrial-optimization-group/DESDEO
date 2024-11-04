"""."""

from types import UnionType

from pydantic import BaseModel, create_model
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from desdeo.problem.schema import Constant, Tensor, TensorConstant, Variable, VariableType


def from_pydantic(
    model_class: BaseModel, name: str, union_type_conversions: dict[type, type], base_model: SQLModel = SQLModel
) -> SQLModel:
    """Creates an SQLModel class from a pydantic model.

    Args:
        model_class (BaseClass): the pydantic class to be converted.
        name (str): the name given to the class.
        union_type_conversions (dict[type, type]): union type conversion table. This is needed, because
            SQLAlchemy expects all table columns to have a specific value. For example, a field with a type like
            `int | float | bool` cannot be stored in a database table because the field's type
            is ambiguous. In this case, storing whichever value originally stored in a the field as a
            `float` will suffice (because `int` and `bool` can be represented by floats).
            Therefore, a type conversion, such as `{int | float | bool: float}` is expected.
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

    # name: str
    # description: str
    # variables: list[Variable | TensorVariable]
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
