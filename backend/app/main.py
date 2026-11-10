"""
FastAPI Application Entry Point
Configures middleware, CORS, routers, exception handlers, and startup events.
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logger import setup_logging
from app.routers import (
    auth,
    dashboard,
    alerts,
    logs,
    threats,
    vulnerabilities,
    assets,
    ai_analyst,
    reports,
    audit_logs,
    notifications,
    ws,
    settings as settings_router,
)

# ─── Logging Setup ─────────────────────────────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ─── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs startup tasks, then cleanup on shutdown."""
    logger.info("Starting CyberSentinel AI backend...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")
    logger.info(f"CyberSentinel AI v{settings.APP_VERSION} started — ENV={settings.APP_ENV}")
    yield
    logger.info("Shutting down CyberSentinel AI...")
    await engine.dispose()


# ─── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade AI-powered cybersecurity SaaS platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─── Middleware ────────────────────────────────────────────────────────────────

# GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS — allowlist only; never wildcard in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Org-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)


@app.middleware("http")
async def request_id_and_timing_middleware(request: Request, call_next):
    """Attaches a unique request ID and logs request timing for every HTTP call."""
    import uuid
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"

    logger.info(
        "HTTP %s %s → %s [%.2fms] req_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


# ─── Exception Handlers ────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Returns structured 422 errors with field-level details."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "One or more fields failed validation.",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches unhandled exceptions; never leaks stack traces to the client."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# ─── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"], include_in_schema=False)
async def health_check():
    """Lightweight health probe for Docker / load balancer."""
    return {"status": "healthy", "version": settings.APP_VERSION}


# ─── API Routers ───────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router,            prefix=f"{API_PREFIX}/auth",            tags=["Authentication"])
app.include_router(dashboard.router,       prefix=f"{API_PREFIX}/dashboard",       tags=["Dashboard"])
app.include_router(alerts.router,          prefix=f"{API_PREFIX}/alerts",          tags=["Alerts"])
app.include_router(logs.router,            prefix=f"{API_PREFIX}/logs",            tags=["Log Ingestion"])
app.include_router(threats.router,         prefix=f"{API_PREFIX}/threats",         tags=["Threat Intelligence"])
app.include_router(vulnerabilities.router, prefix=f"{API_PREFIX}/vulnerabilities", tags=["Vulnerabilities"])
app.include_router(assets.router,          prefix=f"{API_PREFIX}/assets",          tags=["Assets"])
app.include_router(ai_analyst.router,      prefix=f"{API_PREFIX}/ai",              tags=["AI Analyst"])
app.include_router(reports.router,         prefix=f"{API_PREFIX}/reports",         tags=["Reports"])
app.include_router(audit_logs.router,       prefix=f"{API_PREFIX}/audit-logs",      tags=["Audit Logs"])
app.include_router(notifications.router,    prefix=f"{API_PREFIX}/notifications",   tags=["Notifications"])
app.include_router(ws.router,               prefix=f"{API_PREFIX}/ws",              tags=["WebSockets"])
app.include_router(settings_router.router, prefix=f"{API_PREFIX}/settings",        tags=["Settings"])
