from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.api.deps import CurrentUserDep, SessionDep
from app.models.exam import Exam
from app.schemas.exam import (
    EnrollmentRead,
    ExamCreate,
    ExamFacts,
    ExamRead,
    ExamUpdate,
    MisconceptionCreate,
    MisconceptionRead,
    QuestionCreate,
    QuestionRead,
    SyllabusCreate,
    SyllabusRead,
    TopicCreate,
    TopicRead,
)

router = APIRouter(prefix="/exams", tags=["Exams"])


def _readable_exam(session: SessionDep, user: CurrentUserDep, exam_id: int):
    exam = session.get(Exam, exam_id)
    if exam is None or not crud.can_read_exam(user, exam):
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


def _writable_exam(session: SessionDep, user: CurrentUserDep, exam_id: int):
    exam = _readable_exam(session, user, exam_id)
    if not crud.can_write_exam(user, exam):
        raise HTTPException(status_code=403, detail="Not allowed to modify this exam")
    return exam


def _as_400(exc: Exception) -> HTTPException:
    msg = str(exc)
    code = 403 if "Only admins" in msg else 400
    return HTTPException(status_code=code, detail=msg)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ExamRead)
async def create_exam(data: ExamCreate, session: SessionDep, user: CurrentUserDep) -> ExamRead:
    try:
        return crud.create_exam(session, user, data)
    except crud.ContentError as exc:
        raise _as_400(exc) from None


@router.get("/featured/", response_model=list[ExamRead])
async def featured_exams(session: SessionDep, _: CurrentUserDep) -> list[ExamRead]:
    return crud.list_public_exams(session)


@router.get("/mine/", response_model=list[ExamRead])
async def my_exams(session: SessionDep, user: CurrentUserDep) -> list[ExamRead]:
    """Exams the user is preparing for: owned + explicitly joined."""
    return crud.list_enrolled_exams(session, user)


@router.post("/{exam_id:int}/enroll/", status_code=status.HTTP_201_CREATED, response_model=EnrollmentRead)
async def join_exam(exam_id: int, session: SessionDep, user: CurrentUserDep) -> EnrollmentRead:
    exam = _readable_exam(session, user, exam_id)
    return crud.enroll_user(session, user, exam)


@router.delete("/{exam_id:int}/enroll/", status_code=status.HTTP_204_NO_CONTENT)
async def leave_exam(exam_id: int, session: SessionDep, user: CurrentUserDep) -> None:
    exam = _readable_exam(session, user, exam_id)
    crud.leave_exam(session, user, exam)
    return None


@router.get("/{exam_id:int}/", response_model=ExamRead)
async def get_exam(exam_id: int, session: SessionDep, user: CurrentUserDep) -> ExamRead:
    return _readable_exam(session, user, exam_id)


@router.patch("/{exam_id:int}/", response_model=ExamRead)
async def patch_exam(
    exam_id: int, data: ExamUpdate, session: SessionDep, user: CurrentUserDep
) -> ExamRead:
    exam = _writable_exam(session, user, exam_id)
    try:
        return crud.update_exam(session, user, exam, data)
    except crud.ContentError as exc:
        raise _as_400(exc) from None


@router.get("/{exam_id:int}/syllabi/", response_model=list[SyllabusRead])
async def exam_syllabi(exam_id: int, session: SessionDep, user: CurrentUserDep):
    return crud.list_syllabi(session, _readable_exam(session, user, exam_id))


@router.get("/{exam_id:int}/facts/", response_model=ExamFacts)
async def exam_facts(exam_id: int, session: SessionDep, user: CurrentUserDep) -> ExamFacts:
    return crud.exam_facts(session, _readable_exam(session, user, exam_id))


@router.post("/{exam_id:int}/syllabi/", status_code=status.HTTP_201_CREATED, response_model=SyllabusRead)
async def add_syllabus(
    exam_id: int, data: SyllabusCreate, session: SessionDep, user: CurrentUserDep
):
    exam = _writable_exam(session, user, exam_id)
    try:
        return crud.create_syllabus(session, exam, data)
    except crud.ContentError as exc:
        raise _as_400(exc) from None


