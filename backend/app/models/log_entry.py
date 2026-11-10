"""
Log Entry ORM Model
Raw and parsed log records ingested via the HTTP endpoint.
JSONB parsed_data enables flexible querying without schema migrations for new log formats.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LogType(str, enum.Enum):
    SYSLOG = "syslog"
    AUTH = "auth"
    NETWORK = "network"
    APPLICATION = "application"
    FIREWALL = "firewall"
    WINDOWS_EVENT = "windows_event"
    OTHER = "other"


class LogSeverity(str, enum.Enum):
    EMERGENCY = "emergency"
    ALERT = "alert"
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"
    INFO = "info"
    DEBUG = "debug"


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(200), nullable=False, index=True)  # hostname or integration name
    raw_log: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    log_type: Mapped[LogType] = mapped_column(
        Enum(LogType), nullable=False, default=LogType.OTHER, index=True
    )
    severity: Mapped[LogSeverity] = mapped_column(
        Enum(LogSeverity), nullable=False, default=LogSeverity.INFO, index=True
    )
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ip_src: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    ip_dst: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    port_src: Mapped[Optional[int]] = mapped_column(nullable=True)
    port_dst: Mapped[Optional[int]] = mapped_column(nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True
    )
    log_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    alert: Mapped[Optional["Alert"]] = relationship("Alert", back_populates="log_entries")

    def __repr__(self) -> str:
        return f"<LogEntry id={self.id} source={self.source!r} flagged={self.is_flagged}>"
