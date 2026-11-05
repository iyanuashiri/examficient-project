from pydantic import BaseModel, ConfigDict, Field

from app.schemas.exam import OptionRead


class AnswerIn(BaseModel):
    question_id: int
    chosen_option_id: int | None = None
    response_ms: int | None = None


class MasterySnapshot(BaseModel):
    topic_id: int
    theta: float
    mastery_p: float


class AnswerOut(BaseModel):
    attempt_id: int
    correct: bool
    correct_option_id: int | None
    explanation: str | None
    misconception: str | None
    mastery: MasterySnapshot | None
    options: list[OptionRead] = Field(default_factory=list)
    retry_queued: bool = False


class PracticeOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str


class PracticeQuestion(BaseModel):
    """Question as served for practice. Never includes the key."""

    id: int
    exam_id: int
    syllabus_id: int | None
    primary_topic_id: int | None
    question_type: str
    stem: str
    options: list[PracticeOption] = Field(default_factory=list)


class WeakTopic(BaseModel):
    topic_id: int
    code: str | None
    name: str
    mastery_p: float


class ReadinessOut(BaseModel):
    exam_id: int
    predicted_score_pct: float
    pass_mark: float | None = None
    points_to_pass: float | None = None
    on_track: bool | None = None
    topics_total: int
    topics_attempted: int
    weak_topics: list[WeakTopic] = Field(default_factory=list)
