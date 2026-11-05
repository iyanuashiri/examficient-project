from __future__ import annotations

import datetime
import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.certification import Certification

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExamStatus(str, enum.Enum):
    """Lifecycle of an exam."""

    draft = "draft"
    active = "active"
    archived = "archived"


class Origin(str, enum.Enum):
    """Where a record came from."""

    manual = "manual"  # typed by a human
    extracted = "extracted"  # proposed by an ingestion run


class Visibility(str, enum.Enum):
    """Who can see a content root. Topics/questions inherit from their exam."""

    private = "private"  # user uploads stay private to user_id
    public = "public"  # featured library (admin-published)


class QuestionType(str, enum.Enum):
    """Question shapes the engine can grade.

    Objective tests first, so ``single_choice`` is the default. ``multi_select``
    is listed now because it changes how the answer key is read: several options
    are correct, so nothing may assume exactly one.
    """

    single_choice = "single_choice"
    multi_select = "multi_select"
    true_false = "true_false"
    numeric = "numeric"


question_topics = Table(
    "question_topic",
    Base.metadata,
    Column("question_id", ForeignKey("question.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", ForeignKey("topic.id", ondelete="CASCADE"), primary_key=True),
)

topic_prerequisites = Table(
    "topic_prerequisite",
    Base.metadata,
    Column("topic_id", ForeignKey("topic.id", ondelete="CASCADE"), primary_key=True),
    Column("prerequisite_id", ForeignKey("topic.id", ondelete="CASCADE"), primary_key=True),
)


class Exam(TimestampMixin, Base):
    """A certification or school-leaving exam a learner prepares for.

    The stable identity ("WAEC Biology", "JAMB Chemistry", "SAA-C03"). The
    version lives on the syllabus, not here.
    """

    __tablename__ = "exam"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    level: Mapped[str | None] = mapped_column(String(50))  # WASSCE, A-Level, Associate
    country: Mapped[str | None] = mapped_column(String(50))
    issuing_body: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    # Pass mark on the same 0-100 scale as readiness predicted_score_pct.
    pass_mark: Mapped[float | None] = mapped_column(Float)
    # Fixed-date exams: the day everyone sits. Drives countdowns + daily plans.
    exam_date: Mapped[datetime.date | None] = mapped_column(Date)
    # Pace fitness: allowance per question, derived from official timing when known.
    time_allowed_seconds: Mapped[int | None] = mapped_column(Integer)
    question_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus, native_enum=False, length=16), default=ExamStatus.draft, index=True
    )
    # Featured = admin user + visibility public + status active.
    # User uploads stay private to user_id. Children (syllabi/topics/
    # questions) inherit through exam_id, so no per-row user here.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # The credential this exam ladders up to (WASSCE, JAMB UTME, a CFA level
    # track...). NULL = standalone exam. One certification → many exams.
    certification_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification.id", ondelete="SET NULL"), index=True, default=None
    )
    visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility, native_enum=False, length=16),
        default=Visibility.private,
        index=True,
    )
    # Voice input (mic → Meta transcription → same grading path) is a property
    # of the exam, not the user: listening/speaking exams (SAT Reading/Writing,
    # TOEFL, IELTS) get it; written exams (JAMB, WAEC) show it disabled.
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    syllabi: Mapped[list[Syllabus]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )
    questions: Mapped[list[Question]] = relationship(back_populates="exam")
    certification: Mapped[Certification | None] = relationship(
        back_populates="exams", foreign_keys=[certification_id]
    )

    def __repr__(self) -> str:
        return f"<Exam(code={self.code!r})>"


