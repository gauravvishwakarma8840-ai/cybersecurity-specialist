"""
Threat Intelligence Router — IOC management and enrichment.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit, require_role
from app.models.threat import IndicatorType, ThreatIndicator
from app.models.user import User, UserRole
from app.schemas.schemas import ThreatIndicatorCreate, ThreatIndicatorResponse, ThreatListResponse
from app.services.threat_service import enrich_indicator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ThreatListResponse, dependencies=[Depends(rate_limit)])
async def list_threats(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    indicator_type: Optional[IndicatorType] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = True,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    filters = [ThreatIndicator.org_id == org_id]
    if indicator_type:
        filters.append(ThreatIndicator.indicator_type == indicator_type)
    if is_active is not None:
        filters.append(ThreatIndicator.is_active == is_active)
    if search:
        filters.append(ThreatIndicator.value.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(ThreatIndicator).where(and_(*filters)))).scalar_one()
    result = await db.execute(
        select(ThreatIndicator)
        .where(and_(*filters))
        .order_by(ThreatIndicator.last_seen.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ThreatListResponse(items=list(result.scalars().all()), total=total, page=page, page_size=page_size)


@router.post("", response_model=ThreatIndicatorResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit)])
async def create_threat_indicator(
    payload: ThreatIndicatorCreate,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    """Creates a new IOC. Automatically enriches IP/domain indicators if API keys are configured."""
    indicator = ThreatIndicator(org_id=org_id, **payload.model_dump())
    db.add(indicator)
    await db.flush()

    # Fire enrichment asynchronously (doesn't block response)
    try:
        await enrich_indicator(indicator, db)
    except Exception as e:
        logger.warning("Enrichment failed for indicator %s: %s", indicator.value, e)

    return indicator


@router.get("/lookup", response_model=ThreatIndicatorResponse | None, dependencies=[Depends(rate_limit)])
async def lookup_indicator(
    value: str = Query(..., min_length=1, max_length=2048),
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Looks up an exact IOC value."""
    result = await db.execute(
        select(ThreatIndicator).where(ThreatIndicator.org_id == org_id, ThreatIndicator.value == value)
    )
    return result.scalar_one_or_none()


@router.delete("/{indicator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_indicator(
    indicator_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(ThreatIndicator).where(ThreatIndicator.id == indicator_id, ThreatIndicator.org_id == org_id))
    indicator = result.scalar_one_or_none()
    if not indicator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found.")
    await db.delete(indicator)
