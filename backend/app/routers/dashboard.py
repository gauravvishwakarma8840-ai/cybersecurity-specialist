"""
Dashboard Router — Real-time KPI aggregations for the SOC dashboard.
"""
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.asset import Asset
from app.models.log_entry import LogEntry
from app.models.threat import ThreatIndicator
from app.models.vulnerability import Vulnerability, VulnStatus
from app.models.user import User
from app.schemas.schemas import AlertTrend, DashboardStats, ThreatTypeDistribution

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=DashboardStats, dependencies=[Depends(rate_limit)])
async def get_dashboard_stats(
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Returns aggregated KPIs for the dashboard header cards."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)

    # Alerts
    total_alerts = (await db.execute(select(func.count()).select_from(Alert).where(Alert.org_id == org_id))).scalar_one()
    open_alerts = (await db.execute(select(func.count()).select_from(Alert).where(Alert.org_id == org_id, Alert.status == AlertStatus.OPEN))).scalar_one()
    critical_alerts = (await db.execute(select(func.count()).select_from(Alert).where(Alert.org_id == org_id, Alert.severity == AlertSeverity.CRITICAL, Alert.status == AlertStatus.OPEN))).scalar_one()

    # Threats
    total_threats = (await db.execute(select(func.count()).select_from(ThreatIndicator).where(ThreatIndicator.org_id == org_id, ThreatIndicator.is_active == True))).scalar_one()

    # Vulnerabilities
    total_vulns = (await db.execute(select(func.count()).select_from(Vulnerability).where(Vulnerability.org_id == org_id))).scalar_one()
    open_vulns = (await db.execute(select(func.count()).select_from(Vulnerability).where(Vulnerability.org_id == org_id, Vulnerability.status == VulnStatus.OPEN))).scalar_one()

    # Assets
    total_assets = (await db.execute(select(func.count()).select_from(Asset).where(Asset.org_id == org_id, Asset.is_active == True))).scalar_one()

    # Logs (last 24h)
    logs_24h = (await db.execute(select(func.count()).select_from(LogEntry).where(LogEntry.org_id == org_id, LogEntry.ingested_at >= yesterday))).scalar_one()
    flagged_logs = (await db.execute(select(func.count()).select_from(LogEntry).where(LogEntry.org_id == org_id, LogEntry.is_flagged == True, LogEntry.ingested_at >= yesterday))).scalar_one()

    # Risk score average
    avg_risk = (await db.execute(select(func.avg(Alert.risk_score)).where(Alert.org_id == org_id, Alert.status == AlertStatus.OPEN))).scalar_one()

    return DashboardStats(
        total_alerts=total_alerts,
        open_alerts=open_alerts,
        critical_alerts=critical_alerts,
        total_threats=total_threats,
        total_vulnerabilities=total_vulns,
        open_vulnerabilities=open_vulns,
        total_assets=total_assets,
        logs_last_24h=logs_24h,
        flagged_logs=flagged_logs,
        risk_score_avg=round(float(avg_risk or 0), 2),
    )


@router.get("/alert-trends", response_model=list[AlertTrend], dependencies=[Depends(rate_limit)])
async def get_alert_trends(
    days: int = 7,
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Returns daily alert counts by severity for the past N days (default: 7)."""
    from sqlalchemy import cast, Date as SQLDate, Integer

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=min(days, 30))

    # Aggregate by date + severity
    result = await db.execute(
        select(
            cast(Alert.created_at, SQLDate).label("date"),
            Alert.severity,
            func.count().label("count"),
        )
        .where(Alert.org_id == org_id, Alert.created_at >= start)
        .group_by(cast(Alert.created_at, SQLDate), Alert.severity)
        .order_by(cast(Alert.created_at, SQLDate))
    )
    rows = result.all()

    # Pivot into date→severity→count map
    date_map: dict[str, dict[str, int]] = {}
    for row in rows:
        date_str = str(row.date)
        if date_str not in date_map:
            date_map[date_str] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        date_map[date_str][row.severity.value] = row.count

    return [
        AlertTrend(date=d, critical=v.get("critical", 0), high=v.get("high", 0), medium=v.get("medium", 0), low=v.get("low", 0))
        for d, v in sorted(date_map.items())
    ]


@router.get("/threat-distribution", response_model=list[ThreatTypeDistribution], dependencies=[Depends(rate_limit)])
async def get_threat_distribution(
    org_id: UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Returns IOC counts grouped by threat type."""
    result = await db.execute(
        select(ThreatIndicator.threat_type, func.count().label("count"))
        .where(ThreatIndicator.org_id == org_id, ThreatIndicator.is_active == True)
        .group_by(ThreatIndicator.threat_type)
        .order_by(func.count().desc())
    )
    return [ThreatTypeDistribution(threat_type=r.threat_type.value, count=r.count) for r in result.all()]
