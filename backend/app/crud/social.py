import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.exam import ContentError
from app.crud.practice import (
    MIN_ACTIVE_DAY_ANSWERS,
    XP_CONSOLATION,
    _current_syllabus,
    _mastery_map,
    focus_minutes,
    xp_for_attempt,
)
from app.models.exam import Exam, Misconception, Question, Topic
from app.models.practice import Attempt, Mastery
from app.models.room import Room
from app.models.user import User

# Daily effort that still counts as "showing up", and the day-start rule for streaks.
FEASIBLE_MINUTES_PER_DAY = 120  # above this, the plan switches to triage mode
RATE_PER_10Q_AT_ZERO = 3.0  # predicted points gained per 10 answers from 0% (plateau-aware)
MIN_RATE_PER_10Q = 0.2  # learning-rate floor so the math never promises infinity


def _utc(dt: datetime.datetime | None) -> datetime.datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)  # SQLite returns naive
    return dt


def _today_utc() -> datetime.date:
    return datetime.datetime.now(datetime.timezone.utc).date()


def _week_start_utc(now: datetime.datetime) -> datetime.date:
    monday = now - datetime.timedelta(days=now.weekday())
    return monday.date()


def _exam_attempts(session: Session, exam: Exam) -> list[Attempt]:
    """All attempts on an exam's questions, oldest first. MVP: filtered in
    Python because SQLite stores naive timestamps (string compare with aware
    bounds is unreliable). Revisit with a proper range query on Postgres."""
    return (
        session.query(Attempt)
        .join(Question, Question.id == Attempt.question_id)
        .filter(Question.exam_id == exam.id)
        .order_by(Attempt.id)
        .all()
    )


def _difficulties(session: Session, exam: Exam) -> dict[int, float | None]:
    rows = session.query(Question.id, Question.difficulty).filter(Question.exam_id == exam.id).all()
    return {r[0]: r[1] for r in rows}


def _display_name(user: User) -> str:
    if user.last_name:
        return f"{user.first_name} {user.last_name[0]}."
    return user.first_name


# --- XP, streaks, stats -------------------------------------------------------


def xp_total(attempts: list[Attempt], difficulties: dict[int, float | None]) -> int:
    return sum(
        xp_for_attempt(a.correct, difficulties.get(a.question_id), a.response_ms) for a in attempts
    )


def streak_days(attempts: list[Attempt]) -> tuple[int, bool]:
    """(current streak, active today). A day counts with >= MIN_ACTIVE_DAY_ANSWERS."""
    by_day: dict[datetime.date, int] = {}
    for a in attempts:
        ts = _utc(a.created_at)
        if ts is None:
            continue
        day = ts.date()
        by_day[day] = by_day.get(day, 0) + 1
    active = [d for d, n in by_day.items() if n >= MIN_ACTIVE_DAY_ANSWERS]
    if not active:
        return 0, False
    active_set = set(active)
    today = _today_utc()
    cursor = today if today in active_set else today - datetime.timedelta(days=1)
    streak = 0
    while cursor in active_set:
        streak += 1
        cursor -= datetime.timedelta(days=1)
    return streak, today in active_set


