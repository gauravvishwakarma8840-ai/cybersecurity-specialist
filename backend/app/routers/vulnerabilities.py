"""
Vulnerabilities Router — CVE tracking and risk management.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit, require_role
from app.models.vulnerability import Vulnerability, VulnSeverity, VulnStatus
from app.models.user import User, UserRole
from app.schemas.schemas import VulnerabilityCreate, VulnerabilityResponse, VulnerabilityUpdate, VulnListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=VulnListResponse, dependencies=[Depends(rate_limit)])
async def list_vulnerabilities(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    severity: Optional[VulnSeverity] = None,
    status: Optional[VulnStatus] = None,
    asset_id: Optional[UUID] = None,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    filters = [Vulnerability.org_id == org_id]
    if severity:
        filters.append(Vulnerability.severity == severity)
    if status:
        filters.append(Vulnerability.status == status)
    if asset_id:
        filters.append(Vulnerability.asset_id == asset_id)

    total = (await db.execute(select(func.count()).select_from(Vulnerability).where(and_(*filters)))).scalar_one()
    result = await db.execute(
        select(Vulnerability)
        .where(and_(*filters))
        .order_by(Vulnerability.cvss_score.desc(), Vulnerability.discovered_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return VulnListResponse(items=list(result.scalars().all()), total=total, page=page, page_size=page_size)


@router.post("", response_model=VulnerabilityResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit)])
async def create_vulnerability(
    payload: VulnerabilityCreate,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    vuln = Vulnerability(org_id=org_id, **payload.model_dump())
    db.add(vuln)
    await db.flush()
    logger.info("Vulnerability created: cve=%s severity=%s", vuln.cve_id, vuln.severity.value)
    return vuln


@router.get("/{vuln_id}", response_model=VulnerabilityResponse, dependencies=[Depends(rate_limit)])
async def get_vulnerability(
    vuln_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id, Vulnerability.org_id == org_id))
    vuln = result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found.")
    return vuln


@router.patch("/{vuln_id}", response_model=VulnerabilityResponse, dependencies=[Depends(rate_limit)])
async def update_vulnerability(
    vuln_id: UUID,
    payload: VulnerabilityUpdate,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    from datetime import datetime, timezone
    result = await db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id, Vulnerability.org_id == org_id))
    vuln = result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vuln, field, value)

    if payload.status == VulnStatus.MITIGATED and not vuln.mitigated_at:
        vuln.mitigated_at = datetime.now(timezone.utc)

    return vuln


@router.delete("/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vulnerability(
    vuln_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id, Vulnerability.org_id == org_id))
    vuln = result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found.")
    await db.delete(vuln)

