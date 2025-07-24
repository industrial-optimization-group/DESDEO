"""Defines a models for representing preferences."""

from typing import TYPE_CHECKING, ClassVar, Literal

from sqlalchemy.types import TypeDecorator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from .problem import ProblemDB

if TYPE_CHECKING:
    from .user import User


class PreferenceType(TypeDecorator):
    """SQLAlchemy custom type to convert a preferences to JSON and back.

    The reason for this TypeDecorator is to avoid model_dump when initializing
    `PreferenceDB` with instances and derivatives of `PreferenceBase`.
    """

    impl = JSON

    def process_bind_param(self, value, dialect):
        """Preference to JSON."""
        if isinstance(
            value,
            Bounds
            | ReferencePoint
            | PreferredRanges
            | PreferedSolutions
            | NonPreferredSolutions,
        ):
            return value.model_dump()

        msg = f"No JSON serialization set for preference type '{type(value)}'."
        print(msg)

        return value

    def process_result_value(self, value, dialect):
        """JSON to Preference."""
        if "preference_type" in value:
            match value["preference_type"]:
                case "reference_point":
                    return ReferencePoint.model_validate(value)
                case "bounds":
                    return Bounds.model_validate(value)
                case "preferred_solutions":
                    return PreferedSolutions.model_validate(value)
                case "non_preferred_solutions":
                    return NonPreferredSolutions.model_validate(value)
                case "preferred_ranges":  # Add this case
                    return PreferredRanges.model_validate(value)
                case _:
                    msg = f"No preference_type '{value['preference_type']}' found."
                    print(msg)

        return value


class PreferenceBase(SQLModel):
    """The base model for representing preferences."""

    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_on": "type",
        "polymorphic_identity": "preference_base",
    }

    preference_type: str = "unset"


class ReferencePoint(PreferenceBase):
    """Model for representing a reference point type of preference."""

    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_identity": "reference_point"
    }

    preference_type: Literal["reference_point"] = "reference_point"
    aspiration_levels: dict[str, float] = Field(sa_column=Column(JSON, nullable=False))


class Bounds(PreferenceBase):
    """Model for representing desired upper and lower bounds for objective functions."""

    __mapper_args__: ClassVar[dict[str, str]] = {"polymorphic_identity": "bounds"}

    preference_type: Literal["bounds"] = "bounds"

    # Bound can also be None, indicating that it is not bound
    lower_bounds: dict[str, float | None] = Field(
        sa_column=Column(JSON, nullable=False)
    )
    upper_bounds: dict[str, float | None] = Field(
        sa_column=Column(JSON, nullable=False)
    )


class PreferredRanges(PreferenceBase):
    """Model for representing desired upper and lower bounds for objective functions."""

    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_identity": "preferred_ranges"
    }

    preference_type: Literal["preferred_ranges"] = "preferred_ranges"

    preferred_ranges: dict[str, list[float]] = Field(
        sa_column=Column(JSON, nullable=False)
    )


class PreferedSolutions(PreferenceBase):
    """Model for representing a preferred solution type of preference."""

    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_identity": "preferred_solutions"
    }

    preference_type: Literal["preferred_solutions"] = "preferred_solutions"
    preferred_solutions: dict[str, list[float]] = Field(
        sa_column=Column(JSON, nullable=False)
    )


class NonPreferredSolutions(PreferenceBase):
    """Model for representing a non-preferred solution type of preference."""

    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_identity": "non_preferred_solutions"
    }

    preference_type: Literal["non_preferred_solutions"] = "non_preferred_solutions"
    non_preferred_solutions: dict[str, list[float]] = Field(
        sa_column=Column(JSON, nullable=False)
    )


class PreferenceDB(SQLModel, table=True):
    """Database model for storing preferences."""

    id: int | None = Field(primary_key=True, default=None)
    user_id: int | None = Field(foreign_key="user.id", default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    preference: PreferenceBase | None = Field(
        sa_column=Column(PreferenceType), default=None
    )

    # Back populates
    problem: "ProblemDB" = Relationship(back_populates="preferences")
    user: "User" = Relationship(back_populates="preferences")
