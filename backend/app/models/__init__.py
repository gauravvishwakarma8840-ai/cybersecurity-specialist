"""
Models package — imports all ORM models to ensure they are registered
with SQLAlchemy's metadata before Alembic or create_all is called.
"""
from app.models.organization import Organization
from app.models.user import User
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.log_entry import LogEntry, LogType, LogSeverity
from app.models.threat import ThreatIndicator, IndicatorType, ThreatType
from app.models.asset import Asset, AssetType
from app.models.vulnerability import Vulnerability, VulnSeverity, VulnStatus
from app.models.report import Report, ReportType, ReportStatus
from app.models.audit_log import AuditLog
from app.models.ai_conversation import AIConversation
from app.models.notification import Notification

__all__ = [
    "Organization",
    "User", "UserRole",
    "Alert", "AlertSeverity", "AlertStatus",
    "LogEntry", "LogType", "LogSeverity",
    "ThreatIndicator", "IndicatorType", "ThreatType",
    "Asset", "AssetType",
    "Vulnerability", "VulnSeverity", "VulnStatus",
    "Report", "ReportType", "ReportStatus",
    "AuditLog",
    "AIConversation",
    "Notification",
]
