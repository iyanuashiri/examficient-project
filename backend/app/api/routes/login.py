from fastapi import APIRouter, Depends, HTTPException, status

from app import crud
from app.core.security import OAuth2PasswordNewRequestForm
from app.api.deps import SessionDep
from app.core.security import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login/", status_code=status.HTTP_200_OK)
async def login(session: SessionDep, data: OAuth2PasswordNewRequestForm = Depends()):
    user = crud.get_user_by_email(session, data.email)

    if user is None or not user.is_active or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user.email),
        "token_type": "bearer",
    }