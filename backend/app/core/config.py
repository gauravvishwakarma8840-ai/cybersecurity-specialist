"""
Application Configuration
All settings are loaded from environment variables via pydantic-settings.
This ensures secrets are never hardcoded and configuration is environment-driven.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "CyberSentinel AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ─── Backend ──────────────────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except Exception:
                pass
            return [origin.strip().strip("[]\"'") for origin in v.split(",") if origin.strip()]
        return v

    # ─── JWT ──────────────────────────────────────────────────────────────────
    JWT_PRIVATE_KEY_PATH: str = "./certs/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "./certs/public.pem"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "RS256"

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://cybersentinel_user:password@localhost:5432/cybersentinel"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20
    POSTGRES_POOL_TIMEOUT: int = 30

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ─── AI / Gemini ──────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # ─── Threat Intelligence Feeds ────────────────────────────────────────────
    ABUSEIPDB_API_KEY: str = ""
    ALIENVAULT_OTX_API_KEY: str = ""

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 20

    # ─── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def jwt_private_key(self) -> str:
        """Reads RSA private key from disk; cached after first read."""
        try:
            with open(self.JWT_PRIVATE_KEY_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            # Fall back to a dev-only HS256 secret if certs don't exist
            return ""

    @property
    def jwt_public_key(self) -> str:
        """Reads RSA public key from disk."""
        try:
            with open(self.JWT_PUBLIC_KEY_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            return ""


@lru_cache
def get_settings() -> Settings:
    """Returns a cached singleton Settings instance."""
    return Settings()


settings = get_settings()
