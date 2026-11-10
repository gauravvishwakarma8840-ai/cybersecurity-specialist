"""
Alert Pydantic Schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.alert import AlertSeverity, AlertStatus


class AlertCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    severity: AlertSeverity = AlertSeverity.MEDIUM
    alert_type: str = Field(..., min_length=1, max_length=100)
    source_ip: Optional[str] = Field(None, max_length=45)
    dest_ip: Optional[str] = Field(None, max_length=45)
    source_port: Optional[int] = Field(None, ge=0, le=65535)
    dest_port: Optional[int] = Field(None, ge=0, le=65535)
    mitre_tactic: Optional[str] = Field(None, max_length=100)
    mitre_technique: Optional[str] = Field(None, max_length=100)
    risk_score: float = Field(0.0, ge=0.0, le=100.0)


class AlertUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    assigned_to: Optional[UUID] = None
    false_positive_reason: Optional[str] = None
    mitre_tactic: Optional[str] = Field(None, max_length=100)
    mitre_technique: Optional[str] = Field(None, max_length=100)


class AlertResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    alert_type: str
    source_ip: Optional[str]
    dest_ip: Optional[str]
    source_port: Optional[int]
    dest_port: Optional[int]
    mitre_tactic: Optional[str]
    mitre_technique: Optional[str]
    risk_score: float
    ai_summary: Optional[str]
    assigned_to: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
