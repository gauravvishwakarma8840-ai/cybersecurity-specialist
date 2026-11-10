"""
Assets Router — IT asset inventory management.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit, require_role
from app.models.asset import Asset, AssetType
from app.models.user import User, UserRole
from app.schemas.schemas import AssetCreate, AssetListResponse, AssetResponse, AssetUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=AssetListResponse, dependencies=[Depends(rate_limit)])
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    asset_type: Optional[AssetType] = None,
    is_active: Optional[bool] = True,
    search: Optional[str] = None,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    filters = [Asset.org_id == org_id]
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if is_active is not None:
        filters.append(Asset.is_active == is_active)
    if search:
        filters.append(Asset.hostname.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(Asset).where(and_(*filters)))).scalar_one()
    result = await db.execute(
        select(Asset)
        .where(and_(*filters))
        .order_by(Asset.risk_score.desc(), Asset.hostname)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AssetListResponse(items=list(result.scalars().all()), total=total, page=page, page_size=page_size)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit)])
async def create_asset(
    payload: AssetCreate,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    asset = Asset(org_id=org_id, **payload.model_dump())
    db.add(asset)
    await db.flush()
    logger.info("Asset created: hostname=%s type=%s", asset.hostname, asset.asset_type.value)
    return asset


@router.get("/{asset_id}", response_model=AssetResponse, dependencies=[Depends(rate_limit)])
async def get_asset(
    asset_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Asset).where(Asset.id == asset_id, Asset.org_id == org_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return asset


@router.patch("/{asset_id}", response_model=AssetResponse, dependencies=[Depends(rate_limit)])
async def update_asset(
    asset_id: UUID,
    payload: AssetUpdate,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    result = await db.execute(select(Asset).where(Asset.id == asset_id, Asset.org_id == org_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(Asset).where(Asset.id == asset_id, Asset.org_id == org_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    await db.delete(asset)
