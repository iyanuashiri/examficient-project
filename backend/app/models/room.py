"""Drill rooms: shareable timed windows for group practice.

Joins are inferred from attempts on the exam inside the window — no presence
tracking. Rooms are reached by numeric id (/rooms/42)."""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Room(TimestampMixin, Base):
    __tablename__ = "room"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    starts_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # House-run rooms (weekly mock, daily sprint): listed to everyone under
    # "Official". Player-created rooms stay private to their share link.
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    def __repr__(self) -> str:
        return f"<Room(id={self.id}, exam={self.exam_id})>"
