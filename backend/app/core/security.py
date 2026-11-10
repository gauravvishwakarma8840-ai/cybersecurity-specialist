"""
Security Utilities
Handles password hashing (bcrypt) and JWT creation/verification (RS256).
Refresh token rotation is enforced: every use of a refresh token issues a new one.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from jwt import PyJWTError

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Password Hashing ─────────────────────────────────────────────────────────

BCRYPT_ROUNDS = 12  # Cost factor — high enough to be secure, low enough to be fast


def hash_password(plain_password: str) -> str:
    """Hashes a plaintext password using bcrypt with a cost factor of 12."""
    if len(plain_password) < 12:
        raise ValueError("Password must be at least 12 characters long.")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ─── JWT ──────────────────────────────────────────────────────────────────────

def _get_signing_key() -> str:
    """Returns the RSA private key for signing, falling back to DEBUG placeholder."""
    key = settings.jwt_private_key
    if not key:
        logger.warning("RSA private key not found — using fallback HS256 (dev only).")
    return key or settings.model_fields.get("DEBUG", "dev-secret-key-CHANGE-ME")


def _get_verification_key() -> str:
    """Returns the RSA public key for verification."""
    key = settings.jwt_public_key
    if not key:
        logger.warning("RSA public key not found — using fallback HS256 (dev only).")
    return key or settings.model_fields.get("DEBUG", "dev-secret-key-CHANGE-ME")


def create_access_token(
    user_id: str,
    org_id: str,
    role: str,
    email: str,
) -> tuple[str, datetime]:
    """
    Creates a short-lived JWT access token (RS256).
    Returns (token_string, expiry_datetime).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "email": email,
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    private_key = settings.jwt_private_key
    algorithm = settings.JWT_ALGORITHM if private_key else "HS256"
    sign_key = private_key if private_key else "dev-secret-CHANGE-ME"

    token = jwt.encode(payload, sign_key, algorithm=algorithm)
    return token, expire


def create_refresh_token(user_id: str, org_id: str) -> tuple[str, datetime]:
    """
    Creates a long-lived refresh token.
    Refresh tokens are rotated on every use (new token issued, old invalidated).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "type": "refresh",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),  # Used for revocation checking
    }
    private_key = settings.jwt_private_key
    algorithm = settings.JWT_ALGORITHM if private_key else "HS256"
    sign_key = private_key if private_key else "dev-secret-CHANGE-ME"

    token = jwt.encode(payload, sign_key, algorithm=algorithm)
    return token, expire


def decode_token(token: str) -> Optional[dict]:
    """
    Decodes and validates a JWT token.
    Returns the payload dict on success, None on any failure.
    Does NOT check revocation — that must be done separately via Redis.
    """
    try:
        public_key = settings.jwt_public_key
        algorithm = settings.JWT_ALGORITHM if public_key else "HS256"
        verify_key = public_key if public_key else "dev-secret-CHANGE-ME"

        payload = jwt.decode(
            token,
            verify_key,
            algorithms=[algorithm],
            options={"verify_exp": True},
        )
        return payload
    except PyJWTError as e:
        logger.debug("JWT decode failed: %s", str(e))
        return None


def hash_api_key(api_key: str) -> str:
    """Hashes an API key for storage. API keys are never stored in plaintext."""
    return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verifies a submitted API key against its stored hash."""
    return bcrypt.checkpw(plain_key.encode("utf-8"), hashed_key.encode("utf-8"))
