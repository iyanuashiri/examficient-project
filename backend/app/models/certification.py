"""Certifications: the credential a set of exams ladders up to.

One certification → many exams. WAEC WASSCE (one certificate, ~9 subject
exams), JAMB UTME (one sitting, 4 subject tests), AWS SAA (one exam that is
effectively the whole certification), CFA (Level I → II → III ladder).
An exam with no certification is standalone.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Certification(TimestampMixin, Base):
    __tablename__ = "certification"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    issuing_body: Mapped[str | None] = mapped_column(String(255))
    level: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    exams: Mapped[list["Exam"]] = relationship(back_populates="certification")

    def __repr__(self) -> str:
        return f"<Certification(code={self.code!r})>"
