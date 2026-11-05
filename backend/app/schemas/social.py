from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class FocusTopic(BaseModel):
    topic_id: int
    name: str
    points_share_pct: float


class PlanOut(BaseModel):
    exam_id: int
    predicted_score_pct: float
    pass_mark: float | None
    points_to_pass: float | None
    days_left: int | None
    questions_needed: int | None
    minutes_per_day: float | None
    feasible: bool | None
    note: str
    focus_topics: list[FocusTopic] = Field(default_factory=list)


class PaceOut(BaseModel):
    avg_response_ms: int | None
    allowance_ms: int | None
    verdict: str | None


class StatsOut(BaseModel):
    streak_days: int
    active_today: bool
    focus_minutes_today: float
    xp_week: int
    xp_total: int
    level: str
    questions_answered: int
    questions_correct: int
    questions_wrong: int
    accuracy_pct: float | None
    topics_practiced: int
    pace: PaceOut


class LeaderboardEntry(BaseModel):
    rank: int
    display_name: str
    xp: int
    questions: int


class LeaderboardOut(BaseModel):
    exam_id: int
    week_start: date
    entries: list[LeaderboardEntry] = Field(default_factory=list)
    me: LeaderboardEntry | None = None


class HistoryEntry(BaseModel):
    attempt_id: int
    question_id: int
    stem: str
    correct: bool
    answered_at: datetime | None


class RoomCreate(BaseModel):
    exam_id: int
    name: str | None = None
    starts_at: datetime
    ends_at: datetime
    is_official: bool = False
    is_official: bool = False


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_id: int
    exam_name: str = ""
    name: str | None
    starts_at: datetime
    ends_at: datetime
    is_official: bool = False


class RoomQuestionStat(BaseModel):
    question_id: int
    stem: str
    attempts: int
    correct_rate: float


class RoomStats(BaseModel):
    room: RoomRead
    status: str  # upcoming | live | ended
    participants: int
    answers: int
    accuracy_pct: float | None
    hardest_questions: list[RoomQuestionStat] = Field(default_factory=list)
    top_trap: str | None = None


class RoomLeaderboardOut(BaseModel):
    room_id: int
    entries: list[LeaderboardEntry] = Field(default_factory=list)
    me: LeaderboardEntry | None = None


class CohortOut(BaseModel):
    exam_id: int
    days_left: int | None
    learners_active_week: int
    band_counts: dict[str, int] = Field(default_factory=dict)
    my_band: str | None = None
    trap_of_day: RoomQuestionStat | None = None


class AnalyticsWeek(BaseModel):
    week_start: date
    xp: int
    answered: int
    correct: int
    accuracy: float | None


class AnalyticsTopic(BaseModel):
    topic_id: int
    code: str | None
    name: str
    weight: float
    mastery_p: float
    theta: float
    attempts: int
    correct: int
    accuracy: float | None


class MisconceptionStatus(BaseModel):
    id: int
    code: str | None
    description: str
    topic_name: str
    triggered_count: int
    last_triggered: datetime | None
    status: str  # open | quiet | never
    correct_since: int


class AnalyticsRoom(BaseModel):
    room_id: int
    name: str | None
    status: str
    rank: int | None
    participants: int
    user_xp: int
    user_accuracy: float


class AnalyticsPoint(BaseModel):
    date: date
    predicted_pct: float


class AnalyticsOut(BaseModel):
    exam_id: int
    weeks: list[AnalyticsWeek] = Field(default_factory=list)
    readiness_curve: list[AnalyticsPoint] = Field(default_factory=list)
    topics: list[AnalyticsTopic] = Field(default_factory=list)
    misconceptions: list[MisconceptionStatus] = Field(default_factory=list)
    rooms: list[AnalyticsRoom] = Field(default_factory=list)
