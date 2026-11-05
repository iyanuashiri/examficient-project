from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.certification import Certification
from app.models.exam import (
    Exam,
    ExamStatus,
    Misconception,
    Option,
    Origin,
    Question,
    QuestionType,
    Syllabus,
    Topic,
    Visibility,
)
from app.models.user import User, UserRole
from app.schemas.exam import (
    ExamCreate,
    ExamUpdate,
    MisconceptionCreate,
    QuestionCreate,
    SyllabusCreate,
    TopicCreate,
)


class ContentError(ValueError):
    """Domain error (bad reference, duplicate, permission) -> mapped to 4xx."""


def is_admin(user: User) -> bool:
    return user.role == UserRole.admin


def can_read_exam(user: User, exam: Exam) -> bool:
    return exam.visibility == Visibility.public or exam.user_id == user.id or is_admin(user)


def can_write_exam(user: User, exam: Exam) -> bool:
    return exam.user_id == user.id or is_admin(user)


def _parse_visibility(value: str) -> Visibility:
    try:
        return Visibility(value)
    except ValueError:
        raise ContentError(f"Invalid visibility: {value!r}") from None


def get_exam_by_code(session: Session, code: str) -> Exam | None:
    return session.query(Exam).filter(Exam.code == code).first()


def list_public_exams(session: Session) -> list[Exam]:
    """Featured library: all public + active exams. Whether the user has
    joined is a per-exam concern, handled on the detail page
    (Enroll vs Start practice)."""
    return (
        session.query(Exam)
        .filter(Exam.visibility == Visibility.public, Exam.status == ExamStatus.active)
        .order_by(Exam.code)
        .all()
    )


def get_enrollment(session: Session, user: User, exam_id: int):
    from app.models.practice import Enrollment

    return (
        session.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.exam_id == exam_id)
        .first()
    )


def enroll_user(
    session: Session, user: User, exam: Exam, personal_deadline=None
):
    """Join an exam. Idempotent — returns the existing row if already joined."""
    from app.models.practice import Enrollment

    existing = get_enrollment(session, user, exam.id)
    if existing is not None:
        return existing
    row = Enrollment(user_id=user.id, exam_id=exam.id, personal_deadline=personal_deadline)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def leave_exam(session: Session, user: User, exam: Exam) -> bool:
    enrollment = get_enrollment(session, user, exam.id)
    if enrollment is None:
        return False
    session.delete(enrollment)
    session.commit()
    return True


def list_enrolled_exams(session: Session, user: User) -> list[Exam]:
    """Exams the user is preparing for: owned private exams + joined featured ones."""
    from app.models.practice import Enrollment

    return (
        session.query(Exam)
        .join(Enrollment, Enrollment.exam_id == Exam.id)
        .filter(Enrollment.user_id == user.id)
        .order_by(Exam.code)
        .all()
    )


def exam_facts(session: Session, exam: Exam) -> dict:
    """Detail-page numbers, all derived from the data model: who is preparing,
    how much content exists."""
    from app.models.practice import Enrollment
    from app.schemas.exam import ExamFacts

    syllabus_ids = [s.id for s in list_syllabi(session, exam)]
    topics_total = (
        session.query(Topic).filter(Topic.syllabus_id.in_(syllabus_ids)).count()
        if syllabus_ids
        else 0
    )
    questions_total = (
        session.query(Question).filter(Question.exam_id == exam.id).count()
    )
    return ExamFacts(
        enrolled_total=session.query(Enrollment).filter(Enrollment.exam_id == exam.id).count(),
        syllabi_total=len(syllabus_ids),
        topics_total=topics_total,
        questions_total=questions_total,
    )


def create_exam(session: Session, user: User, data: ExamCreate, auto_enroll: bool = True) -> Exam:
    visibility = _parse_visibility(data.visibility)
    if visibility == Visibility.public and not is_admin(user):
        raise ContentError("Only admins can publish featured (public) exams")
    if get_exam_by_code(session, data.code):
        raise ContentError(f"Exam code already exists: {data.code!r}")
    exam = Exam(
        code=data.code,
        name=data.name,
        level=data.level,
        country=data.country,
        issuing_body=data.issuing_body,
        description=data.description,
        user_id=user.id,
        visibility=visibility,
        pass_mark=data.pass_mark,
        exam_date=data.exam_date,
        time_allowed_seconds=data.time_allowed_seconds,
        question_count=data.question_count,
        certification_id=data.certification_id,
        voice_enabled=data.voice_enabled,
    )
    if data.certification_id is not None and session.get(Certification, data.certification_id) is None:
        raise ContentError("certification_id not found")
    session.add(exam)
    session.commit()
    session.refresh(exam)
    if auto_enroll:
        enroll_user(session, user, exam)  # owners are automatically preparing for it
    return exam


