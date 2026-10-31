from __future__ import annotations

import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.core.security import hash_password
import enum


class UserRole(str, enum.Enum):
    """Who can publish featured content. Regular users own private uploads."""

    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=16), default=UserRole.user, index=True
    )
   
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
   
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"

    def set_password(self, password: str) -> None:
        self.password = hash_password(password)