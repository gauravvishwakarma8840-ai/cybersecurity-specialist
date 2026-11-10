"""
Log Entry Pydantic Schemas
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.log_entry import LogSeverity, LogType


class LogIngest(BaseModel):
    """Schema for the HTTP log ingestion endpoint. Accepts raw log strings."""
    source: str = Field(..., min_length=1, max_length=200, description="Hostname or source identifier")
    raw_log: str = Field(..., min_length=1, max_length=65536, description="Raw log string")
    log_type: LogType = LogType.OTHER
    log_timestamp: Optional[datetime] = None  # If None, ingested_at is used
    parsed_data: Optional[dict[str, Any]] = None
    ip_src: Optional[str] = Field(None, max_length=45)
    ip_dst: Optional[str] = Field(None, max_length=45)
    port_src: Optional[int] = Field(None, ge=0, le=65535)
    port_dst: Optional[int] = Field(None, ge=0, le=65535)
    user_agent: Optional[str] = Field(None, max_length=500)


class LogIngestBatch(BaseModel):
    """Batch log ingestion — up to 100 logs per request."""
    logs: list[LogIngest] = Field(..., min_length=1, max_length=100)


class LogEntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    source: str
    raw_log: str
    parsed_data: Optional[dict]
    log_type: LogType
    severity: LogSeverity
    anomaly_score: float
    ip_src: Optional[str]
    ip_dst: Optional[str]
    port_src: Optional[int]
    port_dst: Optional[int]
    is_flagged: bool
    alert_id: Optional[UUID]
    log_timestamp: datetime
    ingested_at: datetime


class LogListResponse(BaseModel):
    items: list[LogEntryResponse]
    total: int
    page: int
    page_size: int