def update_exam(session: Session, user: User, exam: Exam, data: ExamUpdate) -> Exam:
    if data.visibility is not None:
        visibility = _parse_visibility(data.visibility)
        if visibility == Visibility.public and not is_admin(user):
            raise ContentError("Only admins can publish featured (public) exams")
        exam.visibility = visibility
    if data.status is not None:
        try:
            exam.status = ExamStatus(data.status)
        except ValueError:
            raise ContentError(f"Invalid status: {data.status!r}") from None
    if data.certification_id is not None:
        if session.get(Certification, data.certification_id) is None:
            raise ContentError("certification_id not found")
        exam.certification_id = data.certification_id
    for field in ("name", "level", "country", "issuing_body", "description", "pass_mark",
                    "exam_date", "time_allowed_seconds", "question_count"):
        value = getattr(data, field)
        if value is not None:
            setattr(exam, field, value)
    if data.voice_enabled is not None:  # bool: False is a real value, not absent
        exam.voice_enabled = data.voice_enabled
    session.commit()
    session.refresh(exam)
    return exam


def list_syllabi(session: Session, exam: Exam) -> list[Syllabus]:
    return (
        session.query(Syllabus)
        .filter(Syllabus.exam_id == exam.id)
        .order_by(Syllabus.version_label)
        .all()
    )


def create_syllabus(session: Session, exam: Exam, data: SyllabusCreate) -> Syllabus:
    existing = (
        session.query(Syllabus)
        .filter(Syllabus.exam_id == exam.id, Syllabus.version_label == data.version_label)
        .first()
    )
    if existing:
        raise ContentError(f"Syllabus version already exists: {data.version_label!r}")
    row = Syllabus(
        exam_id=exam.id,
        version_label=data.version_label,
        title=data.title,
        description=data.description,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        is_current=data.is_current,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_syllabus(session: Session, syllabus_id: int) -> Syllabus | None:
    return session.get(Syllabus, syllabus_id)


def list_topics(session: Session, syllabus: Syllabus) -> list[Topic]:
    return (
        session.query(Topic)
        .filter(Topic.syllabus_id == syllabus.id)
        .order_by(Topic.sort_order, Topic.id)
        .all()
    )


def upsert_topics(session: Session, syllabus: Syllabus, items: list[TopicCreate]) -> list[Topic]:
    """Bulk write by code. Entries with a matching code update, the rest create."""
    rows: list[Topic] = []
    for item in items:
        row: Topic | None = None
        if item.code:
            row = (
                session.query(Topic)
                .filter(Topic.syllabus_id == syllabus.id, Topic.code == item.code)
                .first()
            )
        if row is None:
            row = Topic(syllabus_id=syllabus.id, code=item.code)
            session.add(row)
        row.node_type = item.node_type
        row.name = item.name
        row.description = item.description
        row.parent_id = item.parent_id
        row.sort_order = item.sort_order
        row.weight = item.weight
        row.depth = item.depth
        rows.append(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ContentError("Topic upsert failed (bad parent_id or duplicate code)") from exc
    for row in rows:
        session.refresh(row)
    return rows


def get_topic(session: Session, topic_id: int) -> Topic | None:
    return session.get(Topic, topic_id)


def list_misconceptions(session: Session, topic: Topic) -> list[Misconception]:
    return (
        session.query(Misconception).filter(Misconception.topic_id == topic.id).order_by(Misconception.id).all()
    )


def create_misconception(
    session: Session, topic: Topic, data: MisconceptionCreate
) -> Misconception:
    if data.code:
        existing = (
            session.query(Misconception)
            .filter(Misconception.topic_id == topic.id, Misconception.code == data.code)
            .first()
        )
        if existing:
            raise ContentError(f"Misconception code already exists: {data.code!r}")
    row = Misconception(topic_id=topic.id, code=data.code, description=data.description)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _validate_options(question_type: str, options: list) -> None:
    if question_type == QuestionType.numeric.value:
        return
    if len(options) < 2:
        raise ContentError("Non-numeric questions need at least 2 options")
    correct = sum(1 for o in options if o.is_correct)
    if question_type in (QuestionType.single_choice.value, QuestionType.true_false.value):
        if correct != 1:
            raise ContentError("single_choice/true_false need exactly 1 correct option")
    elif correct < 1:
        raise ContentError("multi_select needs at least 1 correct option")


def create_question(session: Session, exam: Exam, data: QuestionCreate) -> Question:
    try:
        qtype = QuestionType(data.question_type)
    except ValueError:
        raise ContentError(f"Invalid question_type: {data.question_type!r}") from None
    _validate_options(qtype.value, data.options)

    syllabus: Syllabus | None = None
    if data.syllabus_id is not None:
        syllabus = session.get(Syllabus, data.syllabus_id)
        if syllabus is None or syllabus.exam_id != exam.id:
            raise ContentError("syllabus_id does not belong to this exam")

    primary: Topic | None = None
    if data.primary_topic_id is not None:
        primary = session.get(Topic, data.primary_topic_id)
        if primary is None:
            raise ContentError("primary_topic_id not found")
        if syllabus is not None and primary.syllabus_id != syllabus.id:
            raise ContentError("primary_topic_id is not in this syllabus")

    extra_topics: list[Topic] = []
    if data.topic_ids:
        extra_topics = session.query(Topic).filter(Topic.id.in_(data.topic_ids)).all()
        if len(extra_topics) != len(set(data.topic_ids)):
            raise ContentError("One or more topic_ids not found")

    question = Question(
        exam_id=exam.id,
        syllabus_id=data.syllabus_id,
        primary_topic_id=data.primary_topic_id,
        question_type=qtype,
        stem=data.stem,
        explanation=data.explanation,
    )
    session.add(question)
    session.flush()  # id for options + m2m
    for opt in data.options:
        if opt.misconception_id is not None and session.get(Misconception, opt.misconception_id) is None:
            raise ContentError("misconception_id not found")
        session.add(
            Option(
                question_id=question.id,
                content=opt.content,
                is_correct=opt.is_correct,
                misconception_id=opt.misconception_id,
                explanation=opt.explanation,
            )
        )
    if extra_topics:
        question.topics = extra_topics
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ContentError("Question create failed") from exc
    session.refresh(question)
    return question


def get_question(session: Session, question_id: int) -> Question | None:
    return (
        session.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.id == question_id)
        .first()
    )


def list_questions(
    session: Session,
    exam: Exam,
    syllabus_id: int | None = None,
    topic_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Question]:
    q = (
        session.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.exam_id == exam.id)
    )
    if syllabus_id is not None:
        q = q.filter(Question.syllabus_id == syllabus_id)
    if topic_id is not None:
        q = q.filter(
            (Question.primary_topic_id == topic_id)
            | (Question.topics.any(Topic.id == topic_id))
        )
    return q.order_by(Question.id).limit(limit).offset(offset).all()


def get_certification(session: Session, certification_id: int) -> Certification | None:
    return session.get(Certification, certification_id)


def list_certifications(session: Session) -> list[Certification]:
    return session.query(Certification).order_by(Certification.code).all()


def create_certification(session: Session, user: User, data) -> Certification:
    """Certifications structure the catalog; only admins define them."""
    if not is_admin(user):
        raise ContentError("Only admins can define certifications")
    if session.query(Certification).filter(Certification.code == data.code).first():
        raise ContentError(f"Certification code already exists: {data.code!r}")
    cert = Certification(
        code=data.code,
        name=data.name,
        issuing_body=data.issuing_body,
        level=data.level,
        country=data.country,
        description=data.description,
    )
    session.add(cert)
    session.commit()
    session.refresh(cert)
    return cert


def certification_exams(session: Session, cert: Certification) -> list[Exam]:
    return session.query(Exam).filter(Exam.certification_id == cert.id).order_by(Exam.code).all()
