from fastapi import APIRouter, HTTPException, status

from app import crud
from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.exam import CertificationCreate, CertificationDetail, CertificationRead

router = APIRouter(prefix="/certifications", tags=["Certifications"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CertificationRead)
async def create_certification(data: CertificationCreate, session: SessionDep, user: CurrentUserDep):
    try:
        return crud.create_certification(session, user, data)
    except crud.ContentError as exc:
        code = 403 if "Only admins" in str(exc) else 400
        raise HTTPException(status_code=code, detail=str(exc)) from None


@router.get("/", response_model=list[CertificationRead])
async def list_certifications(session: SessionDep, _: CurrentUserDep):
    return crud.list_certifications(session)


@router.get("/{cert_id}/", response_model=CertificationDetail)
async def get_certification(cert_id: int, session: SessionDep, user: CurrentUserDep):
    _ = user
    cert = crud.get_certification(session, cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certification not found")
    return CertificationDetail(
        **CertificationRead.model_validate(cert).model_dump(),
        exams=crud.certification_exams(session, cert),
    )