def user_stats(session: Session, user: User, exam_id: int) -> dict:
    from app.schemas.social import PaceOut, StatsOut

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    attempts = [a for a in _exam_attempts(session, exam) if a.user_id == user.id]
    difficulties = _difficulties(session, exam)
    streak, active_today = streak_days(attempts)
    today = _today_utc()
    todays_ms = [
        a.response_ms
        for a in attempts
        if (_utc(a.created_at).date() == today if _utc(a.created_at) else False)
    ]
    ms_vals = [a.response_ms for a in attempts if a.response_ms]
    recent_ms = ms_vals[-20:] if ms_vals else []
    avg_ms = round(sum(recent_ms) / len(recent_ms)) if recent_ms else None
    allowance_ms = None
    verdict = None
    if exam.time_allowed_seconds and exam.question_count:
        allowance_ms = round(exam.time_allowed_seconds * 1000 / exam.question_count)
        if avg_ms is not None:
            verdict = "ahead of pace" if avg_ms <= allowance_ms else "behind pace"
    # Level from the same readiness number the dashboard shows.
    from app.crud.practice import readiness

    score = readiness(session, user, exam.id).predicted_score_pct
    level = "Bronze"
    if score >= 85:
        level = "Exam-ready"
    elif score >= 70:
        level = "Gold"
    elif score >= 50:
        level = "Silver"
    week_start = _week_start_utc(datetime.datetime.now(datetime.timezone.utc))
    week_xp = xp_total(
        [a for a in attempts if _utc(a.created_at) and _utc(a.created_at).date() >= week_start],
        difficulties,
    )
    from app.crud.explain import explain_xp_map

    _exp_map = explain_xp_map(session, exam.id, [user.id])
    _exp_week = explain_xp_map(session, exam.id, [user.id], since_date=week_start)
    week_xp += _exp_week.get(user.id, 0)
    all_time_explain = _exp_map.get(user.id, 0)
    correct_total = sum(1 for a in attempts if a.correct)
    wrong_total = len(attempts) - correct_total
    syllabus = _current_syllabus(session, exam)
    topics_practiced = 0
    if syllabus is not None:
        topic_ids = [t.id for t in session.query(Topic).filter(Topic.syllabus_id == syllabus.id).all()]
        if topic_ids:
            topics_practiced = (
                session.query(Mastery.topic_id)
                .filter(Mastery.user_id == user.id, Mastery.topic_id.in_(topic_ids), Mastery.attempts > 0)
                .distinct()
                .count()
            )
    return StatsOut(
        streak_days=streak,
        active_today=active_today,
        focus_minutes_today=focus_minutes(todays_ms),
        xp_week=week_xp,
        xp_total=xp_total(attempts, difficulties) + all_time_explain,
        level=level,
        questions_answered=len(attempts),
        questions_correct=correct_total,
        questions_wrong=wrong_total,
        accuracy_pct=round(correct_total / len(attempts) * 100.0, 1) if attempts else None,
        topics_practiced=topics_practiced,
        pace=PaceOut(avg_response_ms=avg_ms, allowance_ms=allowance_ms, verdict=verdict),
    )


def leaderboard(session: Session, user: User, exam_id: int, limit: int = 20) -> dict:
    from app.schemas.social import LeaderboardEntry, LeaderboardOut

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    now = datetime.datetime.now(datetime.timezone.utc)
    week_start = _week_start_utc(now)
    difficulties = _difficulties(session, exam)
    per_user: dict[int, list[Attempt]] = {}
    for a in _exam_attempts(session, exam):
        ts = _utc(a.created_at)
        if ts is None or ts.date() < week_start:
            continue
        per_user.setdefault(a.user_id, []).append(a)
    users = {u.id: u for u in session.query(User).filter(User.id.in_(per_user)).all()} if per_user else {}
    from app.crud.explain import explain_uids_since, explain_xp_map

    # Explain-only users (no attempts this week) still belong on the effort board.
    for uid in explain_uids_since(session, exam.id, since_date=week_start):
        per_user.setdefault(uid, [])
        if uid not in users:
            u = session.get(User, uid)
            if u is not None:
                users[uid] = u

    explain_map = explain_xp_map(session, exam.id, list(per_user), since_date=week_start)
    rows: list[tuple[int, int, User]] = []
    for uid, atts in per_user.items():
        u = users.get(uid)
        if u is None or not u.show_on_leaderboard:
            continue
        rows.append((xp_total(atts, difficulties) + explain_map.get(uid, 0), len(atts), u))
    rows.sort(key=lambda r: (-r[0], r[2].id))
    entries = [
        LeaderboardEntry(rank=i + 1, display_name=_display_name(u), xp=xp, questions=n)
        for i, (xp, n, u) in enumerate(rows[:limit])
    ]
    me = None
    for i, (xp, n, u) in enumerate(rows):
        if u.id == user.id:
            me = LeaderboardEntry(rank=i + 1, display_name=_display_name(u), xp=xp, questions=n)
            break
    return LeaderboardOut(exam_id=exam.id, week_start=week_start, entries=entries, me=me)


