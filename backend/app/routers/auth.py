"""
Authentication Router
Handles registration, login, token refresh, and logout endpoints.
All endpoints include rate limiting and input validation.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, get_current_token_payload, rate_limit
from app.schemas.auth import AuthResponse, PasswordChange, RefreshTokenRequest, TokenResponse, UserLogin, UserRegister
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter()

REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_SECURE = True   # Set False in local dev if not using HTTPS
COOKIE_SAMESITE = "strict"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Sets the refresh token as an httpOnly, Secure cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/v1/auth")


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization and admin user",
    dependencies=[Depends(rate_limit)],
)
async def register(
    payload: UserRegister,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    auth_response, refresh_token = await auth_service.register_user(payload, db, request)
    _set_refresh_cookie(response, refresh_token)
    return auth_response


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate and receive access token",
    dependencies=[Depends(rate_limit)],
)
async def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    auth_response, refresh_token = await auth_service.login_user(payload, db, redis, request)
    _set_refresh_cookie(response, refresh_token)
    return auth_response


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue new access token",
    dependencies=[Depends(rate_limit)],
)
async def refresh_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided.",
        )
    token_response, new_refresh_token = await auth_service.refresh_access_token(
        refresh_token, db, redis
    )
    _set_refresh_cookie(response, new_refresh_token)
    return token_response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current session tokens",
)
async def logout(
    request: Request,
    response: Response,
    payload: dict = Depends(get_current_token_payload),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    await auth_service.logout_user(
        access_token_jti=payload.get("jti", ""),
        user_id=payload.get("sub", ""),
        org_id=payload.get("org_id", ""),
        db=db,
        redis=redis,
        request=request,
    )
    _clear_refresh_cookie(response)
