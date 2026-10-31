from fastapi import APIRouter, HTTPException, status

from app import crud
from app.api.deps import SessionDep, CurrentUserDep
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserRead)
async def create_user(user: UserCreate, session: SessionDep) -> UserRead:
    existing_user = crud.get_user_by_email(session, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(session, user)


@router.get("/me/", response_model=UserRead)
async def get_me(current_user: CurrentUserDep) -> UserRead:
    return current_user


@router.get("/{user_id}/", response_model=UserRead)
async def get_user(user_id: int, session: SessionDep, _: CurrentUserDep) -> UserRead:
    user = crud.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user