def history(session: Session, user: User, exam_id: int, wrong_only: bool, limit: int) -> list[dict]:
    from app.schemas.social import HistoryEntry

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    q = (
        session.query(Attempt, Question.stem)
        .join(Question, Question.id == Attempt.question_id)
        .filter(Attempt.user_id == user.id, Question.exam_id == exam.id)
        .order_by(Attempt.id.desc())
        .limit(limit * 3)  # over-fetch: wrong_only filters after
    )
    out: list[dict] = []
    for attempt, stem in q.all():
        if wrong_only and attempt.correct:
            continue
        out.append(
            HistoryEntry(
                attempt_id=attempt.id,
                question_id=attempt.question_id,
                stem=stem,
                correct=attempt.correct,
                answered_at=_utc(attempt.created_at),
            )
        )
        if len(out) >= limit:
            break
    return out


# --- Study plan ----------------------------------------------------------------


def study_plan(session: Session, user: User, exam_id: int) -> dict:
    from app.schemas.social import FocusTopic, PlanOut

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    from app.crud.practice import readiness

    ready = readiness(session, user, exam.id)
    score, target = ready.predicted_score_pct, exam.pass_mark
    if target is None:
        return PlanOut(
            exam_id=exam.id,
            predicted_score_pct=score,
            pass_mark=None,
            points_to_pass=None,
            days_left=None,
            questions_needed=None,
            minutes_per_day=None,
            feasible=None,
            note="Set a pass mark on this exam to unlock the daily plan.",
            focus_topics=_focus_topics(session, user, exam)[:3],
        )
    gap = max(0.0, target - score)
    days_left = (exam.exam_date - _today_utc()).days if exam.exam_date else None
    # Plateau-aware rate: fastest from zero, floors at MIN_RATE so the math
    # never promises infinite speed. Heuristic v1, recomputed every call.
    rate_per_10 = max(MIN_RATE_PER_10Q, RATE_PER_10Q_AT_ZERO * (1.0 - score / 100.0))
    questions_needed = 0 if gap <= 0 else int(gap / (rate_per_10 / 10.0)) + 1
    ms_vals = [
        a.response_ms
        for a in _exam_attempts(session, exam)
        if a.user_id == user.id and a.response_ms
    ]
    median_min = (sorted(ms_vals)[len(ms_vals) // 2] / 60000.0) if ms_vals else 1.5
    minutes_total = questions_needed * median_min
    if gap <= 0:
        return PlanOut(
            exam_id=exam.id,
            predicted_score_pct=score,
            pass_mark=target,
            points_to_pass=0.0,
            days_left=days_left,
            questions_needed=0,
            minutes_per_day=0.0,
            feasible=True,
            note="Already clear of the pass mark. Maintain with light review.",
            focus_topics=[],
        )
    if days_left is None:
        return PlanOut(
            exam_id=exam.id,
            predicted_score_pct=score,
            pass_mark=target,
            points_to_pass=round(gap, 1),
            days_left=None,
            questions_needed=questions_needed,
            minutes_per_day=None,
            feasible=None,
            note="Set an exam date to turn this into a daily plan.",
            focus_topics=_focus_topics(session, user, exam)[:3],
        )
    if days_left <= 0:
        return PlanOut(
            exam_id=exam.id,
            predicted_score_pct=score,
            pass_mark=target,
            points_to_pass=round(gap, 1),
            days_left=0,
            questions_needed=questions_needed,
            minutes_per_day=None,
            feasible=False,
            note="Exam day is here or past — triage to the top-3 topics below.",
            focus_topics=_focus_topics(session, user, exam)[:3],
        )
    minutes_per_day = round(minutes_total / days_left, 1)
    feasible = minutes_per_day <= FEASIBLE_MINUTES_PER_DAY
    note = (
        f"~{minutes_per_day} min/day for {days_left} days closes the gap at your current pace."
        if feasible
        else (
            f"Full coverage needs ~{minutes_per_day} min/day — not realistic. "
            "Triage to the highest-points-per-minute topics below."
        )
    )
    return PlanOut(
        exam_id=exam.id,
        predicted_score_pct=score,
        pass_mark=target,
        points_to_pass=round(gap, 1),
        days_left=days_left,
        questions_needed=questions_needed,
        minutes_per_day=minutes_per_day,
        feasible=feasible,
        note=note,
        focus_topics=_focus_topics(session, user, exam)[:3],
    )


def _focus_topics(session: Session, user: User, exam: Exam) -> list:
    from app.schemas.social import FocusTopic

    syllabus = _current_syllabus(session, exam)
    if syllabus is None:
        return []
    topics = session.query(Topic).filter(Topic.syllabus_id == syllabus.id).all()
    mmap = _mastery_map(session, user, [t.id for t in topics])
    ranked = []
    for t in topics:
        p = mmap[t.id].mastery_p if t.id in mmap else 0.0
        w = t.weight if t.weight else 1.0
        ranked.append((w * (1.0 - p), t, p))
    ranked.sort(key=lambda r: -r[0])
    return [
        FocusTopic(topic_id=t.id, name=t.name, points_share_pct=round(share * 100.0, 1))
        for share, t, _ in ranked
    ]


def _readiness_band(score: float) -> str:
    if score >= 85:
        return "85+"
    if score >= 70:
        return "70-85"
    if score >= 50:
        return "50-70"
    return "<50"


def cohort(session: Session, user: User, exam_id: int) -> dict:
    from app.schemas.social import CohortOut, RoomQuestionStat

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    now = datetime.datetime.now(datetime.timezone.utc)
    week_ago = now - datetime.timedelta(days=7)
    month_ago = now - datetime.timedelta(days=30)
    all_atts = _exam_attempts(session, exam)
    recent = [a for a in all_atts if _utc(a.created_at) and _utc(a.created_at) >= week_ago]
    learners_active_week = len({a.user_id for a in recent})
    # Readiness bands for learners active in the last 30 days.
    syllabus = _current_syllabus(session, exam)
    topics = session.query(Topic).filter(Topic.syllabus_id == syllabus.id).all() if syllabus else []
    weights = [(t.weight if t.weight else 1.0) for t in topics]
    total_w = sum(weights) or 1.0
    uids = {a.user_id for a in all_atts if _utc(a.created_at) and _utc(a.created_at) >= month_ago}
    band_counts = {"<50": 0, "50-70": 0, "70-85": 0, "85+": 0}
    my_band = None
    for uid in uids:
        mmap = _mastery_map(session, User(id=uid), [t.id for t in topics])
        s = sum((weights[i] / total_w) * (mmap[t.id].mastery_p if t.id in mmap else 0.0) for i, t in enumerate(topics))
        band = _readiness_band(s * 100.0)
        band_counts[band] += 1
        if uid == user.id:
            my_band = band
    # Trap of the day: most-missed question from yesterday (>=3 attempts).
    yesterday = (now - datetime.timedelta(days=1)).date()
    by_q: dict[int, list[Attempt]] = {}
    for a in all_atts:
        ts = _utc(a.created_at)
        if ts and ts.date() == yesterday:
            by_q.setdefault(a.question_id, []).append(a)
    trap = None
    worst = None
    for qid, atts in by_q.items():
        if len(atts) >= 3:
            miss_rate = sum(1 for a in atts if not a.correct) / len(atts)
            if worst is None or miss_rate > worst[0]:
                worst = (miss_rate, qid, atts)
    if worst:
        q = session.get(Question, worst[1])
        trap = RoomQuestionStat(
            question_id=worst[1],
            stem=q.stem if q else "",
            attempts=len(worst[2]),
            correct_rate=round(1.0 - worst[0], 2),
        )
    days_left = (exam.exam_date - _today_utc()).days if exam.exam_date else None
    return CohortOut(
        exam_id=exam.id,
        days_left=days_left,
        learners_active_week=learners_active_week,
        band_counts=band_counts,
        my_band=my_band,
        trap_of_day=trap,
    )


# --- Drill rooms -----------------------------------------------------------------


def _room_read(session: Session, room: Room) -> dict:
    from app.schemas.social import RoomRead

    exam = session.get(Exam, room.exam_id)
    return RoomRead(
        id=room.id,
        exam_id=room.exam_id,
        exam_name=exam.name if exam else "",
        name=room.name,
        starts_at=_utc(room.starts_at),
        ends_at=_utc(room.ends_at),
        is_official=bool(room.is_official),
    )


def create_room(session: Session, user: User, exam_id: int, name: str | None,
                starts_at: datetime.datetime, ends_at: datetime.datetime,
                is_official: bool = False) -> dict:
    from app.crud.exam import can_read_exam, is_admin

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    if exam is None or not can_read_exam(user, exam):
        raise ContentError("Exam not found")
    if is_official and not is_admin(user):
        raise ContentError("Only admins can create official rooms")
    if _utc(ends_at) <= _utc(starts_at):
        raise ContentError("ends_at must be after starts_at")
    room = Room(exam_id=exam.id, name=name,
                starts_at=starts_at, ends_at=ends_at, created_by=user.id,
                is_official=is_official)
    session.add(room)
    session.commit()
    session.refresh(room)
    return _room_read(session, room)


def get_room(session: Session, room_id: int) -> Room | None:
    return session.get(Room, room_id)


def list_official_rooms(session: Session, user: User, limit: int = 20) -> list:
    """House-run rooms (weekly mocks, daily sprints) on public exams, soonest first.
    Anyone who can read the exam can see them; joining happens by answering."""
    from app.models.exam import ExamStatus, Visibility

    now = datetime.datetime.now(datetime.timezone.utc)
    rooms = (
        session.query(Room)
        .join(Exam, Exam.id == Room.exam_id)
        .filter(
            Room.is_official.is_(True),
            Exam.visibility == Visibility.public,
            Exam.status == ExamStatus.active,
            Room.ends_at >= now - datetime.timedelta(days=1),
        )
        .order_by(Room.starts_at)
        .limit(limit)
        .all()
    )
    return [_room_read(session, r) for r in rooms]


def list_my_rooms(session: Session, user: User) -> list:
    """Rooms for exams the user is enrolled in, newest first."""
    from app.models.practice import Enrollment

    exam_ids = session.query(Enrollment.exam_id).filter(Enrollment.user_id == user.id)
    rooms = (
        session.query(Room)
        .filter(Room.exam_id.in_(exam_ids))
        .order_by(Room.starts_at.desc())
        .all()
    )
    return [_room_read(session, r) for r in rooms]


def list_rooms(session: Session, user: User, exam_id: int) -> list:
    from app.crud.exam import can_read_exam

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    if exam is None or not can_read_exam(user, exam):
        raise ContentError("Exam not found")
    rooms = session.query(Room).filter(Room.exam_id == exam.id).order_by(Room.starts_at).all()
    return [_room_read(session, r) for r in rooms]


def room_stats(session: Session, user: User, room_id: int) -> dict:
    from app.schemas.social import RoomQuestionStat, RoomRead, RoomStats

    room = get_room(session, room_id)
    if room is None:
        raise ContentError("Room not found")
    exam = session.get(Exam, room.exam_id)
    from app.crud.exam import can_read_exam

    if exam is None or not can_read_exam(user, exam):
        raise ContentError("Room not found")
    now = datetime.datetime.now(datetime.timezone.utc)
    start, end = _utc(room.starts_at), _utc(room.ends_at)
    status = "upcoming" if now < start else ("live" if now <= end else "ended")
    in_window = [
        a for a in _exam_attempts(session, exam)
        if _utc(a.created_at) and start <= _utc(a.created_at) <= end
    ]
    participants = len({a.user_id for a in in_window})
    accuracy = round(sum(1 for a in in_window if a.correct) / len(in_window) * 100.0, 1) if in_window else None
    by_q: dict[int, list[Attempt]] = {}
    for a in in_window:
        by_q.setdefault(a.question_id, []).append(a)
    hardest: list[RoomQuestionStat] = []
    for qid, atts in sorted(by_q.items(), key=lambda kv: sum(x.correct for x in kv[1]) / len(kv[1])):
        if len(atts) < 2:
            continue
        q = session.get(Question, qid)
        hardest.append(RoomQuestionStat(
            question_id=qid, stem=q.stem if q else "",
            attempts=len(atts),
            correct_rate=round(sum(1 for a in atts if a.correct) / len(atts), 2),
        ))
        if len(hardest) >= 3:
            break
    trap = None
    mids = [a.misconception_id for a in in_window if a.misconception_id]
    if mids:
        top = max(set(mids), key=mids.count)
        m = session.get(Misconception, top)
        trap = m.description if m else None
    return RoomStats(
        room=RoomRead(
            id=room.id,
            exam_id=exam.id,
            exam_name=exam.name,
            name=room.name,
            starts_at=_utc(room.starts_at),
            ends_at=_utc(room.ends_at),
            is_official=bool(room.is_official),
        ),
        status=status,
        participants=participants,
        answers=len(in_window),
        accuracy_pct=accuracy,
        hardest_questions=hardest,
        top_trap=trap,
    )


def room_leaderboard(session: Session, user: User, room_id: int, limit: int = 20) -> dict:
    """Effort-only ranking inside one room window. Same display-name privacy
    rules as the global board; mastery never appears."""
    from app.schemas.social import LeaderboardEntry, RoomLeaderboardOut

    room = get_room(session, room_id)
    if room is None:
        raise ContentError("Room not found")
    exam = session.get(Exam, room.exam_id)
    from app.crud.exam import can_read_exam

    if exam is None or not can_read_exam(user, exam):
        raise ContentError("Room not found")
    now = datetime.datetime.now(datetime.timezone.utc)
    start, end = _utc(room.starts_at), _utc(room.ends_at)
    in_window = [
        a for a in _exam_attempts(session, exam)
        if _utc(a.created_at) and start <= _utc(a.created_at) <= end
    ]
    difficulties = _difficulties(session, exam)
    per_user: dict[int, list[Attempt]] = {}
    for a in in_window:
        per_user.setdefault(a.user_id, []).append(a)
    users = {u.id: u for u in session.query(User).filter(User.id.in_(list(per_user))).all()} if per_user else {}
    rows: list[tuple[int, int, User]] = []
    for uid, atts in per_user.items():
        u = users.get(uid)
        if u is None or not u.show_on_leaderboard:
            continue
        rows.append((xp_total(atts, difficulties), len(atts), u))
    rows.sort(key=lambda r: (-r[0], r[2].id))
    entries = [
        LeaderboardEntry(rank=i + 1, display_name=_display_name(u), xp=xp, questions=n)
        for i, (xp, n, u) in enumerate(rows[:limit])
    ]
    me = None
    for i, (xp, n, u) in enumerate(rows):
        if u.id == user.id:
            me = LeaderboardEntry(rank=i + 1, display_name=_display_name(u), xp=xp, questions=n)
            break
    return RoomLeaderboardOut(room_id=room.id, entries=entries, me=me)


# --- Analytics ----------------------------------------------------------------------


def analytics(session: Session, user: User, exam_id: int) -> dict:
    """Investigative view: weekly activity, readiness curve (daily snapshots),
    per-topic state, misconception ledger, room history with placements."""
    from app.schemas.social import (
        AnalyticsOut,
        AnalyticsPoint,
        AnalyticsRoom,
        AnalyticsTopic,
        AnalyticsWeek,
        MisconceptionStatus,
    )

    exam = session.get(Exam, exam_id)
    if exam is None:
        raise ContentError("Exam not found")
    from app.crud.exam import can_read_exam

    if not can_read_exam(user, exam):
        raise ContentError("Exam not found")

    difficulties = _difficulties(session, exam)
    mine = [a for a in _exam_attempts(session, exam) if a.user_id == user.id]
    now = datetime.datetime.now(datetime.timezone.utc)

    # Weekly buckets, last 8 weeks.
    weeks: list[AnalyticsWeek] = []
    today = now.date()
    monday = today - datetime.timedelta(days=today.weekday())
    for w in range(7, -1, -1):
        start = monday - datetime.timedelta(weeks=w)
        end = start + datetime.timedelta(days=7)
        bucket = [a for a in mine if _utc(a.created_at) and start <= _utc(a.created_at).date() < end]
        correct = sum(1 for a in bucket if a.correct)
        weeks.append(AnalyticsWeek(
            week_start=start,
            xp=xp_total(bucket, difficulties),
            answered=len(bucket),
            correct=correct,
            accuracy=round(correct / len(bucket) * 100.0, 1) if bucket else None,
        ))

    # Per-topic current state.
    syllabus = _current_syllabus(session, exam)
    topics = session.query(Topic).filter(Topic.syllabus_id == syllabus.id).order_by(Topic.sort_order).all() if syllabus else []
    mmap = _mastery_map(session, user, [t.id for t in topics])
    per_topic: dict[int, list[Attempt]] = {t.id: [] for t in topics}
    for a in mine:
        q = session.get(Question, a.question_id)
        if q is not None and q.primary_topic_id in per_topic:
            per_topic[q.primary_topic_id].append(a)
    topics_out: list[AnalyticsTopic] = []
    for t in topics:
        m = mmap.get(t.id)
        atts = per_topic[t.id]
        ok = sum(1 for a in atts if a.correct)
        topics_out.append(AnalyticsTopic(
            topic_id=t.id,
            code=t.code,
            name=t.name,
            weight=t.weight if t.weight is not None else 1.0,
            mastery_p=round(m.mastery_p, 3) if m else 0.0,
            theta=round(m.theta, 3) if m else 0.0,
            attempts=len(atts),
            correct=ok,
            accuracy=round(ok / len(atts) * 100.0, 1) if atts else None,
        ))

    # Misconception ledger.
    ledger: list[MisconceptionStatus] = []
    tids = [t.id for t in topics]
    if tids:
        tname = {t.id: t.name for t in topics}
        cutoff = now - datetime.timedelta(days=14)
        for mc in session.query(Misconception).filter(Misconception.topic_id.in_(tids)).all():
            hits = sorted(_utc(a.created_at) for a in mine if a.misconception_id == mc.id and _utc(a.created_at))
            if not hits:
                status = "never"
            elif hits[-1] >= cutoff:
                status = "open"
            else:
                status = "quiet"
            cleared = sum(1 for a in mine if a.correct and _utc(a.created_at) and (not hits or _utc(a.created_at) > hits[-1]))
            ledger.append(MisconceptionStatus(
                id=mc.id,
                code=mc.code,
                description=mc.description,
                topic_name=tname.get(mc.topic_id, ""),
                triggered_count=len(hits),
                last_triggered=hits[-1] if hits else None,
                status=status,
                correct_since=cleared,
            ))
        ledger.sort(key=lambda m: (m.status != "open", -(m.triggered_count or 0)))

    # Room history with placement.
    rooms_out: list[AnalyticsRoom] = []
    for room in list_my_rooms(session, user):
        if room.exam_id != exam.id:
            continue
        start, end = _utc(room.starts_at), _utc(room.ends_at)
        window = [a for a in _exam_attempts(session, exam)
                  if _utc(a.created_at) and start <= _utc(a.created_at) <= end]
        mine_here = [a for a in window if a.user_id == user.id]
        if not mine_here:
            continue
        per_user: dict[int, list[Attempt]] = {}
        for a in window:
            per_user.setdefault(a.user_id, []).append(a)
        ranked = sorted(per_user.items(), key=lambda kv: (-xp_total(kv[1], difficulties), kv[0]))
        rank = next((i + 1 for i, (uid, _) in enumerate(ranked) if uid == user.id), None)
        ok = sum(1 for a in mine_here if a.correct)
        rooms_out.append(AnalyticsRoom(
            room_id=room.id,
            name=room.name,
            status="upcoming" if now < start else ("live" if now <= end else "ended"),
            rank=rank,
            participants=len(per_user),
            user_xp=xp_total(mine_here, difficulties),
            user_accuracy=round(ok / len(mine_here) * 100.0, 1),
        ))
        if len(rooms_out) >= 10:
            break

    from app.models.practice import ReadinessSnapshot

    curve = [
        AnalyticsPoint(date=r.snapshot_date, predicted_pct=r.predicted_pct)
        for r in session.query(ReadinessSnapshot)
        .filter(ReadinessSnapshot.user_id == user.id, ReadinessSnapshot.exam_id == exam.id)
        .order_by(ReadinessSnapshot.snapshot_date)
        .limit(90)
        .all()
    ]
    return AnalyticsOut(
        exam_id=exam.id,
        weeks=weeks,
        readiness_curve=curve,
        topics=topics_out,
        misconceptions=ledger,
        rooms=rooms_out,
    )
