"""Explain-it-back challenges: the user explains, the LLM grades, XP scales.

Hard rules (see docs/product-thinking.md):
- Grading feeds XP/leaderboard ONLY. Never mastery, readiness, or calibration.
- Zero XP unless a valid grade was parsed from the model.
- Deterministic anti-gaming gates run BEFORE any LLM call.
"""

from __future__ import annotations

import datetime
import difflib
import json
import re

from app import llm
from app.crud.exam import ContentError, get_question
from app.models.practice import ExplainAttempt
from app.prompts import explain as prompts

MIN_CHARS = 40
MAX_SIMILARITY = 0.8
EXPLAIN_XP_CAP_PER_DAY = 30


def _today_start_naive() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(
        tzinfo=None, hour=0, minute=0, second=0, microsecond=0
    )


def _as_utc(dt):
    if dt is not None and getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _clamp4(v) -> int:
    try:
        return max(0, min(4, int(v)))
    except (TypeError, ValueError):
        raise ValueError(f"bad sub-score: {v!r}")


def _parse_grade(raw: str) -> tuple[int, int, int, str]:
    """Extract {accuracy, completeness, own_words, feedback} or raise."""
    data = None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            data = parsed
    except (json.JSONDecodeError, TypeError):
        data = None
    if data is None:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict):
                    data = parsed
            except (json.JSONDecodeError, TypeError):
                data = None
    if not isinstance(data, dict):
        raise ValueError("no JSON object in model output")
    for key in ("accuracy", "completeness", "own_words"):
        if key not in data:
            raise ValueError(f"missing key: {key}")
    feedback = str(data.get("feedback") or "")[:500]
    return _clamp4(data["accuracy"]), _clamp4(data["completeness"]), _clamp4(data["own_words"]), feedback


def explain_xp_today(session, user_id: int, exam_id: int) -> int:
    rows = (
        session.query(ExplainAttempt)
        .filter(
            ExplainAttempt.user_id == user_id,
            ExplainAttempt.exam_id == exam_id,
            ExplainAttempt.created_at >= _today_start_naive(),
        )
        .all()
    )
    return sum(r.xp for r in rows)


def explain_xp_map(session, exam_id: int, user_ids: list[int], since_date=None) -> dict[int, int]:
    """XP from explanations per user, optionally restricted to date >= since_date."""
    if not user_ids:
        return {}
    rows = (
        session.query(ExplainAttempt)
        .filter(ExplainAttempt.exam_id == exam_id, ExplainAttempt.user_id.in_(user_ids))
        .all()
    )
    out: dict[int, int] = {}
    for r in rows:
        if since_date is not None:
            ts = _as_utc(r.created_at)
            if ts is None or ts.date() < since_date:
                continue
        out[r.user_id] = out.get(r.user_id, 0) + (r.xp or 0)
    return out


def explain_uids_since(session, exam_id: int, since_date=None) -> list[int]:
    """User ids with explanation XP on the exam, optionally since a date."""
    rows = (
        session.query(ExplainAttempt)
        .filter(ExplainAttempt.exam_id == exam_id)
        .all()
    )
    out = set()
    for r in rows:
        if since_date is not None:
            ts = _as_utc(r.created_at)
            if ts is None or ts.date() < since_date:
                continue
        if r.xp:
            out.add(r.user_id)
    return sorted(out)


def grade_explanation(session, user, question_id: int, text: str) -> dict:
    from app.schemas.explain import ExplainOut

    question = get_question(session, question_id)
    if question is None:
        raise ContentError("Question not found")
    clean = (text or "").strip()
    if len(clean) < MIN_CHARS:
        raise ContentError(f"Explain in at least {MIN_CHARS} characters — one real sentence or more.")
    correct_text = " ".join(o.content for o in question.options if o.is_correct)
    if correct_text and difflib.SequenceMatcher(None, clean.lower(), correct_text.lower()).ratio() >= MAX_SIMILARITY:
        raise ContentError("Too close to the answer text — explain it in your own words.")

    remaining = EXPLAIN_XP_CAP_PER_DAY - explain_xp_today(session, user.id, question.exam_id)
    messages = prompts.grade(question.stem, correct_text or "(see options)", clean)
    try:
        raw = llm.complete(messages, max_tokens=400)
        accuracy, completeness, own_words, feedback = _parse_grade(raw)
        graded = True
    except Exception:
        row = ExplainAttempt(
            user_id=user.id, exam_id=question.exam_id, question_id=question.id,
            text=clean, graded=False,
        )
        session.add(row)
        session.commit()
        return ExplainOut(
            id=row.id, question_id=question.id, graded=False,
            accuracy=0, completeness=0, own_words=0, score_10=0,
            xp_awarded=0, capped=False, feedback="",
            note="Grading is unavailable right now — no XP awarded. Try again in a bit.",
        )

    score_10 = round((accuracy + completeness + own_words) / 12 * 10)
    xp_awarded = min(score_10, max(0, remaining))
    capped = remaining <= 0
    row = ExplainAttempt(
        user_id=user.id, exam_id=question.exam_id, question_id=question.id,
        text=clean, accuracy=accuracy, completeness=completeness, own_words=own_words,
        score_10=score_10, xp=xp_awarded, feedback=feedback, graded=True,
    )
    session.add(row)
    session.commit()
    return ExplainOut(
        id=row.id, question_id=question.id, graded=True,
        accuracy=accuracy, completeness=completeness, own_words=own_words,
        score_10=score_10, xp_awarded=xp_awarded, capped=capped, feedback=feedback,
        note=("Daily explain bonus reached — grade kept, no XP this time." if capped else None),
    )


def explain_history(session, user, exam_id: int, limit: int = 20) -> list[dict]:
    from app.models.exam import Question
    from app.schemas.explain import ExplainHistoryEntry

    rows = (
        session.query(ExplainAttempt, Question.stem)
        .join(Question, Question.id == ExplainAttempt.question_id)
        .filter(ExplainAttempt.user_id == user.id, ExplainAttempt.exam_id == exam_id)
        .order_by(ExplainAttempt.id.desc())
        .limit(limit)
        .all()
    )
    return [
        ExplainHistoryEntry(
            id=r.id, question_id=r.question_id, stem=stem,
            score_10=r.score_10, xp=r.xp, feedback=r.feedback,
            created_at=_as_utc(r.created_at),
        )
        for r, stem in rows
    ]
