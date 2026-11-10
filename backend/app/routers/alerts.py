"""
Alerts Router — Full CRUD with pagination, filtering, and AI summary generation.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit, require_role
from app.core.websocket import ws_manager
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.schemas.alert import AlertCreate, AlertListResponse, AlertResponse, AlertUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=AlertListResponse, dependencies=[Depends(rate_limit)])
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[AlertSeverity] = None,
    status: Optional[AlertStatus] = None,
    alert_type: Optional[str] = None,
    search: Optional[str] = None,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Lists alerts with optional filtering and pagination. Scoped to caller's organization."""
    filters = [Alert.org_id == org_id]
    if severity:
        filters.append(Alert.severity == severity)
    if status:
        filters.append(Alert.status == status)
    if alert_type:
        filters.append(Alert.alert_type == alert_type)
    if search:
        filters.append(Alert.title.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count()).select_from(Alert).where(and_(*filters)))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Alert)
        .where(and_(*filters))
        .order_by(Alert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    alerts = result.scalars().all()

    return AlertListResponse(items=list(alerts), total=total, page=page, page_size=page_size)


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit)])
async def create_alert(
    payload: AlertCreate,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    """Creates a new alert. Analysts and Admins only."""
    alert = Alert(org_id=org_id, **payload.model_dump())
    db.add(alert)
    await db.flush()

    # Automatically create a Notification
    notif = Notification(
        org_id=org_id,
        title=f"New Alert: {alert.title}",
        message=alert.description[:200] if alert.description else "A new security alert was detected.",
        severity=alert.severity.value,
        link="/alerts",
    )
    db.add(notif)
    await db.flush()

    # Broadcast event via WebSocket
    await ws_manager.broadcast_to_org(
        org_id,
        {
            "type": "new_alert",
            "alert": {
                "id": str(alert.id),
                "title": alert.title,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "risk_score": alert.risk_score,
                "alert_type": alert.alert_type,
            },
            "notification": {
                "id": str(notif.id),
                "title": notif.title,
                "severity": notif.severity,
            },
        },
    )

    logger.info("Alert created: id=%s severity=%s by user=%s", alert.id, alert.severity.value, current_user.id)
    return alert


@router.get("/{alert_id}", response_model=AlertResponse, dependencies=[Depends(rate_limit)])
async def get_alert(
    alert_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.org_id == org_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse, dependencies=[Depends(rate_limit)])
async def update_alert(
    alert_id: UUID,
    payload: AlertUpdate,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    """Updates alert fields. Resolves it if status changed to RESOLVED."""
    from datetime import datetime, timezone

    result = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.org_id == org_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    if payload.status == AlertStatus.RESOLVED and not alert.resolved_at:
        alert.resolved_at = datetime.now(timezone.utc)

    # Broadcast update via WebSocket
    await ws_manager.broadcast_to_org(
        org_id,
        {
            "type": "alert_updated",
            "alert": {
                "id": str(alert.id),
                "status": alert.status.value,
                "severity": alert.severity.value,
            },
        },
    )

    logger.info("Alert updated: id=%s by user=%s", alert.id, current_user.id)
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Deletes an alert. Admin only."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.org_id == org_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    await db.delete(alert)
    logger.info("Alert deleted: id=%s", alert_id)
