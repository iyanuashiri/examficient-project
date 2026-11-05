"""Daily + weekly explain challenges.

Each challenge is one question to explain. Daily picks are engine-chosen
(weakest topics first, deterministic per day so everyone shares one set);
weekly picks are the user's hardest questions of the week and stay locked
until the week's last day. Completion and grading reuse explain_attempt.
"""

from __future__ import annotations

import datetime

from app.crud.exam import ContentError
from app.models.exam import Question
from app.models.practice import Attempt, ExplainAttempt

DAILY_N = 3
WEEKLY_N = 5


def _today_utc() -> datetime.date:
    return datetime.datetime.now(datetime.timezone.utc).date()


def _week_start(today: datetime.date) -> datetime.date:
    return today - datetime.timedelta(days=today.weekday())  # Monday


def _as_utc(dt):
    if dt is not None and getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def challenges(session, user, exam_id: int) -> dict:
    from app.crud.practice import readiness
    from app.models.exam import Exam
    from app.schemas.explain import ChallengeBoardOut, ChallengeItem

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    today = _today_utc()
    week_start = _week_start(today)

    weak_ids = [t.topic_id for t in readiness(session, user, exam.id).weak_topics]

    atts = (
        session.query(Attempt, Question)
        .join(Question, Question.id == Attempt.question_id)
        .filter(Attempt.user_id == user.id, Question.exam_id == exam.id)
        .order_by(Attempt.id)
        .all()
    )
    seen: dict[int, str] = {}
    weak_first: list[int] = []
    rest: list[int] = []
    for a, q in atts:
        if q.id in seen:
            continue
        seen[q.id] = q.stem
        (weak_first if q.primary_topic_id in weak_ids else rest).append(q.id)
    candidates = weak_first + rest
    if not candidates:
        bank = session.query(Question).filter(Question.exam_id == exam.id).order_by(Question.id).all()
        for q in bank:
            seen[q.id] = q.stem
        candidates = [q.id for q in bank]

    # Deterministic daily rotation: same set for everyone, changes at midnight.
    daily_ids: list[int] = []
    if candidates:
        start = (user.id + exam.id + today.toordinal()) % len(candidates)
        for i in range(min(DAILY_N, len(candidates))):
            daily_ids.append(candidates[(start + i) % len(candidates)])

    # Weekly: user's hardest questions of this week (lowest own correct rate).
    per_q: dict[int, list[bool]] = {}
    for a, q in atts:
        ts = _as_utc(a.created_at)
        if ts is None or ts.date() < week_start:
            continue
        per_q.setdefault(q.id, []).append(bool(a.correct))
    ranked = sorted(per_q.items(), key=lambda kv: (sum(kv[1]) / len(kv[1]), kv[0]))
    weekly_ids = [qid for qid, _ in ranked[:WEEKLY_N]]

    done: dict[int, int] = {}
    for r in session.query(ExplainAttempt).filter(
        ExplainAttempt.user_id == user.id, ExplainAttempt.exam_id == exam.id,
        ExplainAttempt.graded.is_(True),
    ).all():
        if r.question_id not in done or r.score_10 > done[r.question_id]:
            done[r.question_id] = r.score_10

    def item(qid: int, kind: str) -> ChallengeItem:
        return ChallengeItem(
            question_id=qid, stem=seen.get(qid, ""), kind=kind,
            done=qid in done, best_score=done.get(qid),
        )

    unlock_day = week_start + datetime.timedelta(days=6)  # Sunday
    return ChallengeBoardOut(
        daily=[item(qid, "daily") for qid in daily_ids],
        weekly=[item(qid, "weekly") for qid in weekly_ids],
        weekly_unlocked=today >= unlock_day,
        unlocks_at=unlock_day,
    )
