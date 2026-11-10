"""
Report Generation Service — Assembles report data from the database.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.asset import Asset
from app.models.log_entry import LogEntry
from app.models.report import Report
from app.models.threat import ThreatIndicator
from app.models.vulnerability import Vulnerability, VulnSeverity, VulnStatus

logger = logging.getLogger(__name__)


async def generate_report_content(report: Report, db: AsyncSession) -> dict:
    """
    Generates report content based on report type.
    Returns a structured dict that is stored as JSONB.
    """
    org_id = report.org_id
    now = datetime.now(timezone.utc)
    params = report.parameters or {}
    days = params.get("days", 30)
    since = now - timedelta(days=days)

    content = {
        "generated_at": now.isoformat(),
        "report_type": report.report_type.value,
        "period_days": days,
        "sections": {},
    }

    # ─── Alert Summary ─────────────────────────────────────────────────────────
    alert_counts = {}
    for severity in AlertSeverity:
        count = (await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.org_id == org_id,
                Alert.severity == severity,
                Alert.created_at >= since,
            )
        )).scalar_one()
        alert_counts[severity.value] = count

    resolved = (await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.org_id == org_id,
            Alert.status == AlertStatus.RESOLVED,
            Alert.created_at >= since,
        )
    )).scalar_one()

    content["sections"]["alerts"] = {
        "by_severity": alert_counts,
        "resolved": resolved,
        "total": sum(alert_counts.values()),
    }

    # ─── Vulnerability Summary ─────────────────────────────────────────────────
    vuln_counts = {}
    for severity in VulnSeverity:
        count = (await db.execute(
            select(func.count()).select_from(Vulnerability).where(
                Vulnerability.org_id == org_id,
                Vulnerability.severity == severity,
            )
        )).scalar_one()
        vuln_counts[severity.value] = count

    content["sections"]["vulnerabilities"] = {
        "by_severity": vuln_counts,
        "open": (await db.execute(
            select(func.count()).select_from(Vulnerability).where(
                Vulnerability.org_id == org_id,
                Vulnerability.status == VulnStatus.OPEN,
            )
        )).scalar_one(),
    }

    # ─── Asset Summary ─────────────────────────────────────────────────────────
    total_assets = (await db.execute(
        select(func.count()).select_from(Asset).where(Asset.org_id == org_id, Asset.is_active == True)
    )).scalar_one()
    internet_facing = (await db.execute(
        select(func.count()).select_from(Asset).where(
            Asset.org_id == org_id, Asset.is_active == True, Asset.is_internet_facing == True
        )
    )).scalar_one()

    content["sections"]["assets"] = {
        "total": total_assets,
        "internet_facing": internet_facing,
    }

    # ─── Threat Intel Summary ──────────────────────────────────────────────────
    total_iocs = (await db.execute(
        select(func.count()).select_from(ThreatIndicator).where(
            ThreatIndicator.org_id == org_id, ThreatIndicator.is_active == True
        )
    )).scalar_one()

    content["sections"]["threat_intelligence"] = {"active_iocs": total_iocs}

    # ─── Log Summary ───────────────────────────────────────────────────────────
    total_logs = (await db.execute(
        select(func.count()).select_from(LogEntry).where(
            LogEntry.org_id == org_id, LogEntry.ingested_at >= since
        )
    )).scalar_one()
    flagged_logs = (await db.execute(
        select(func.count()).select_from(LogEntry).where(
            LogEntry.org_id == org_id, LogEntry.is_flagged == True, LogEntry.ingested_at >= since
        )
    )).scalar_one()

    content["sections"]["logs"] = {
        "total": total_logs,
        "flagged": flagged_logs,
        "flag_rate": round(flagged_logs / total_logs * 100, 2) if total_logs else 0,
    }

    return content
