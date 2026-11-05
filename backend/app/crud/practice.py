import datetime
import math
import random

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.exam import ContentError
from app.models.exam import Exam, Option, Question, Syllabus, Topic
from app.models.practice import Attempt, Mastery
from app.models.user import User
from app.schemas.exam import OptionRead
from app.schemas.practice import AnswerOut, MasterySnapshot, PracticeOption, PracticeQuestion


# Tuning constants. Deterministic and documented; calibrate later from data.
K_THETA = 0.25  # Elo step per answer
P_LEARN = 0.2  # mastery_p gain share on a correct answer
P_FORGET_HIT = 0.7  # mastery_p retained after a miss
PRIOR_P = 0.5  # unseen topic prior for selection
B_DEFAULT = 0.0  # fallback difficulty before a question is calibrated
B_MIN, B_MAX = -3.0, 3.0  # clamp for calibrated difficulty
MIN_ATTEMPTS_FOR_B = 5  # answers needed before trusting a difficulty estimate
BAND_LO, BAND_HI = 0.6, 0.8  # target predicted-success band
HISTORY_EXCLUDE = 20  # recent attempts excluded from next-question picks
RETRY_LOOKBACK = 10  # recent wrong answers scanned for retest candidates

# XP constants (locked). Points are non-increasing in response time: waiting
# can only ever reduce the speed bonus, never increase it.
XP_BASE_CORRECT = 10
XP_CONSOLATION = 2  # wrong answers still pay effort, never mastery
XP_SPEED_PAR_MS = 60_000  # at/above this pace: no speed bonus
XP_SPEED_MAX_BONUS = 0.5  # instant correct answer pays up to +50%
XP_DIFFICULTY_LO, XP_DIFFICULTY_HI = 0.5, 2.0  # easy pays half, hard pays double
MIN_ACTIVE_DAY_ANSWERS = 5  # answers for a day to count toward streaks
FOCUS_MS_CAP = 180_000  # per-answer cap for focus minutes (anti-idle)
GUESS_MS = 5_000  # wrong faster than this is treated as a guess, not a gap
RETRY_LOOKBACK = 10  # recent wrong answers scanned for retest candidates


def _recalibrate_difficulty(session: Session, question: Question) -> float:
    """Empirical IRT b from the question's own answer history.

    b = -logit(smoothed correct rate), clamped. Easy questions (high
    correct rate) get negative b; hard ones positive. Needs a few answers
    before it means anything — hence MIN_ATTEMPTS_FOR_B.
    """
    total = session.query(Attempt).filter(Attempt.question_id == question.id).count()
    if total < MIN_ATTEMPTS_FOR_B:
        return question.difficulty if question.difficulty is not None else B_DEFAULT
    correct_n = (
        session.query(Attempt)
        .filter(Attempt.question_id == question.id, Attempt.correct.is_(True))
        .count()
    )
    p = (correct_n + 1) / (total + 2)  # Laplace smoothing keeps logit finite
    b = -math.log(p / (1.0 - p))
    question.difficulty = max(B_MIN, min(B_MAX, b))
    return question.difficulty


def predicted(theta: float, b: float = B_DEFAULT) -> float:
    return 1.0 / (1.0 + math.exp(-(theta - b)))


def xp_for_attempt(correct: bool, difficulty: float | None, response_ms: int | None) -> int:
    """XP for one answer. Non-increasing in response time by construction."""
    if not correct:
        return XP_CONSOLATION
    b = difficulty if difficulty is not None else B_DEFAULT
    dmult = min(XP_DIFFICULTY_HI, max(XP_DIFFICULTY_LO, 1.0 + max(-3.0, min(3.0, b)) / 3.0))
    smult = 1.0
    if response_ms is not None and response_ms < XP_SPEED_PAR_MS:
        smult = 1.0 + XP_SPEED_MAX_BONUS * max(0.0, 1.0 - response_ms / XP_SPEED_PAR_MS)
    return max(1, round(XP_BASE_CORRECT * dmult * smult))


def focus_minutes(response_ms_values: list[int | None]) -> float:
    """Engaged minutes: capped per-answer response times. Idling pays nothing."""
    return round(sum(min(ms, FOCUS_MS_CAP) for ms in response_ms_values if ms) / 60000.0, 1)


