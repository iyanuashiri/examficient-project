"""Model package.

Every model must be imported here so that ``Base.metadata`` knows its table.
Alembic autogenerate and ``create_all`` only see what this module has pulled in.
"""

from app.models.base import Base, TimestampMixin
from app.models.document import Document
from app.models.exam import (
    Exam,
    ExamStatus,
    Misconception,
    Option,
    Origin,
    Question,
    QuestionType,
    Syllabus,
    Topic,
    Visibility,
    question_topics,
    topic_prerequisites,
)
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "TimestampMixin",
    "Document",
    "Exam",
    "ExamStatus",
    "Misconception",
    "Option",
    "Origin",
    "Question",
    "QuestionType",
    "Syllabus",
    "Topic",
    "User",
    "UserRole",
    "Visibility",
    "question_topics",
    "topic_prerequisites",
]