"""
Authentication Service
Business logic for user registration, login, token refresh, and logout.
All security-sensitive operations are logged to the audit trail.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.auth import AuthResponse, OrgCreate, TokenResponse, UserLogin, UserRegister

logger = logging.getLogger(__name__)


async def _write_audit_log(
    db: AsyncSession,
    action: str,
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Appends an immutable audit entry. Failures are logged but do not break auth."""
    try:
        entry = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type="auth",
            details=details or {},
            ip_address=ip_address,
        )
        db.add(entry)
    except Exception as e:
        logger.error("Failed to write audit log: %s", e)


async def register_user(
    payload: UserRegister,
    db: AsyncSession,
    request: Optional[Request] = None,
) -> AuthResponse:
    """
    Registers a new organization and its first admin user atomically.
    Fails if the email or org slug already exists.
    """
    # Check uniqueness
    existing_user = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    existing_org = await db.execute(
        select(Organization).where(Organization.slug == payload.org.slug.lower())
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug already taken.")

    # Create organization
    org = Organization(
        name=payload.org.name,
        slug=payload.org.slug.lower(),
        plan="free",
        is_active=True,
    )
    db.add(org)
    await db.flush()  # Get org.id before creating user

    # Create first admin user
    user = User(
        org_id=org.id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ADMIN,
        is_active=True,
        last_login=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    await _write_audit_log(
        db, "user.register", org.id, user.id,
        {"email": user.email},
        ip_address=request.client.host if request and request.client else None,
    )

    access_token, expires_at = create_access_token(
        str(user.id), str(org.id), user.role.value, user.email
    )
    refresh_token, _ = create_refresh_token(str(user.id), str(org.id))

    logger.info("New user registered: %s (org=%s)", user.email, org.slug)

    return AuthResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=user,
        organization=org,
    ), refresh_token


async def login_user(
    payload: UserLogin,
    db: AsyncSession,
    redis: aioredis.Redis,
    request: Optional[Request] = None,
) -> tuple[AuthResponse, str]:
    """
    Authenticates a user by email + password.
    Applies account lockout after 5 consecutive failures (via Redis counter).
    """
    ip = request.client.host if request and request.client else "unknown"

    # Brute-force lockout check
    lockout_key = f"login_failures:{payload.email.lower()}"
    try:
        failures = await redis.get(lockout_key) if redis else None
        if failures and int(failures) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked due to too many failed login attempts. Try again in 15 minutes.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Redis unavailable for lockout check: %s", e)

    result = await db.execute(
        select(User).where(User.email == payload.email.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        # Increment failure counter with 15-min TTL
        try:
            if redis:
                await redis.incr(lockout_key)
                await redis.expire(lockout_key, 900)
        except Exception as e:
            logger.warning("Redis unavailable to record login failure: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Clear lockout on success
    try:
        if redis:
            await redis.delete(lockout_key)
    except Exception as e:
        logger.warning("Redis unavailable to clear lockout: %s", e)

    # Update last_login
    user.last_login = datetime.now(timezone.utc)

    # Fetch org
    org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = org_result.scalar_one_or_none()
    if not org or not org.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization is inactive.")

    await _write_audit_log(db, "user.login", user.org_id, user.id, {"ip": ip}, ip_address=ip)

    access_token, expires_at = create_access_token(
        str(user.id), str(org.id), user.role.value, user.email
    )
    refresh_token, _ = create_refresh_token(str(user.id), str(org.id))

    logger.info("User logged in: %s", user.email)
    return AuthResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=user,
        organization=org,
    ), refresh_token


async def refresh_access_token(
    refresh_token: str,
    db: AsyncSession,
    redis: aioredis.Redis,
) -> tuple[TokenResponse, str]:
    """
    Validates a refresh token and issues a new access token + rotated refresh token.
    Old refresh token JTI is added to the revocation set.
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    # Check if refresh token was already revoked
    jti = payload.get("jti")
    if jti:
        try:
            if redis and await redis.get(f"revoked_token:{jti}"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has been revoked.",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Redis unavailable for token revocation check: %s", e)

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id), User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Revoke the used refresh token (rotation)
    if jti:
        ttl = 60 * 60 * 24 * 7  # 7 days
        try:
            if redis:
                await redis.setex(f"revoked_token:{jti}", ttl, "1")
        except Exception as e:
            logger.warning("Redis unavailable to revoke refresh token: %s", e)

    new_access, expires_at = create_access_token(
        str(user.id), str(user.org_id), user.role.value, user.email
    )
    new_refresh, _ = create_refresh_token(str(user.id), str(user.org_id))

    return TokenResponse(access_token=new_access, expires_at=expires_at), new_refresh


async def logout_user(
    access_token_jti: str,
    user_id: str,
    org_id: str,
    db: AsyncSession,
    redis: aioredis.Redis,
    request: Optional[Request] = None,
) -> None:
    """Revokes the access token by adding its JTI to the Redis blocklist."""
    ttl = 60 * 15  # Access token TTL
    try:
        if redis:
            await redis.setex(f"revoked_token:{access_token_jti}", ttl, "1")
    except Exception as e:
        logger.warning("Redis unavailable during logout: %s", e)
    await _write_audit_log(
        db,
        "user.logout",
        uuid.UUID(org_id),
        uuid.UUID(user_id),
        ip_address=request.client.host if request and request.client else None,
    )
    logger.info("User logged out: user_id=%s", user_id)
