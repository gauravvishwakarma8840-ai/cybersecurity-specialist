"""
FastAPI Dependency Injection
Provides reusable dependencies for authentication, authorization,
database access, Redis, and rate limiting.
"""
import logging
from typing import Optional
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# ─── HTTP Bearer Token Scheme ─────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Redis Client ─────────────────────────────────────────────────────────────
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Returns a Redis client. Lazily initialized as a singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


# ─── Rate Limiter ─────────────────────────────────────────────────────────────
async def rate_limit(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    """
    Redis sliding-window rate limiter.
    Limits each client IP to RATE_LIMIT_PER_MINUTE requests per minute.
    Gracefully degrades if Redis is unavailable in local dev.
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client_ip}"

    import time
    now = int(time.time())
    window_start = now - 60  # 1-minute window

    try:
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        request_count = results[2]

        if request_count > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Redis rate limiter unavailable (local dev fallback): %s", e)


# ─── Token Extraction ─────────────────────────────────────────────────────────
async def get_current_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    """
    Extracts and validates the JWT from the Authorization header.
    Also checks Redis to see if the token has been explicitly revoked (logout).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    # Check token revocation via Redis blocklist (graceful fallback if Redis offline)
    jti = payload.get("jti")
    if jti:
        try:
            if await redis.get(f"revoked_token:{jti}"):
                raise credentials_exception
        except HTTPException:
            raise
        except Exception:
            pass

    return payload


# ─── Current User ─────────────────────────────────────────────────────────────
async def get_current_user(
    payload: dict = Depends(get_current_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the current authenticated user from the JWT payload.
    Raises 401 if the user is not found or is inactive.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    result = await db.execute(select(User).where(User.id == UUID(user_id), User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures the user account is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")
    return current_user


# ─── Role-Based Access Control ────────────────────────────────────────────────
def require_role(*roles: UserRole):
    """
    Dependency factory that restricts access to users with specific roles.
    Usage: Depends(require_role(UserRole.ADMIN, UserRole.ANALYST))
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return role_checker


# ─── Org-Scoped Dependencies ──────────────────────────────────────────────────
async def get_current_org_id(
    current_user: User = Depends(get_current_active_user),
) -> UUID:
    """Extracts the organization ID from the current user — used to enforce multi-tenancy."""
    return current_user.org_id


async def get_ingest_org_id(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UUID:
    """
    Resolves the organization ID for log ingestion via either:
    1. 'X-API-Key' header (for automated log shippers, curl, agents)
    2. 'Authorization: Bearer <token>' (for dashboard users)
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        from app.models.organization import Organization
        from app.core.security import verify_api_key

        result = await db.execute(
            select(Organization).where(Organization.is_active == True, Organization.api_key_hash != None)
        )
        for org in result.scalars().all():
            if org.api_key_hash and verify_api_key(api_key, org.api_key_hash):
                return org.id

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
        )

    if credentials:
        payload = decode_token(credentials.credentials)
        if payload and payload.get("type") == "access":
            org_id_str = payload.get("org_id")
            if org_id_str:
                return UUID(org_id_str)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide 'X-API-Key' or 'Authorization: Bearer <token>'.",
    )
