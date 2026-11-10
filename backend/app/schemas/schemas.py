"""
Remaining Pydantic Schemas: Threats, Vulnerabilities, Assets, AI, Reports
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.threat import IndicatorType, ThreatType
from app.models.vulnerability import VulnSeverity, VulnStatus
from app.models.asset import AssetType
from app.models.report import ReportType, ReportStatus


# ───────────────────────── THREAT INDICATORS ──────────────────────────────────

class ThreatIndicatorCreate(BaseModel):
    indicator_type: IndicatorType
    value: str = Field(..., min_length=1, max_length=2048)
    threat_type: ThreatType = ThreatType.UNKNOWN
    confidence_score: float = Field(0.5, ge=0.0, le=1.0)
    source: str = Field("manual", max_length=100)
    description: Optional[str] = None
    tags: Optional[list[str]] = None


class ThreatIndicatorResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    indicator_type: IndicatorType
    value: str
    threat_type: ThreatType
    confidence_score: float
    abuse_confidence: int
    source: str
    description: Optional[str]
    country_code: Optional[str]
    asn: Optional[str]
    tags: Optional[list[str]]
    is_active: bool
    first_seen: datetime
    last_seen: datetime


class ThreatListResponse(BaseModel):
    items: list[ThreatIndicatorResponse]
    total: int
    page: int
    page_size: int


# ─────────────────────────── VULNERABILITIES ──────────────────────────────────

class VulnerabilityCreate(BaseModel):
    asset_id: Optional[UUID] = None
    cve_id: Optional[str] = Field(None, pattern=r"^CVE-\d{4}-\d{4,7}$")
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    cvss_score: float = Field(0.0, ge=0.0, le=10.0)
    severity: VulnSeverity = VulnSeverity.MEDIUM
    affected_software: Optional[str] = Field(None, max_length=500)
    affected_version: Optional[str] = Field(None, max_length=100)
    patch_available: bool = False
    patch_url: Optional[str] = Field(None, max_length=2048)
    exploit_available: bool = False
    remediation_notes: Optional[str] = None
    references: Optional[str] = None


class VulnerabilityUpdate(BaseModel):
    status: Optional[VulnStatus] = None
    remediation_notes: Optional[str] = None
    patch_available: Optional[bool] = None
    patch_url: Optional[str] = Field(None, max_length=2048)


class VulnerabilityResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    asset_id: Optional[UUID]
    cve_id: Optional[str]
    title: str
    description: str
    cvss_score: float
    severity: VulnSeverity
    status: VulnStatus
    affected_software: Optional[str]
    patch_available: bool
    exploit_available: bool
    remediation_notes: Optional[str]
    discovered_at: datetime
    updated_at: datetime


class VulnListResponse(BaseModel):
    items: list[VulnerabilityResponse]
    total: int
    page: int
    page_size: int


# ──────────────────────────────── ASSETS ──────────────────────────────────────

class AssetCreate(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255)
    ip_address: Optional[str] = Field(None, max_length=45)
    mac_address: Optional[str] = Field(None, max_length=17)
    os_type: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=100)
    asset_type: AssetType = AssetType.OTHER
    owner: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    tags: Optional[list[str]] = None
    is_internet_facing: bool = False
    notes: Optional[str] = None


class AssetUpdate(BaseModel):
    hostname: Optional[str] = Field(None, min_length=1, max_length=255)
    ip_address: Optional[str] = Field(None, max_length=45)
    os_type: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=100)
    owner: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    tags: Optional[list[str]] = None
    is_internet_facing: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class AssetResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    hostname: str
    ip_address: Optional[str]
    mac_address: Optional[str]
    os_type: Optional[str]
    os_version: Optional[str]
    asset_type: AssetType
    owner: Optional[str]
    department: Optional[str]
    tags: Optional[list[str]]
    risk_score: float
    is_internet_facing: bool
    is_active: bool
    last_seen: datetime
    created_at: datetime


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    page: int
    page_size: int


# ──────────────────────────── AI ANALYST ──────────────────────────────────────

class AIMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=8192)
    context_type: str = Field("general", max_length=50)
    context_ref_id: Optional[str] = Field(None, max_length=100)
    session_id: Optional[str] = Field(None, max_length=100)


class AIResponse(BaseModel):
    session_id: str
    message: str
    role: str = "assistant"
    timestamp: datetime
    tokens_used: Optional[int] = None


# ──────────────────────────────── REPORTS ─────────────────────────────────────

class ReportCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    report_type: ReportType = ReportType.EXECUTIVE_SUMMARY
    parameters: Optional[dict[str, Any]] = None


class ReportResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    title: str
    report_type: ReportType
    status: ReportStatus
    content: Optional[dict]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


# ──────────────────────────── DASHBOARD ───────────────────────────────────────

class DashboardStats(BaseModel):
    total_alerts: int
    open_alerts: int
    critical_alerts: int
    total_threats: int
    total_vulnerabilities: int
    open_vulnerabilities: int
    total_assets: int
    logs_last_24h: int
    flagged_logs: int
    risk_score_avg: float


class AlertTrend(BaseModel):
    date: str
    critical: int
    high: int
    medium: int
    low: int


class ThreatTypeDistribution(BaseModel):
    threat_type: str
    count: int


# ──────────────────────────── AUDIT LOGS ──────────────────────────────────────

class AuditLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


# ─────────────────────────── NOTIFICATIONS ────────────────────────────────────

class NotificationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    severity: str = Field("info", max_length=50)
    link: Optional[str] = Field(None, max_length=500)
    user_id: Optional[UUID] = None


class NotificationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    user_id: Optional[UUID] = None
    title: str
    message: str
    severity: str
    is_read: bool
    link: Optional[str] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    total: int
    page: int
    page_size: int