@router.get("/{exam_id:int}/questions/", response_model=list[QuestionRead])
async def exam_questions(
    exam_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    syllabus_id: int | None = None,
    topic_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return crud.list_questions(
        session, _readable_exam(session, user, exam_id), syllabus_id, topic_id, limit, offset
    )


@router.post("/{exam_id:int}/questions/", status_code=status.HTTP_201_CREATED, response_model=QuestionRead)
async def add_question(
    exam_id: int, data: QuestionCreate, session: SessionDep, user: CurrentUserDep
):
    exam = _writable_exam(session, user, exam_id)
    try:
        return crud.create_question(session, exam, data)
    except crud.ContentError as exc:
        raise _as_400(exc) from None


syllabus_router = APIRouter(prefix="/syllabi", tags=["Syllabi"])


@syllabus_router.get("/{syllabus_id}/topics/", response_model=list[TopicRead])
async def syllabus_topics(syllabus_id: int, session: SessionDep, user: CurrentUserDep):
    syllabus = crud.get_syllabus(session, syllabus_id)
    if syllabus is None:
        raise HTTPException(status_code=404, detail="Syllabus not found")
    # Resolve exam through syllabus.exam_id without extra query tricks:
    from app.models.exam import Exam as ExamModel

    exam_row = session.get(ExamModel, syllabus.exam_id)
    if exam_row is None or not crud.can_read_exam(user, exam_row):
        raise HTTPException(status_code=404, detail="Syllabus not found")
    return crud.list_topics(session, syllabus)


@syllabus_router.put("/{syllabus_id}/topics/bulk/", response_model=list[TopicRead])
async def bulk_topics(
    syllabus_id: int, items: list[TopicCreate], session: SessionDep, user: CurrentUserDep
):
    from app.models.exam import Exam as ExamModel

    syllabus = crud.get_syllabus(session, syllabus_id)
    if syllabus is None:
        raise HTTPException(status_code=404, detail="Syllabus not found")
    exam_row = session.get(ExamModel, syllabus.exam_id)
    if exam_row is None or not crud.can_write_exam(user, exam_row):
        raise HTTPException(status_code=403, detail="Not allowed to modify this exam")
    if len(items) > 500:
        raise HTTPException(status_code=400, detail="Max 500 topics per bulk call")
    try:
        return crud.upsert_topics(session, syllabus, items)
    except crud.ContentError as exc:
        raise _as_400(exc) from None


topic_router = APIRouter(prefix="/topics", tags=["Topics"])


@topic_router.get("/{topic_id}/misconceptions/", response_model=list[MisconceptionRead])
async def topic_misconceptions(topic_id: int, session: SessionDep, user: CurrentUserDep):
    from app.models.exam import Exam as ExamModel, Syllabus as SyllabusModel

    topic = crud.get_topic(session, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    syllabus = session.get(SyllabusModel, topic.syllabus_id)
    exam_row = session.get(ExamModel, syllabus.exam_id) if syllabus else None
    if exam_row is None or not crud.can_read_exam(user, exam_row):
        raise HTTPException(status_code=404, detail="Topic not found")
    return crud.list_misconceptions(session, topic)


@topic_router.post(
    "/{topic_id}/misconceptions/",
    status_code=status.HTTP_201_CREATED,
    response_model=MisconceptionRead,
)
async def add_misconception(
    topic_id: int, data: MisconceptionCreate, session: SessionDep, user: CurrentUserDep
):
    from app.models.exam import Exam as ExamModel, Syllabus as SyllabusModel

    topic = crud.get_topic(session, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    syllabus = session.get(SyllabusModel, topic.syllabus_id)
    exam_row = session.get(ExamModel, syllabus.exam_id) if syllabus else None
    if exam_row is None or not crud.can_write_exam(user, exam_row):
        raise HTTPException(status_code=403, detail="Not allowed to modify this exam")
    try:
        return crud.create_misconception(session, topic, data)
    except crud.ContentError as exc:
        raise _as_400(exc) from None


question_router = APIRouter(prefix="/questions", tags=["Questions"])


@question_router.get("/{question_id}/", response_model=QuestionRead)
async def get_question(question_id: int, session: SessionDep, user: CurrentUserDep):
    from app.models.exam import Exam as ExamModel

    question = crud.get_question(session, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    exam_row = session.get(ExamModel, question.exam_id)
    if exam_row is None or not crud.can_read_exam(user, exam_row):
        raise HTTPException(status_code=404, detail="Question not found")
    return question
