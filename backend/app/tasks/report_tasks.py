"""
Background task for asynchronous report generation.
"""
import asyncio
import logging
from datetime import datetime, timezone
import uuid

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.report import Report, ReportStatus
from app.services.report_service import generate_report_content
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _async_generate_report(report_id: str, org_id: str):
    async with AsyncSessionLocal() as db:
        try:
            report_uuid = uuid.UUID(report_id)
            org_uuid = uuid.UUID(org_id)

            result = await db.execute(
                select(Report).where(Report.id == report_uuid, Report.org_id == org_uuid)
            )
            report = result.scalar_one_or_none()
            if not report:
                logger.error("Report %s not found for async generation", report_id)
                return

            report.status = ReportStatus.GENERATING
            await db.commit()

            content = await generate_report_content(report, db)

            report.content = content
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now(timezone.utc)
            report.error_message = None
            await db.commit()
            logger.info("Report %s generated successfully via Celery worker", report_id)

        except Exception as e:
            logger.exception("Failed to generate report %s asynchronously: %s", report_id, e)
            try:
                if report:
                    report.status = ReportStatus.FAILED
                    report.error_message = str(e)
                    await db.commit()
            except Exception:
                pass


@celery_app.task(name="tasks.generate_report_async", bind=True, max_retries=3)
def generate_report_async(self, report_id: str, org_id: str):
    """Executes asynchronous report generation within an async event loop."""
    logger.info("Async report task started: report_id=%s org_id=%s", report_id, org_id)
    try:
        asyncio.run(_async_generate_report(report_id, org_id))
    except Exception as exc:
        logger.error("Error in generate_report_async task: %s", exc)
        raise self.retry(exc=exc, countdown=10)
