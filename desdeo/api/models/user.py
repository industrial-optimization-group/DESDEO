from passlib.hash import pbkdf2_sha256 as sha256
from sqlalchemy.orm import Mapped, mapped_column, relationship

from desdeo.api.db import Base
from desdeo.api.schema import UserRole


class UserModel(Base.Model):
    """A user with a password, stored problems, role, and user group."""

    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    problems = relationship("Problem", back_populates="owner", lazy=True)
    role: Mapped[UserRole] = mapped_column(nullable=False)
    user_group: Mapped[str] = mapped_column(nullable=True)

    def __repr__(self):
        return f"User: ('{self.username}')"

    @staticmethod
    def generate_hash(password):
        return sha256.hash(password)

    @staticmethod
    def verify_hash(password, hash):
        return sha256.verify(password, hash)


class TokenBlocklist(Base.Model):
    id = Base.Column(Base.Integer, primary_key=True)
    jti = Base.Column(Base.String(120), nullable=False)
    created_at = Base.Column(Base.DateTime, nullable=False)
