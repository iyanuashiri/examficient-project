from typing import Any

from pydantic import BaseModel, Field


class NarrateIn(BaseModel):
    kind: str = Field(pattern="^(plan_intro|replan|nudge|readiness_summary)$")
    exam_id: int
    # Optional extras the caller already knows (e.g. nudge moment, missed_days).
    context: dict[str, Any] = Field(default_factory=dict)


class NarrateOut(BaseModel):
    text: str
    source: str  # "meta" | "template"
    model: str | None = None
