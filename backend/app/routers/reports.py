"""
Reports Router — Generate on-demand security reports.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit, require_role
from app.models.report import Report, ReportStatus
from app.models.user import User, UserRole
from app.schemas.schemas import ReportCreate, ReportResponse
from app.services.report_service import generate_report_content

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit)])
async def create_report(
    payload: ReportCreate,
    async_generation: bool = False,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Creates and generates a security report (synchronous or queued via Celery)."""
    report = Report(
        org_id=org_id,
        created_by=current_user.id,
        title=payload.title,
        report_type=payload.report_type,
        parameters=payload.parameters or {},
        status=ReportStatus.GENERATING,
    )
    db.add(report)
    await db.flush()

    if async_generation:
        try:
            from app.tasks.report_tasks import generate_report_async
            generate_report_async.delay(str(report.id), str(org_id))
            return report
        except Exception as e:
            logger.warning("Could not queue Celery task, falling back to sync: %s", e)

    # Generate report content synchronously
    try:
        content = await generate_report_content(report, db)
        report.content = content
        report.status = ReportStatus.COMPLETED
        from datetime import datetime, timezone
        report.completed_at = datetime.now(timezone.utc)
    except Exception as e:
        logger.error("Report generation failed: %s", e)
        report.status = ReportStatus.FAILED
        report.error_message = str(e)

    return report


@router.get("", response_model=list[ReportResponse], dependencies=[Depends(rate_limit)])
async def list_reports(
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Report)
        .where(Report.org_id == org_id)
        .order_by(Report.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


@router.get("/{report_id}", response_model=ReportResponse, dependencies=[Depends(rate_limit)])
async def get_report(
    report_id: UUID,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Report).where(Report.id == report_id, Report.org_id == org_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report