def schedule_next_review(correct: bool, attempts: int) -> datetime.datetime:
    """When this topic should resurface. Correct stretches the interval
    (capped at 30 days); a miss pulls it back to tomorrow."""
    now = datetime.datetime.now(datetime.timezone.utc)
    if correct:
        return now + datetime.timedelta(days=min(30, max(1, attempts)))
    return now + datetime.timedelta(days=1)


def _as_utc(dt: datetime.datetime | None) -> datetime.datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)  # SQLite returns naive
    return dt


def _mastery_map(session: Session, user: User, topic_ids: list[int]) -> dict[int, Mastery]:
    if not topic_ids:
        return {}
    rows = session.query(Mastery).filter(Mastery.user_id == user.id, Mastery.topic_id.in_(topic_ids)).all()
    return {r.topic_id: r for r in rows}


def _current_syllabus(session: Session, exam: Exam) -> Syllabus | None:
    rows = session.query(Syllabus).filter(Syllabus.exam_id == exam.id).all()
    for row in rows:
        if row.is_current:
            return row
    return rows[0] if rows else None


def record_answer(
    session: Session, user: User, question_id: int, chosen_option_id: int | None, response_ms: int | None
) -> AnswerOut:
    question = (
        session.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.id == question_id)
        .first()
    )
    if question is None:
        raise ContentError("Question not found")
    exam = session.get(Exam, question.exam_id)
    if exam is None:
        raise ContentError("Question not found")

    chosen = next((o for o in question.options if o.id == chosen_option_id), None)
    if chosen_option_id is not None and chosen is None:
        raise ContentError("chosen_option_id does not belong to this question")
    if question.options and chosen is None:
        raise ContentError("chosen_option_id is required for this question")

    correct = bool(chosen.is_correct) if chosen else False
    misconception = chosen.misconception if chosen and not correct else None

    attempt = Attempt(
        user_id=user.id,
        exam_id=exam.id,
        question_id=question.id,
        chosen_option_id=chosen_option_id,
        correct=correct,
        misconception_id=misconception.id if misconception else None,
        response_ms=response_ms,
    )
    session.add(attempt)
    session.flush()  # attempt visible to the difficulty recount below
    # First touch joins the exam: answering = preparing.
    from app.crud.exam import enroll_user

    enroll_user(session, user, exam)

    b = _recalibrate_difficulty(session, question)

    snapshot: MasterySnapshot | None = None
    if question.primary_topic_id is not None:
        mastery = (
            session.query(Mastery)
            .filter(Mastery.user_id == user.id, Mastery.topic_id == question.primary_topic_id)
            .first()
        )
        if mastery is None:
            mastery = Mastery(user_id=user.id, topic_id=question.primary_topic_id,
                              theta=0.0, mastery_p=PRIOR_P, attempts=0, correct=0)
            session.add(mastery)
        actual = 1.0 if correct else 0.0
        # Fast wrong answers smell like guesses, not gaps: discount the hit.
        # Slow wrong answers are genuine misconceptions: full penalty + retry.
        guess_discount = 1.0
        if not correct and response_ms is not None and response_ms < GUESS_MS:
            guess_discount = 0.5
        mastery.theta = mastery.theta + K_THETA * (actual - predicted(mastery.theta, b)) * guess_discount
        if correct:
            mastery.mastery_p = mastery.mastery_p + (1.0 - mastery.mastery_p) * P_LEARN
        else:
            mastery.mastery_p = mastery.mastery_p * (1.0 - (1.0 - P_FORGET_HIT) * guess_discount)
        mastery.attempts += 1
        mastery.correct += 1 if correct else 0
        mastery.last_seen = datetime.datetime.now(datetime.timezone.utc)
        mastery.next_review_at = schedule_next_review(correct, mastery.attempts)
        session.flush()
        snapshot = MasterySnapshot(topic_id=mastery.topic_id, theta=mastery.theta, mastery_p=mastery.mastery_p)

    session.commit()
    session.refresh(attempt)
    _record_daily_snapshot(session, user, exam)
    correct_option = next((o for o in question.options if o.is_correct), None)
    # Retry bookkeeping: a miss on a misconception-tagged option queues a
    # same-misconception retest. Computed here so the UI can say "queued".
    retry_queued = bool(misconception) and _has_retry_candidate(
        session, user, exam.id, attempted_ids={attempt.question_id}, misconception_id=misconception.id
    )
    return AnswerOut(
        attempt_id=attempt.id,
        correct=correct,
        correct_option_id=correct_option.id if correct_option else None,
        explanation=question.explanation,
        misconception=misconception.description if misconception else None,
        mastery=snapshot,
        options=[OptionRead.model_validate(o) for o in question.options],
        retry_queued=retry_queued,
    )


