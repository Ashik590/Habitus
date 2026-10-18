from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_database_session
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def authentication_error(detail: str = "Could not validate credentials.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise authentication_error("Authentication is required.")

    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise authentication_error("An access token is required.")
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise authentication_error() from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise authentication_error("User is inactive or no longer exists.")

    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
) -> User | None:
    if credentials is None:
        return None

    if credentials.scheme.lower() != "bearer":
        raise authentication_error()

    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise authentication_error("An access token is required.")
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise authentication_error() from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise authentication_error("User is inactive or no longer exists.")

    return user
