"""Upload records. The extractor writes drafts into Content tables; this just tracks the source file."""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.exam import Visibility


class Document(TimestampMixin, Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    filename: Mapped[str | None] = mapped_column(String(255))
    visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility, native_enum=False, length=16),
        default=Visibility.private,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename!r})>"