def _record_daily_snapshot(session: Session, user: User, exam: Exam) -> None:
    """One readiness point per user/exam/day, written on first answer of the day."""
    from app.models.practice import ReadinessSnapshot

    today = datetime.datetime.now(datetime.timezone.utc).date()
    exists = (
        session.query(ReadinessSnapshot.id)
        .filter(
            ReadinessSnapshot.user_id == user.id,
            ReadinessSnapshot.exam_id == exam.id,
            ReadinessSnapshot.snapshot_date == today,
        )
        .first()
    )
    if exists:
        return
    predicted = readiness(session, user, exam.id).predicted_score_pct
    session.add(ReadinessSnapshot(user_id=user.id, exam_id=exam.id, snapshot_date=today, predicted_pct=predicted))
    session.commit()


def _has_retry_candidate(
    session: Session, user: User, exam_id: int, attempted_ids: set[int], misconception_id: int
) -> bool:
    attempted_sub = select(Attempt.question_id).filter(Attempt.user_id == user.id)
    return (
        session.query(Question.id)
        .filter(
            Question.exam_id == exam_id,
            ~Question.id.in_(attempted_ids),
            ~Question.id.in_(attempted_sub),
            Question.options.any(Option.misconception_id == misconception_id),
        )
        .first()
        is not None
    )


def _exam_question_ids(session: Session, exam: Exam) -> list[int]:
    return [r[0] for r in session.query(Question.id).filter(Question.exam_id == exam.id).all()]


def select_next(session: Session, user: User, exam_id: int) -> PracticeQuestion | None:
    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")

    syllabus = _current_syllabus(session, exam)
    topics: list[Topic] = []
    if syllabus is not None:
        topics = (
            session.query(Topic)
            .filter(Topic.syllabus_id == syllabus.id)
            .order_by(Topic.sort_order, Topic.id)
            .all()
        )
    mmap = _mastery_map(session, user, [t.id for t in topics])

    qids = _exam_question_ids(session, exam)
    if not qids:
        return None
    attempted: set[int] = set()
    recent: list[int] = []
    if qids:
        rows = (
            session.query(Attempt.question_id)
            .filter(Attempt.user_id == user.id, Attempt.question_id.in_(qids))
            .order_by(Attempt.id.desc())
            .all()
        )
        seen = [r[0] for r in rows]
        attempted = set(seen)
        recent = seen[:HISTORY_EXCLUDE]

    now = datetime.datetime.now(datetime.timezone.utc)

    def priority(topic: Topic) -> float:
        m = mmap.get(topic.id)
        p = m.mastery_p if m else PRIOR_P
        w = topic.weight if topic.weight else 1.0
        if m is None or m.attempts == 0:
            days = 30.0  # unseen first: cold-start probe
            due_boost = 1.0
        else:
            nr = _as_utc(m.next_review_at)
            if nr is not None:
                overdue = (now - nr).total_seconds() / 86400.0
                days = max(0.0, overdue)
                due_boost = 3.0 if overdue >= 0 else 1.0
            else:
                last = _as_utc(m.last_seen)
                days = max(0.0, (now - last).total_seconds() / 86400.0) if last else 30.0
                due_boost = 1.0
        return w * (1.0 - p) * (1.0 + days / 7.0) * due_boost

    ordered_topics = sorted(topics, key=priority, reverse=True)

    def pick(pool: list[Question], theta: float = 0.0) -> Question | None:
        fresh = [q for q in pool if q.id not in attempted]
        cands = fresh or [q for q in pool if q.id not in recent]
        if not cands:
            # Bank exhausted: loop forever rather than stopping. The engine
            # keeps calibrating and retesting; repetition *is* the drill.
            cands = pool
        if not cands:
            return None
        # Prefer questions whose calibrated difficulty puts them in the
        # success band for this learner; fall back to anything unasked,
        # then to anything at all.
        in_band = [
            q
            for q in cands
            if BAND_LO <= predicted(theta, q.difficulty if q.difficulty is not None else B_DEFAULT) <= BAND_HI
        ]
        return random.choice(in_band or cands)

    # 1. Retest queue: a recent miss on a misconception-tagged option jumps
    # the queue — serve a *different* question testing the same misconception
    # to verify the explanation stuck (DeepSeek's micro-remediation loop).
    miss_mids: list[int] = [
        r[0]
        for r in (
            session.query(Attempt.misconception_id)
            .join(Question, Question.id == Attempt.question_id)
            .filter(
                Attempt.user_id == user.id,
                Question.exam_id == exam.id,
                Attempt.correct.is_(False),
                Attempt.misconception_id.is_not(None),
            )
            .order_by(Attempt.id.desc())
            .limit(RETRY_LOOKBACK)
            .all()
        )
    ]
    for mid in dict.fromkeys(miss_mids):  # most-recent miss first, deduped
        retry_pool = (
            session.query(Question)
            .options(selectinload(Question.options))
            .filter(
                Question.exam_id == exam.id,
                ~Question.id.in_(attempted) if attempted else True,
                Question.options.any(Option.misconception_id == mid),
            )
            .order_by(Question.id)
            .all()
        )
        chosen = pick(retry_pool)
        if chosen:
            return _serve(chosen)

    for topic in ordered_topics:
        m = mmap.get(topic.id)
        theta = m.theta if m else 0.0
        prob = predicted(theta)
        if topics and not (BAND_LO <= prob <= BAND_HI) and m is not None and m.attempts > 0:
            continue  # mastered or too hard: try the next topic
        pool = (
            session.query(Question)
            .options(selectinload(Question.options))
            .filter(Question.exam_id == exam.id)
            .filter(
                (Question.primary_topic_id == topic.id)
                | (Question.topics.any(Topic.id == topic.id))
            )
            .order_by(Question.id)
            .all()
        )
        chosen = pick(pool, theta)
        if chosen:
            return _serve(chosen)

    # Fallback: anything in the exam, prefer never-attempted.
    pool = (
        session.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.exam_id == exam.id)
        .order_by(Question.id)
        .all()
    )
    chosen = pick(pool)
    return _serve(chosen) if chosen else None


