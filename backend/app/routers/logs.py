"""
Log Ingestion Router
Accepts single and batch log submissions, parses them, scores anomalies,
and flags suspicious entries automatically.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, get_ingest_org_id, rate_limit, require_role
from app.core.websocket import ws_manager
from app.models.log_entry import LogEntry, LogSeverity
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.schemas.log_entry import LogEntryResponse, LogIngest, LogIngestBatch, LogListResponse
from app.services.log_service import ingest_log_entry, compute_anomaly_score

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=LogEntryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit)])
async def ingest_log(
    payload: LogIngest,
    org_id: UUID = Depends(get_ingest_org_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests a single log entry, parses it, and scores for anomalies.
    Supports authentication via 'X-API-Key' or JWT Bearer token.
    """
    entry = await ingest_log_entry(payload, org_id, db)

    if entry.is_flagged:
        notif = Notification(
            org_id=org_id,
            title=f"Suspicious Log: {entry.source} ({entry.log_type})",
            message=f"Anomaly score: {entry.anomaly_score:.2f} | IP: {entry.ip_src or 'unknown'}",
            severity="high" if entry.anomaly_score > 0.8 else "medium",
            link="/logs",
        )
        db.add(notif)
        await db.flush()

        await ws_manager.broadcast_to_org(
            org_id,
            {
                "type": "flagged_log",
                "log": {
                    "id": str(entry.id),
                    "source": entry.source,
                    "anomaly_score": entry.anomaly_score,
                    "ip_src": entry.ip_src,
                },
                "notification": {
                    "id": str(notif.id),
                    "title": notif.title,
                    "severity": notif.severity,
                },
            },
        )

    return entry


@router.post("/ingest/batch", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(rate_limit)])
async def ingest_log_batch(
    payload: LogIngestBatch,
    org_id: UUID = Depends(get_ingest_org_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests up to 100 log entries in a single request.
    Supports authentication via 'X-API-Key' or JWT Bearer token.
    """
    entries = []
    flagged_count = 0
    for log in payload.logs:
        entry = await ingest_log_entry(log, org_id, db)
        entries.append(entry.id)
        if entry.is_flagged:
            flagged_count += 1

    if flagged_count > 0:
        notif = Notification(
            org_id=org_id,
            title=f"Batch Ingestion: {flagged_count} Flagged Logs",
            message=f"{flagged_count} anomalous logs detected in batch of {len(payload.logs)}.",
            severity="high",
            link="/logs",
        )
        db.add(notif)
        await db.flush()

        await ws_manager.broadcast_to_org(
            org_id,
            {
                "type": "flagged_log_batch",
                "count": flagged_count,
                "notification": {
                    "id": str(notif.id),
                    "title": notif.title,
                    "severity": notif.severity,
                },
            },
        )

    return {"accepted": len(entries), "ids": [str(i) for i in entries], "flagged": flagged_count}


@router.get("", response_model=LogListResponse, dependencies=[Depends(rate_limit)])
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    is_flagged: Optional[bool] = None,
    source: Optional[str] = None,
    ip_src: Optional[str] = None,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Queries log entries with filtering. Ordered by newest first."""
    filters = [LogEntry.org_id == org_id]
    if is_flagged is not None:
        filters.append(LogEntry.is_flagged == is_flagged)
    if source:
        filters.append(LogEntry.source.ilike(f"%{source}%"))
    if ip_src:
        filters.append(LogEntry.ip_src == ip_src)

    total = (await db.execute(select(func.count()).select_from(LogEntry).where(and_(*filters)))).scalar_one()
    result = await db.execute(
        select(LogEntry)
        .where(and_(*filters))
        .order_by(LogEntry.ingested_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return LogListResponse(items=list(result.scalars().all()), total=total, page=page, page_size=page_size)


@router.get("/{log_id}", response_model=LogEntryResponse, dependencies=[Depends(rate_limit)])
async def get_log(
    log_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    from fastapi import HTTPException
    result = await db.execute(select(LogEntry).where(LogEntry.id == log_id, LogEntry.org_id == org_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found.")
    return entry
