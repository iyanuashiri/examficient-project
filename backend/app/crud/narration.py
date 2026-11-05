"""LLM narration: a Meta model writes words about numbers we computed.

Every kind has a deterministic template fallback, so the feature works with
no API key, offline, or on any Meta API failure. The model is never asked to
compute, grade, or rank.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app import llm
from app.crud.exam import ContentError
from app.crud.social import analytics, study_plan, user_stats
from app.models.exam import Question
from app.models.practice import Attempt
from app.prompts import narration as prompts


def _plan_facts(session, user, exam_id: int, context: dict) -> tuple[dict, str]:
    plan = study_plan(session, user, exam_id)
    facts = {
        "predicted": plan.predicted_score_pct,
        "pass_mark": plan.pass_mark,
        "gap": plan.points_to_pass,
        "days_left": plan.days_left,
        "minutes_per_day": plan.minutes_per_day,
        "feasible": plan.feasible,
        "focus": [{"name": t.name, "share_pct": t.points_share_pct} for t in plan.focus_topics],
        "missed_days": context.get("missed_days"),
    }
    return facts, plan.note


def _readiness_facts(session, user, exam_id: int) -> tuple[dict, str]:
    from app.crud.practice import readiness

    r = readiness(session, user, exam_id)
    facts = {
        "predicted": r.predicted_score_pct,
        "pass_mark": r.pass_mark,
        "weak": [{"name": t.name, "mastery_pct": round(t.mastery_p * 100, 1)} for t in r.weak_topics[:3]],
    }
    template = f"Predicted {r.predicted_score_pct}%"
    if r.pass_mark is not None:
        template += f" against a {r.pass_mark}% pass mark"
    template += "."
    return facts, template


def _nudge_facts(session: Session, user, exam_id: int, context: dict) -> tuple[str, dict, str]:
    """Returns (moment, facts, template_fallback)."""
    moment = str(context.get("moment", ""))
    if moment == "streak_at_risk":
        st = user_stats(session, user, exam_id)
        today = datetime.datetime.now(datetime.timezone.utc).date()
        n = sum(
            1 for a in session.query(Attempt).join(Question, Question.id == Attempt.question_id).filter(
                Attempt.user_id == user.id, Question.exam_id == exam_id).all()
            if _as_utc(a.created_at) and _utc(a.created_at).date() == today
        )
        need = max(0, 5 - n)
        facts = {"streak_days": st.streak_days, "answered_today": n, "needed_today": need}
        template = (f"Answer {need} more today to keep your {st.streak_days}-day streak alive."
                    if need > 0 else f"Streak safe at {st.streak_days} days — nice work.")
        return moment, facts, template
    if moment == "trap_fixed":
        traps = analytics(session, user, exam_id).get("misconceptions", [])
        top = max(traps, key=lambda m: (m.get("triggered_count") or 0, m.get("id", 0)), default=None) if traps else None
        name = (top or {}).get("description", "that trap")
        return moment, {"trap": name}, f"You stopped falling for {name} — that trap is closed."
    if moment == "milestone_reached":
        facts, _ = _readiness_facts(session, user, exam_id)
        template = (f"You just crossed {facts['predicted']}% — above the {facts['pass_mark']}% pass mark."
                    if facts["pass_mark"] else f"You just hit {facts['predicted']}% predicted.")
        return moment, facts, template
    raise ContentError("Unknown nudge moment (expected streak_at_risk | trap_fixed | milestone_reached)")


def _as_utc(dt):
    if dt is not None and getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def narrate(session, user, kind: str, exam_id: int, context: dict) -> dict:
    from app.schemas.narration import NarrateOut

    if kind == "plan_intro":
        facts, template = _plan_facts(session, user, exam_id, context)
        messages = prompts.plan_intro(facts)
    elif kind == "replan":
        facts, template = _plan_facts(session, user, exam_id, context)
        facts["triage"] = facts.get("feasible") is False
        messages = prompts.replan(facts)
    elif kind == "nudge":
        moment, facts, template = _nudge_facts(session, user, exam_id, context)
        messages = prompts.nudge(moment, facts)
    elif kind == "readiness_summary":
        facts, template = _readiness_facts(session, user, exam_id)
        messages = prompts.readiness_summary(facts)
    else:
        raise ContentError("Unknown narration kind (expected plan_intro | replan | nudge | readiness_summary)")

    try:
        text = llm.complete(messages)
        return NarrateOut(text=text, source="meta", model=llm.DEFAULT_MODEL)
    except Exception:
        return NarrateOut(text=template, source="template", model=None)
