from uuid import UUID

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.db.session import get_database_session
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest
from app.schemas.user import UserRegister, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_refresh_cookie(response: Response, user_id: UUID) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=create_refresh_token(user_id),
        max_age=settings.refresh_cookie_max_age,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path=f"{settings.api_v1_prefix}/auth",
    )


def build_access_token(user_id: UUID) -> AccessTokenResponse:
    return AccessTokenResponse(access_token=create_access_token(user_id))


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    registration: UserRegister,
    session: AsyncSession = Depends(get_database_session),
) -> User:
    existing_user = await session.scalar(
        select(User).where(User.email == registration.email)
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=registration.name,
        email=registration.email,
        password_hash=hash_password(registration.password),
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    await session.refresh(user)
    return user


@router.post("/login", response_model=AccessTokenResponse)
async def login(
    login_request: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_database_session),
) -> AccessTokenResponse:
    user = await session.scalar(
        select(User).where(User.email == login_request.email)
    )
    if user is None or not verify_password(
        login_request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    set_refresh_cookie(response, user.user_id)
    return build_access_token(user.user_id)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_tokens(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    session: AsyncSession = Depends(get_database_session),
) -> AccessTokenResponse:
    try:
        if refresh_token is None:
            raise ValueError("A refresh-token cookie is required.")
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("A refresh token is required.")
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Rotate the cookie whenever it is used successfully.
    set_refresh_cookie(response, user.user_id)
    return build_access_token(user.user_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=f"{settings.api_v1_prefix}/auth",
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )
