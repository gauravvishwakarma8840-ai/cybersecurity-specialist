"""
Audit Logs Router — Immutable security audit trail queries.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org_id, rate_limit, require_role
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.schemas import AuditLogListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=AuditLogListResponse, dependencies=[Depends(rate_limit)])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[UUID] = None,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    """
    Lists audit log entries for the current organization.
    Ordered by creation time descending (most recent first).
    """
    filters = [AuditLog.org_id == org_id]
    if action:
        filters.append(AuditLog.action == action)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if user_id:
        filters.append(AuditLog.user_id == user_id)

    total = (
        await db.execute(
            select(func.count()).select_from(AuditLog).where(and_(*filters))
        )
    ).scalar_one()

    result = await db.execute(
        select(AuditLog)
        .where(and_(*filters))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(result.scalars().all())

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )

