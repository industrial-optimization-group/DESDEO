"""All models for the API. I put them all in a single file for simplicity."""

# TODO: ADD TIMESTAMP COLUMNS TO ALL TABLES

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT, JSON, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from desdeo.api import schema
from desdeo.api.db import Base


class User(Base):
    """A user with a password, stored problems, role, and user group."""

    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[schema.UserRole] = mapped_column(nullable=False)
    user_group: Mapped[str] = mapped_column(nullable=True)
    privilages: Mapped[list[schema.UserPrivileges]] = mapped_column(ARRAY(Enum(schema.UserPrivileges)), nullable=False)

    def __repr__(self):
        """Return a string representation of the user (username)."""
        return f"User: ('{self.username}')"


class Problem(Base):
    """A model to store a problem and its associated data."""

    __tablename__ = "problem"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    owner = mapped_column(Integer, ForeignKey("user.id"), nullable=True)  # Null if problem is public.
    name: Mapped[str] = mapped_column(nullable=False)
    # kind and obj_kind are also in value, but we need them as columns for querying. Maybe?
    kind: Mapped[schema.ProblemKind] = mapped_column(nullable=False)
    obj_kind: Mapped[schema.ObjectiveKind] = mapped_column(nullable=False)
    role_permission: Mapped[list[schema.UserRole]] = mapped_column(ARRAY(Enum(schema.UserRole)), nullable=True)
    # We need some way to tell the API what solver should be used, and this seems like a good place
    # This should match one of the available_solvers in desdeo.tools.utils
    solver: Mapped[schema.Solvers] = mapped_column(nullable=True)
    # Other code assumes these ideals and nadirs are dicts with objective symbols as keys
    presumed_ideal = mapped_column(JSONB, nullable=True)
    presumed_nadir = mapped_column(JSONB, nullable=True)
    # Mapped doesn't work with JSON, so we use JSON directly.
    value = mapped_column(JSON, nullable=False)  # desdeo.problem.schema.Problem


class UserProblemAccess(Base):
    """A model to store user's access to problems."""

    __tablename__ = "user_problem_access"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    problem_access: Mapped[int] = mapped_column(Integer, ForeignKey("problem.id"), nullable=False)
    problem = relationship("Problem", foreign_keys=[problem_access], lazy="selectin")


class Method(Base):
    """A model to store a method and its associated data."""

    __tablename__ = "method"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    kind: Mapped[schema.Methods] = mapped_column(Enum(schema.Methods), nullable=False)
    properties: Mapped[list[schema.MethodProperties]] = mapped_column(
        ARRAY(Enum(schema.MethodProperties)), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    parameters = mapped_column(JSON, nullable=True)


class Preference(Base):
    """A model to store user preferences provided by the DM."""

    __tablename__ = "preference"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    problem = mapped_column(Integer, ForeignKey("problem.id"), nullable=False)
    previous_preference = mapped_column(Integer, ForeignKey("preference.id"), nullable=True)
    method = mapped_column(Integer, ForeignKey("method.id"), nullable=False)
    kind: Mapped[str]  # Depends on the method
    value = mapped_column(JSON, nullable=False)


class MethodState(Base):
    """A model to store the state of a method. Contains all the information needed to restore the state of a method."""

    __tablename__ = "method_state"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    problem = mapped_column(Integer, ForeignKey("problem.id"), nullable=False)
    method = mapped_column(Integer, ForeignKey("method.id"), nullable=False)  # Honestly, this can just be a string.
    preference = mapped_column(Integer, ForeignKey("preference.id"), nullable=True)
    value = mapped_column(JSON, nullable=False)  # Depends on the method.


class Results(Base):
    """A model to store the results of a method run.

    The results can be partial or complete, depending on the method. For example, NAUTILUS can return ranges instead of
    solutions. The overlap between the Results and SolutionArchive tables is intentional. Though if you have a better
    idea, feel free to change it.
    """

    __tablename__ = "results"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    problem = mapped_column(Integer, ForeignKey("problem.id"), nullable=False)
    # TODO: The method is temporarily nullable for initial testing. It should be non-nullable.
    method = mapped_column(Integer, ForeignKey("method.id"), nullable=True)
    method_state = mapped_column(Integer, ForeignKey("method_state.id"), nullable=True)
    value = mapped_column(JSON, nullable=False)  # Depends on the method


class SolutionArchive(Base):
    """A model to store a solution archive.

    The archive can be used to store the results of a method run. Note that each entry must be a single,
    complete solution. This is different from the Results table, which can store partial results.
    """

    __tablename__ = "solution_archive"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    problem = mapped_column(Integer, ForeignKey("problem.id"), nullable=False)
    method = mapped_column(Integer, ForeignKey("method.id"), nullable=False)
    preference = mapped_column(Integer, ForeignKey("preference.id"), nullable=True)
    decision_variables = mapped_column(JSONB, nullable=True)
    objectives = mapped_column(ARRAY(FLOAT), nullable=False)
    constraints = mapped_column(ARRAY(FLOAT), nullable=True)
    extra_funcs = mapped_column(ARRAY(FLOAT), nullable=True)
    other_info = mapped_column(
        JSON,
        nullable=True,
    )  # Depends on the method. May include things such as scalarization functions value, etc.
    saved: Mapped[bool] = mapped_column(nullable=False)
    current: Mapped[bool] = mapped_column(nullable=False)
    chosen: Mapped[bool] = mapped_column(nullable=False)


class Log(Base):
    """A model to store logs of user actions. I have no idea what to put in this table."""

    __tablename__ = "log"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    action: Mapped[str] = mapped_column(nullable=False)
    value = mapped_column(JSON, nullable=False)
    timestamp: Mapped[str] = mapped_column(nullable=False)


class Utopia(Base):
    """A model to store user specific information relating to Utopia problems."""

    __tablename__ = "utopia"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    problem: Mapped[int] = mapped_column(Integer, ForeignKey("problem.id"), nullable=False)
    user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    map_json: Mapped[str] = mapped_column(nullable=False)
    schedule_dict = mapped_column(JSONB, nullable=False)
    years: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    stand_id_field: Mapped[str] = mapped_column(String, nullable=False)
    stand_descriptor = mapped_column(JSONB, nullable=True)
