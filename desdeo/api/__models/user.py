"""SQLAlchemy model for a user."""

from passlib.hash import pbkdf2_sha256 as sha256
from sqlalchemy.orm import Mapped, mapped_column, relationship

from desdeo.api.db import Base
from desdeo.api.schema import UserRole


class User(Base.Model):
    """A user with a password, stored problems, role, and user group."""

    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    problems = relationship("Problem", back_populates="owner", lazy=True)
    role: Mapped[UserRole] = mapped_column(nullable=False)
    user_group: Mapped[str] = mapped_column(nullable=True)

    def __repr__(self):
        """Return a string representation of the user (username)."""
        return f"User: ('{self.username}')"

    @staticmethod
    def generate_hash(password: str) -> str:
        """Generate a hash from a password.

        Args:
            password: The password to hash.

        Returns:
            The hashed password.
        """
        return sha256.hash(password)

    @staticmethod
    def verify_hash(password: str, hashed: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: The password to verify.
            hashed (str): The hash to verify against.

        Returns:
            True if the password matches the hash, False otherwise.
        """
        return sha256.verify(password, hashed)
