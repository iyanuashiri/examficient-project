from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError

from app import crud
from app.core.config import settings
from app.core.database import get_session
from app.models.user import User
from app.core.security import decode_access_token


SessionDep = Annotated[Session, Depends(get_session)]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/", auto_error=False)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        email = decode_access_token(token)
    except InvalidTokenError:
        raise credentials_exception from None

    user = crud.get_user_by_email(session, email)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
