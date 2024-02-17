"""SQLAlchemy model for a user."""

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from desdeo.api.db import Base
from desdeo.api.models.user import User


class Preference(Base.Model):
    """A model to store user preferences provided by the DM."""

    __tablename__ = "preference"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user: Mapped["User"] = relationship("User", back_populates="preferences", lazy=True)
    problem: Mapped["Problem"] = relationship("Problem", lazy=True)
    next_preference: Mapped["Preference"] = relationship("Preference", back_populates="previous_preference", lazy=True)
    method: Mapped["Method"] = relationship("Method", lazy=True)
    preference_type: Mapped[str]
    value: Mapped[JSON]
