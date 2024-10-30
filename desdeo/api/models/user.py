"""Define models related to users."""

from enum import Enum
from typing import Any, Optional
from types import UnionType

from pydantic import BaseModel, create_model, field_validator
from sqlmodel import Field, SQLModel

from desdeo.problem import TensorConstant, Variable, VariableType
from desdeo.problem.schema import Tensor
import json


class UserRole(str, Enum):
    """Possible user roles."""

    guest = "guest"
    dm = "dm"
    analyst = "analyst"
    admin = "admin"


class UserBase(SQLModel):
    """Base user object."""

    username: str = Field(index=True)


class User(UserBase, table=True):
    """The table model of the user stored in the database."""

    id: int = Field(primary_key=True, unique=True)
    password_hash: str = Field()
    role: UserRole = Field()
    group: str = Field(default="")


class UserPublic(UserBase):
    """The object to handle public user information."""

    id: int
    role: UserRole
    group: str


"""Need to dump Tensors into JSON. Need custom base class for this. E.g.,

class VariableBase(SQLModel):
    tensor_data: Optional[str] = Field(default=None)

    def set_tensor_data(self, value: Any):
        self.tensor_data = json.dumps(value)

    def get_tensor_data(self) -> Any:
        return json.loads(self.tensor_data) if self.tensor_data else None

and

def tensor_custom_error_validator(value: TensorType) -> TensorType:
    # Your custom recursive validation logic here
    if not isinstance(value, (list, int, float, str, type(None))):
        raise ValueError("Invalid type for Tensor")
    # Additional recursive checks for nested lists, etc.
    return value

class MyModel(SQLModel, table=True):
    id: int = Field(primary_key=True)
    tensor_data: Optional[str] = Field(default=None)  # Store as JSON string

    @validator("tensor_data", pre=True, always=True)
    def validate_tensor_data(cls, v):
        if v is not None:
            # Validate the structure of the tensor data recursively
            tensor_custom_error_validator(v)
        return json.dumps(v) if v is not None else None
"""


def from_pydantic(model_class, union_type_conversions: dict):
    union_conversions = {key | None: value | None for key, value in union_type_conversions.items()}

    field_definitions = {}
    for name, field_info in model_class.__fields__.items():
        if type(field_type := field_info.annotation) is UnionType:
            if field_type not in union_conversions:
                raise TypeError("Missing Union type conversion")

            annotation = union_conversions[field_type]
        else:
            annotation = field_info.annotation
        field_definitions[name] = (annotation, field_info)

    # __base__ should also be dynamic and be a class that that inherits from SQLModel
    return create_model("VariableBase", __base__=SQLModel, **field_definitions)


VariableBase = from_pydantic(Variable, union_type_conversions={VariableType: float})


class _TensorConstant(SQLModel):
    def validate_tensor_value(cls, v):
        return json.dumps(v) if v is not None else None

    _validate_tensor = field_validator("values", mode="before", check_fields=False)(validate_tensor_value)


class VariableDB(VariableBase, table=True):
    id: int = Field(primary_key=True, unique=True)


print()
