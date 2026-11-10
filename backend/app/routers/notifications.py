"""
Notifications Router — User & Organization notification management.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit
from app.models.notification import Notification
from app.models.user import User
from app.schemas.schemas import NotificationListResponse, NotificationResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=NotificationListResponse, dependencies=[Depends(rate_limit)])
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    unread_only: bool = False,
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists notifications for the current user/organization."""
    filters = [
        Notification.org_id == org_id,
        (Notification.user_id == current_user.id) | (Notification.user_id == None),
    ]
    if unread_only:
        filters.append(Notification.is_read == False)

    total = (
        await db.execute(
            select(func.count()).select_from(Notification).where(and_(*filters))
        )
    ).scalar_one()

    unread_count = (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.org_id == org_id,
                    (Notification.user_id == current_user.id) | (Notification.user_id == None),
                    Notification.is_read == False,
                )
            )
        )
    ).scalar_one()

    result = await db.execute(
        select(Notification)
        .where(and_(*filters))
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(result.scalars().all())

    return NotificationListResponse(
        items=items,
        unread_count=unread_count,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Marks a single notification as read."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.org_id == org_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    notif.is_read = True
    return notif


@router.post("/mark-all-read", status_code=status.HTTP_200_OK)
async def mark_all_as_read(
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Marks all notifications for this user/org as read."""
    await db.execute(
        update(Notification)
        .where(
            Notification.org_id == org_id,
            (Notification.user_id == current_user.id) | (Notification.user_id == None),
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    return {"message": "All notifications marked as read."}

