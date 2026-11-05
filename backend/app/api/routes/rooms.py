from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.narration import NarrateIn, NarrateOut
from app.schemas.social import (
    AnalyticsOut,
    CohortOut,
    HistoryEntry,
    LeaderboardOut,
    PlanOut,
    RoomCreate,
    RoomLeaderboardOut,
    RoomRead,
    RoomStats,
    StatsOut,
)

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=RoomRead)
async def create_room(data: RoomCreate, session: SessionDep, user: CurrentUserDep) -> RoomRead:
    try:
        return crud.create_room(session, user, data.exam_id, data.name, data.starts_at, data.ends_at, data.is_official)
    except crud.ContentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/official/", response_model=list[RoomRead])
async def official_rooms(session: SessionDep, user: CurrentUserDep):
    return crud.list_official_rooms(session, user)


@router.get("/mine/", response_model=list[RoomRead])
async def my_rooms(session: SessionDep, user: CurrentUserDep):
    return crud.list_my_rooms(session, user)


@router.get("/", response_model=list[RoomRead])
async def upcoming_rooms(exam_id: int, session: SessionDep, user: CurrentUserDep):
    try:
        return crud.list_rooms(session, user, exam_id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/{room_id}/", response_model=RoomRead)
async def get_room(room_id: int, session: SessionDep, user: CurrentUserDep):
    from app.models.exam import Exam as ExamModel
    from app.models.room import Room as RoomModel

    if room_id <= 0:
        raise HTTPException(status_code=404, detail="Room not found")
    room = session.get(RoomModel, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    exam = session.get(ExamModel, room.exam_id)
    if exam is None or not crud.can_read_exam(user, exam):
        raise HTTPException(status_code=404, detail="Room not found")
    return _room_read(session, room)


def _room_read(session: SessionDep, room):
    from app.schemas.social import RoomRead as RR

    from app.models.exam import Exam as ExamModel

    exam = session.get(ExamModel, room.exam_id)
    return RR(
        id=room.id,
        exam_id=room.exam_id,
        exam_name=exam.name if exam else "",
        name=room.name,
        starts_at=room.starts_at,
        ends_at=room.ends_at,
    )


@router.get("/{room_id}/stats/", response_model=RoomStats)
async def get_room_stats(room_id: int, session: SessionDep, user: CurrentUserDep):
    if room_id <= 0:
        raise HTTPException(status_code=404, detail="Room not found")
    try:
        return crud.room_stats(session, user, room_id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/{room_id}/leaderboard/", response_model=RoomLeaderboardOut)
async def get_room_leaderboard(
    room_id: int, session: SessionDep, user: CurrentUserDep,
    limit: int = Query(default=20, ge=1, le=100),
):
    if room_id <= 0:
        raise HTTPException(status_code=404, detail="Room not found")
    try:
        return crud.room_leaderboard(session, user, room_id, limit)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


practice_extra = APIRouter(prefix="/practice", tags=["Practice"])


@practice_extra.get("/plan/", response_model=PlanOut)
async def get_plan(exam_id: int, session: SessionDep, user: CurrentUserDep):
    try:
        return crud.study_plan(session, user, exam_id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@practice_extra.get("/stats/", response_model=StatsOut)
async def get_stats(exam_id: int, session: SessionDep, user: CurrentUserDep):
    try:
        return crud.user_stats(session, user, exam_id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@practice_extra.get("/leaderboard/", response_model=LeaderboardOut)
async def get_leaderboard(
    exam_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        return crud.leaderboard(session, user, exam_id, limit)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@practice_extra.get("/history/", response_model=list[HistoryEntry])
async def get_history(
    exam_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    wrong_only: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
):
    try:
        return crud.history(session, user, exam_id, wrong_only, limit)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@practice_extra.get("/cohort/", response_model=CohortOut)
async def get_cohort(exam_id: int, session: SessionDep, user: CurrentUserDep):
    try:
        return crud.cohort(session, user, exam_id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@practice_extra.get("/analytics/", response_model=AnalyticsOut)
async def get_analytics(exam_id: int, session: SessionDep, user: CurrentUserDep):
    try:
        return crud.analytics(session, user, exam_id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@practice_extra.post("/narrate/", response_model=NarrateOut)
async def narrate(data: NarrateIn, session: SessionDep, user: CurrentUserDep):
    try:
        return crud.narrate(session, user, data.kind, data.exam_id, data.context)
    except crud.ContentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