class Syllabus(TimestampMixin, Base):
    """A version of an exam's syllabus, and the root of one topic tree.

    A revision is a new row with a new ``version_label``, never an edit to an
    existing one: an answer recorded against the 2025 syllabus must stay
    comparable to what was in force when it was given. ``is_current`` marks
    which version new learners are placed on.
    """

    __tablename__ = "syllabus"
    __table_args__ = (
        UniqueConstraint("exam_id", "version_label", name="uq_syllabus_exam_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    version_label: Mapped[str] = mapped_column(String(50))  # "2026", "v2", "2024/2025"
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    effective_from: Mapped[datetime.date | None] = mapped_column(Date)
    effective_to: Mapped[datetime.date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    origin: Mapped[Origin] = mapped_column(
        Enum(Origin, native_enum=False, length=16), default=Origin.manual
    )

    exam: Mapped[Exam] = relationship(back_populates="syllabi")
    # Every topic in the version, flat - roots and descendants alike. One query
    # for the whole tree; nest it in Python via ``parent_id`` rather than
    # walking ``Topic.children``, which would be a query per level.
    topics: Mapped[list[Topic]] = relationship(
        back_populates="syllabus",
        cascade="all, delete-orphan",
        order_by="Topic.sort_order",
    )

    def __repr__(self) -> str:
        return f"<Syllabus(exam_id={self.exam_id}, version={self.version_label!r})>"


class Topic(TimestampMixin, Base):
    """One node in a syllabus tree: an objective, unit or topic at any depth.

    A single self-referencing table instead of separate topic and subtopic
    tables, because real syllabi mix two and three levels (unit, topic,
    learning objective) and a fixed pair of tables cannot express that.

    Two fields carry the stable identity and the display identity separately:
    ``code`` is what mastery rows and links point at ("GEN.2.1"), so ``name``
    can be reworded without breaking anything. ``depth`` is stored for
    convenience and maintained by the application - enforcing it in DDL would
    need a recursive check, which SQLite and Postgres do not share.
    """

    __tablename__ = "topic"
    __table_args__ = (
        UniqueConstraint("syllabus_id", "code", name="uq_topic_syllabus_code"),
        CheckConstraint("depth >= 0", name="ck_topic_depth"),
        CheckConstraint("weight IS NULL OR weight >= 0", name="ck_topic_weight"),
        Index("ix_topic_syllabus_parent", "syllabus_id", "parent_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    syllabus_id: Mapped[int] = mapped_column(ForeignKey("syllabus.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("topic.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str | None] = mapped_column(String(50))
    # The label the syllabus itself uses for this level ("Unit", "Section",
    # "Objective"), for display only.
    node_type: Mapped[str | None] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    # Order among siblings, as the syllabus presents them.
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # Share of the exam, where the syllabus states it. Nullable because most
    # school syllabi do not.
    weight: Mapped[float | None] = mapped_column(Float)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    origin: Mapped[Origin] = mapped_column(
        Enum(Origin, native_enum=False, length=16), default=Origin.manual
    )

    syllabus: Mapped[Syllabus] = relationship(back_populates="topics")
    parent: Mapped[Topic | None] = relationship(back_populates="children", remote_side="Topic.id")
    children: Mapped[list[Topic]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", order_by="Topic.sort_order"
    )
    # A learner must normally cover these first. Directional: A requires B does
    # not imply B requires A.
    prerequisites: Mapped[list[Topic]] = relationship(
        secondary=topic_prerequisites,
        primaryjoin="Topic.id == topic_prerequisite.c.topic_id",
        secondaryjoin="Topic.id == topic_prerequisite.c.prerequisite_id",
    )
    questions: Mapped[list[Question]] = relationship(
        secondary=question_topics, back_populates="topics"
    )
    misconceptions: Mapped[list[Misconception]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, code={self.code!r})>"


class Question(TimestampMixin, Base):
    """One exam question.

    ``stem`` never contains the options. Keeping them apart is what lets the
    options be shuffled or re-lettered for a retry without the question text
    going stale.
    """

    __tablename__ = "question"
    __table_args__ = (
        CheckConstraint("stem <> ''", name="ck_question_stem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id", ondelete="CASCADE"), index=True)
    # Nullable so a past paper can be loaded before the syllabus it belongs to
    # is settled; it is backfilled when the question is mapped.
    syllabus_id: Mapped[int | None] = mapped_column(
        ForeignKey("syllabus.id", ondelete="SET NULL"), index=True
    )
    # The topic this question is scored against. Separate from the many-to-many
    # below: a question can touch three topics, but only one of them owns the
    # miss when the learner gets it wrong.
    primary_topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topic.id", ondelete="SET NULL"), index=True
    )

    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, native_enum=False, length=20),
        default=QuestionType.single_choice,
        index=True,
    )
    stem: Mapped[str] = mapped_column(Text)
    # passage: Mapped[str | None] = mapped_column(Text)  # shared comprehension text
    # stem_media_url: Mapped[str | None] = mapped_column(String(512))  # diagram, table, chart
    explanation: Mapped[str | None] = mapped_column(Text)  # authored answer rationale
    # IRT difficulty (b): negative = easy, positive = hard. NULL until enough
    # learners have answered it to estimate; treated as 0.0 meanwhile.
    difficulty: Mapped[float | None] = mapped_column(Float)
    # source_year: Mapped[int | None]  # year of the past paper, when it has one
    origin: Mapped[Origin] = mapped_column(
        Enum(Origin, native_enum=False, length=16), default=Origin.manual, index=True
    )

    exam: Mapped[Exam] = relationship(back_populates="questions")
    syllabus: Mapped[Syllabus | None] = relationship(foreign_keys=[syllabus_id])
    primary_topic: Mapped[Topic | None] = relationship(foreign_keys=[primary_topic_id])
    options: Mapped[list[Option]] = relationship(
        # Ordered by id so the display order is deterministic; swap to
        # ``Option.sort_order`` when options become re-orderable.
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Option.id",
    )
    topics: Mapped[list[Topic]] = relationship(
        secondary=question_topics, back_populates="questions"
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, type={self.question_type})>"


class Option(TimestampMixin, Base):
    """One answer option.

    No label column: A/B/C/D letters are presentation, assigned by the client
    after shuffling. The database stores order-insensitive content plus the
    correctness flag; display order is the insertion order (``Option.id``).
    Grading and misconception diagnosis key off ``Option.id``, never a letter,
    so shuffling can never corrupt an answer or a diagnosis.

    No database constraint forces "exactly one correct option", because a
    ``multi_select`` question legitimately has several. The single-choice rule
    is enforced when the question is written and checked by the ingestion agent.
    """

    __tablename__ = "option"
    __table_args__ = (
        Index("ix_option_question_correct", "question_id", "is_correct"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    # sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # The wrong belief this distractor represents, when it is a known one. This
    # is what turns a miss into a diagnosis: "you chose B" becomes "you treated
    # a carrier as affected".
    misconception_id: Mapped[int | None] = mapped_column(
        ForeignKey("misconception.id", ondelete="SET NULL")
    )
    # Why this option is right/wrong. Shown after answering; never served
    # with the question (PracticeQuestion omits it).
    explanation: Mapped[str | None] = mapped_column(Text)

    question: Mapped[Question] = relationship(back_populates="options")
    misconception: Mapped[Misconception | None] = relationship()

    def __repr__(self) -> str:
        return f"<Option(id={self.id}, correct={self.is_correct})>"


class Misconception(TimestampMixin, Base):
    """A wrong belief about a topic, behind one or more distractors.

    Scoped to the topic rather than the question, because the same
    misunderstanding shows up across many questions. Several options on
    different questions can point at one row, which is what lets the learner
    model report "you keep making this mistake" instead of "you missed three
    questions".
    """

    __tablename__ = "misconception"
    __table_args__ = (
        UniqueConstraint("topic_id", "code", name="uq_misconception_topic_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topic.id", ondelete="CASCADE"), index=True)
    code: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    origin: Mapped[Origin] = mapped_column(
        Enum(Origin, native_enum=False, length=16), default=Origin.manual
    )

    topic: Mapped[Topic] = relationship(back_populates="misconceptions")

    def __repr__(self) -> str:
        return f"<Misconception(code={self.code!r})>"