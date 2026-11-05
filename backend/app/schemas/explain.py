import datetime

from pydantic import BaseModel, Field


class ExplainIn(BaseModel):
    question_id: int
    text: str = Field(min_length=1, max_length=2000)


class ExplainOut(BaseModel):
    id: int
    question_id: int
    graded: bool
    accuracy: int
    completeness: int
    own_words: int
    score_10: int
    xp_awarded: int
    capped: bool
    feedback: str
    note: str | None = None


class ExplainHistoryEntry(BaseModel):
    id: int
    question_id: int
    stem: str
    score_10: int
    xp: int
    feedback: str
    created_at: datetime.datetime | None = None


class ChallengeItem(BaseModel):
    question_id: int
    stem: str
    kind: str  # daily | weekly
    done: bool = False
    best_score: int | None = None


class ChallengeBoardOut(BaseModel):
    daily: list[ChallengeItem]
    weekly: list[ChallengeItem]
    weekly_unlocked: bool
    unlocks_at: datetime.date


class TranscribeOut(BaseModel):
    transcript: str
