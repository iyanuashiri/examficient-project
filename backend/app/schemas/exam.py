from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ExamCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    level: str | None = None
    country: str | None = None
    issuing_body: str | None = None
    description: str | None = None
    visibility: str = "private"
    pass_mark: float | None = None
    exam_date: date | None = None
    time_allowed_seconds: int | None = None
    question_count: int | None = None
    certification_id: int | None = None
    voice_enabled: bool = False


class ExamUpdate(BaseModel):
    name: str | None = None
    level: str | None = None
    country: str | None = None
    issuing_body: str | None = None
    description: str | None = None
    visibility: str | None = None
    status: str | None = None
    pass_mark: float | None = None
    exam_date: date | None = None
    time_allowed_seconds: int | None = None
    question_count: int | None = None
    certification_id: int | None = None
    voice_enabled: bool | None = None


class ExamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    level: str | None
    country: str | None
    issuing_body: str | None
    description: str | None
    status: str
    user_id: int | None
    visibility: str
    pass_mark: float | None
    exam_date: date | None
    time_allowed_seconds: int | None
    question_count: int | None
    certification_id: int | None
    voice_enabled: bool


class SyllabusCreate(BaseModel):
    version_label: str = Field(min_length=1, max_length=50)
    title: str | None = None
    description: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_current: bool = False


class SyllabusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_id: int
    version_label: str
    title: str | None
    description: str | None
    effective_from: date | None
    effective_to: date | None
    is_current: bool
    origin: str


class TopicCreate(BaseModel):
    code: str | None = None
    node_type: str | None = None
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    parent_id: int | None = None
    sort_order: int = 0
    weight: float | None = None
    depth: int = 0


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    syllabus_id: int
    parent_id: int | None
    code: str | None
    node_type: str | None
    name: str
    description: str | None
    sort_order: int
    weight: float | None
    depth: int
    origin: str


class MisconceptionCreate(BaseModel):
    code: str | None = None
    description: str = Field(min_length=1)


class MisconceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    code: str | None
    description: str
    origin: str


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    exam_id: int
    personal_deadline: date | None


class ExamFacts(BaseModel):
    enrolled_total: int
    syllabi_total: int
    topics_total: int
    questions_total: int


class CertificationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    issuing_body: str | None = None
    level: str | None = None
    country: str | None = None
    description: str | None = None


class CertificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    issuing_body: str | None
    level: str | None
    country: str | None
    description: str | None


class CertificationDetail(CertificationRead):
    exams: list[ExamRead] = Field(default_factory=list)


class OptionCreate(BaseModel):
    content: str = Field(min_length=1)
    is_correct: bool = False
    misconception_id: int | None = None
    explanation: str | None = None


class OptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    content: str
    is_correct: bool
    misconception_id: int | None
    explanation: str | None


class QuestionCreate(BaseModel):
    syllabus_id: int | None = None
    primary_topic_id: int | None = None
    topic_ids: list[int] = Field(default_factory=list)
    question_type: str = "single_choice"
    stem: str = Field(min_length=1)
    explanation: str | None = None
    options: list[OptionCreate] = Field(default_factory=list)


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_id: int
    syllabus_id: int | None
    primary_topic_id: int | None
    question_type: str
    stem: str
    explanation: str | None
    difficulty: float | None
    origin: str
    options: list[OptionRead] = Field(default_factory=list)
