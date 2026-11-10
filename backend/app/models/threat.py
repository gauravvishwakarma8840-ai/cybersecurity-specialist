"""
Threat Indicator ORM Model
Stores Indicators of Compromise (IOCs): IPs, domains, file hashes, URLs.
Enriched from threat intelligence feeds (AbuseIPDB, AlienVault OTX, etc.).
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndicatorType(str, enum.Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    FILE_HASH_MD5 = "hash_md5"
    FILE_HASH_SHA1 = "hash_sha1"
    FILE_HASH_SHA256 = "hash_sha256"
    EMAIL = "email"


class ThreatType(str, enum.Enum):
    MALWARE = "malware"
    PHISHING = "phishing"
    C2 = "c2"               # Command & Control
    SCANNER = "scanner"
    BOTNET = "botnet"
    RANSOMWARE = "ransomware"
    APT = "apt"
    SPAM = "spam"
    EXPLOIT = "exploit"
    UNKNOWN = "unknown"


class ThreatIndicator(Base):
    __tablename__ = "threat_indicators"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    indicator_type: Mapped[IndicatorType] = mapped_column(
        Enum(IndicatorType), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    threat_type: Mapped[ThreatType] = mapped_column(
        Enum(ThreatType), nullable=False, default=ThreatType.UNKNOWN, index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 0.0–1.0
    abuse_confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)   # AbuseIPDB 0–100
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")   # Feed name
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    asn: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<ThreatIndicator type={self.indicator_type.value!r} value={self.value!r}>"