def _serve(question: Question) -> PracticeQuestion:
    # Insertion order only; the client shuffles and assigns A/B/C/D letters.
    # Grading and diagnosis key off option ids, so letters can never corrupt them.
    opts = [PracticeOption.model_validate(o) for o in question.options]
    return PracticeQuestion(
        id=question.id,
        exam_id=question.exam_id,
        syllabus_id=question.syllabus_id,
        primary_topic_id=question.primary_topic_id,
        question_type=question.question_type.value,
        stem=question.stem,
        options=opts,
    )


def readiness(session: Session, user: User, exam_id: int) -> dict:
    from app.schemas.practice import ReadinessOut, WeakTopic

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    syllabus = _current_syllabus(session, exam)
    topics = (
        session.query(Topic).filter(Topic.syllabus_id == syllabus.id).all()
        if syllabus
        else []
    )
    mmap = _mastery_map(session, user, [t.id for t in topics])
    weights = [(t.weight if t and t.weight else 1.0) for t in topics]
    total_w = sum(weights) or 1.0
    score = 0.0
    attempted = 0
    scored: list[tuple[Topic, float]] = []
    for topic, w in zip(topics, weights):
        m = mmap.get(topic.id)
        p = m.mastery_p if m else 0.0  # unseen counts as 0 for prediction
        if m and m.attempts > 0:
            attempted += 1
        score += (w / total_w) * p
        scored.append((topic, p))
    scored.sort(key=lambda tp: tp[1])
    weak = [
        WeakTopic(topic_id=t.id, code=t.code, name=t.name, mastery_p=round(p, 3))
        for t, p in scored[:3]
    ]
    predicted_pct = round(score * 100.0, 1)
    points_to_pass = round(exam.pass_mark - predicted_pct, 1) if exam.pass_mark is not None else None
    return ReadinessOut(
        exam_id=exam.id,
        predicted_score_pct=predicted_pct,
        pass_mark=exam.pass_mark,
        points_to_pass=points_to_pass,
        on_track=(points_to_pass <= 0) if points_to_pass is not None else None,
        topics_total=len(topics),
        topics_attempted=attempted,
        weak_topics=weak,
    )
