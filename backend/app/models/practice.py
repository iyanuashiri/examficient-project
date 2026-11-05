"""Learner state. Derived from answers, never authored."""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Mastery(TimestampMixin, Base):
    """One learner's estimated mastery of one topic.

    ``theta`` is the Elo-style ability estimate, ``mastery_p`` the 0..1
    dashboard score. Missing row = unseen (prior).
    """

    __tablename__ = "mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_mastery_user_topic"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topic.id", ondelete="CASCADE"), index=True)
    theta: Mapped[float] = mapped_column(Float, default=0.0)
    mastery_p: Mapped[float] = mapped_column(Float, default=0.5)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    # Embedded-SR scheduling: when this topic should resurface. Set on every
    # answer from the topic's own history; the picker treats it as the primary
    # "is it due?" signal instead of raw days-since-seen.
    next_review_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Mastery(user={self.user_id}, topic={self.topic_id}, p={self.mastery_p:.2f})>"


class Enrollment(TimestampMixin, Base):
    """A user joined an exam: featured (open to all) or their own private one.

    One exam → many users. Holds per-user-per-exam details: when they joined
    and their personal deadline (defaults to the exam's official date).
    Mastery rows and attempts hang off the (user, exam) pair this represents.
    """

    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("user_id", "exam_id", name="uq_enrollment_user_exam"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    personal_deadline: Mapped[datetime.date | None] = mapped_column(Date)

    def __repr__(self) -> str:
        return f"<Enrollment(user={self.user_id}, exam={self.exam_id})>"


class ReadinessSnapshot(TimestampMixin, Base):
    """One readiness data point per user/exam/day. Written lazily on the first
    answer of the day; the analytics curve reads these rows instead of
    recomputing history. Gaps (inactive days) are simply absent."""

    __tablename__ = "readiness_snapshot"
    __table_args__ = (
        UniqueConstraint("user_id", "exam_id", "snapshot_date", name="uq_readiness_user_exam_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    snapshot_date: Mapped[datetime.date] = mapped_column(Date, index=True)
    predicted_pct: Mapped[float] = mapped_column(Float, default=0.0)

    def __repr__(self) -> str:
        return f"<ReadinessSnapshot(user={self.user_id}, exam={self.exam_id}, p={self.predicted_pct})>"


class Attempt(TimestampMixin, Base):
    """One graded answer. Append-only; mastery is derived from these.

    Anchored to the exam explicitly (not just via the question), so a user's
    work in an exam survives question re-mapping and per-exam queries are trivial.
    """

    __tablename__ = "attempt"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), index=True)
    chosen_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("option.id", ondelete="SET NULL")
    )
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    misconception_id: Mapped[int | None] = mapped_column(
        ForeignKey("misconception.id", ondelete="SET NULL")
    )
    response_ms: Mapped[int | None] = mapped_column(Integer)

    def __repr__(self) -> str:
        return f"<Attempt(user={self.user_id}, q={self.question_id}, correct={self.correct})>"


class ExplainAttempt(TimestampMixin, Base):
    """One explain-it-back submission, graded by the LLM against a rubric.

    Feeds XP/leaderboard ONLY — never mastery, readiness, or calibration.
    Append-only audit trail: every grade the model ever gave is inspectable.
    """

    __tablename__ = "explain_attempt"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column()
    accuracy: Mapped[int] = mapped_column(Integer, default=0)
    completeness: Mapped[int] = mapped_column(Integer, default=0)
    own_words: Mapped[int] = mapped_column(Integer, default=0)
    score_10: Mapped[int] = mapped_column(Integer, default=0)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    feedback: Mapped[str] = mapped_column(default="")
    graded: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<ExplainAttempt(user={self.user_id}, q={self.question_id}, score={self.score_10})>"

