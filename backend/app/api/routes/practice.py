from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app import crud, llm
from app.api.deps import CurrentUserDep, SessionDep
from app.models.exam import Exam as ExamModel
from app.schemas.explain import ChallengeBoardOut, ExplainHistoryEntry, ExplainIn, ExplainOut, TranscribeOut
from app.schemas.practice import AnswerIn, AnswerOut, PracticeQuestion, ReadinessOut

router = APIRouter(prefix="/practice", tags=["Practice"])

MAX_VOICE_BYTES = 8 * 1024 * 1024  # well under Meta's 32 MB cap (~2 min of 16 kHz WAV)


@router.post("/answer/", status_code=status.HTTP_201_CREATED, response_model=AnswerOut)
async def answer(data: AnswerIn, session: SessionDep, user: CurrentUserDep) -> AnswerOut:
    question = crud.get_question(session, data.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    exam = session.get(ExamModel, question.exam_id)
    if exam is None or not crud.can_read_exam(user, exam):
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        return crud.record_answer(session, user, data.question_id, data.chosen_option_id, data.response_ms)
    except crud.ContentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/next/", response_model=PracticeQuestion | None)
async def next_question(exam_id: int, session: SessionDep, user: CurrentUserDep):
    exam = session.get(ExamModel, exam_id)
    if exam is None or not crud.can_read_exam(user, exam):
        raise HTTPException(status_code=404, detail="Exam not found")
    try:
        return crud.select_next(session, user, exam.id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/readiness/", response_model=ReadinessOut)
async def exam_readiness(exam_id: int, session: SessionDep, user: CurrentUserDep):
    exam = session.get(ExamModel, exam_id)
    if exam is None or not crud.can_read_exam(user, exam):
        raise HTTPException(status_code=404, detail="Exam not found")
    try:
        return crud.readiness(session, user, exam.id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post("/explain/", status_code=status.HTTP_201_CREATED, response_model=ExplainOut)
async def explain(data: ExplainIn, session: SessionDep, user: CurrentUserDep) -> ExplainOut:
    question = crud.get_question(session, data.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    exam = session.get(ExamModel, question.exam_id)
    if exam is None or not crud.can_read_exam(user, exam):
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        return crud.grade_explanation(session, user, data.question_id, data.text)
    except crud.ContentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/explain/history/", response_model=list[ExplainHistoryEntry])
async def explain_history(exam_id: int, session: SessionDep, user: CurrentUserDep, limit: int = 20):
    exam = session.get(ExamModel, exam_id)
    if exam is None or not crud.can_read_exam(user, exam):
        raise HTTPException(status_code=404, detail="Exam not found")
    return crud.explain_history(session, user, exam.id, min(max(limit, 1), 50))


@router.post("/transcribe/", response_model=TranscribeOut)
async def transcribe_audio(file: UploadFile, session: SessionDep, user: CurrentUserDep):
    """Voice input for explanations: WAV audio in, transcript out.

    Transcribed by Meta Muse Voice Transcribe; the transcript then travels
    the identical grading path as typed text. Auth required; audio is not stored.
    """
    _ = (session, user)  # auth + readability gate; no DB touch needed
    data = await file.read()
    if not (file.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=400, detail="Upload audio (WAV).")
    if len(data) > MAX_VOICE_BYTES:
        raise HTTPException(status_code=400, detail="Audio too long — keep it under ~2 minutes.")
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio.")
    try:
        return TranscribeOut(transcript=await llm.atranscribe(data))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from None
    except Exception as exc:  # network etc: retryable, never a silent empty grade
        raise HTTPException(status_code=502, detail="Transcription service unreachable.") from exc


@router.get("/challenges/", response_model=ChallengeBoardOut)
async def challenge_board(exam_id: int, session: SessionDep, user: CurrentUserDep):
    exam = session.get(ExamModel, exam_id)
    if exam is None or not crud.can_read_exam(user, exam):
        raise HTTPException(status_code=404, detail="Exam not found")
    try:
        return crud.challenges(session, user, exam.id)
    except crud.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
