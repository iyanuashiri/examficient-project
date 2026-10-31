import secrets
from datetime import datetime, timedelta, timezone
from typing import Union, Annotated
from typing_extensions import Doc

from fastapi.param_functions import Form
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from pwdlib import PasswordHash
from jwt.exceptions import InvalidTokenError

from app.core.config import settings


password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    expire_minutes = expires_minutes or settings.access_token_expire_minutes
    
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidTokenError("Missing token subject")
    return subject


class OAuth2PasswordNewRequestForm(OAuth2PasswordRequestForm):
    def __init__(self,
                 *,
                 grant_type: Annotated[
                     Union[str, None],
                     Form(pattern="password"),
                     Doc(
                         """
                         The OAuth2 spec says it is required and MUST be the fixed string
                         "password". Nevertheless, this dependency class is permissive and
                         allows not passing it. If you want to enforce it, use instead the
                         `OAuth2PasswordRequestFormStrict` dependency.
                         """
                     ),
                 ] = None,
                 email: Annotated[
                     str,
                     Form(),
                     Doc(
                         """
                         `email` string. The OAuth2 spec requires the exact field name
                         `email`.
                         """
                     ),
                 ],
                 password: Annotated[
                     str,
                     Form(),
                     Doc(
                         """
                         `password` string. The OAuth2 spec requires the exact field name
                         `password".
                         """
                     ),
                 ],
                 scope: Annotated[
                     str,
                     Form(),
                     Doc(
                         """
                         A single string with actually several scopes separated by spaces. Each
                         scope is also a string.
     
                         For example, a single string with:
     
                         ```python
                         "items:read items:write users:read profile openid"
                         ````
     
                         would represent the scopes:
     
                         * `items:read`
                         * `items:write`
                         * `users:read`
                         * `profile`
                         * `openid`
                         """
                     ),
                 ] = "",
                 client_id: Annotated[
                     Union[str, None],
                     Form(),
                     Doc(
                         """
                         If there's a `client_id`, it can be sent as part of the form fields.
                         But the OAuth2 specification recommends sending the `client_id` and
                         `client_secret` (if any) using HTTP Basic auth.
                         """
                     ),
                 ] = None,
                 client_secret: Annotated[
                     Union[str, None],
                     Form(),
                     Doc(
                         """
                         If there's a `client_password` (and a `client_id`), they can be sent
                         as part of the form fields. But the OAuth2 specification recommends
                         sending the `client_id` and `client_secret` (if any) using HTTP Basic
                         auth.
                         """
                     ),
                 ] = None,
                 ):
        self.grant_type = grant_type
        self.email = email
        self.password = password
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret    