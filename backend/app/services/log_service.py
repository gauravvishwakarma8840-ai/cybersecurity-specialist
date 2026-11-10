"""
Log Service — Parsing and Anomaly Scoring
Applies lightweight heuristic anomaly scoring to ingested log entries.
A score > 0.7 flags the entry for analyst review.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry, LogSeverity
from app.schemas.log_entry import LogIngest

logger = logging.getLogger(__name__)

# ─── Heuristic Anomaly Patterns ────────────────────────────────────────────────
# Each pattern adds to the anomaly score. Max realistic score is ~1.0.
ANOMALY_PATTERNS: list[tuple[re.Pattern, float, str]] = [
    (re.compile(r"failed\s+password", re.IGNORECASE), 0.25, "failed_auth"),
    (re.compile(r"authentication\s+failure", re.IGNORECASE), 0.30, "auth_failure"),
    (re.compile(r"invalid\s+user", re.IGNORECASE), 0.20, "invalid_user"),
    (re.compile(r"root\s+login", re.IGNORECASE), 0.35, "root_login"),
    (re.compile(r"sudo\s*:", re.IGNORECASE), 0.15, "sudo_usage"),
    (re.compile(r"sql\s*injection|union\s+select|'\s*or\s+'1", re.IGNORECASE), 0.50, "sqli"),
    (re.compile(r"<script[\s>]|javascript:|onerror=", re.IGNORECASE), 0.45, "xss"),
    (re.compile(r"\/etc\/passwd|\/etc\/shadow|\/proc\/", re.IGNORECASE), 0.40, "path_traversal"),
    (re.compile(r"\.\.\/|\.\.\\", re.IGNORECASE), 0.30, "directory_traversal"),
    (re.compile(r"nmap|masscan|nikto|sqlmap|hydra|metasploit", re.IGNORECASE), 0.55, "scanner_tool"),
    (re.compile(r"port\s+scan|port\s+sweep", re.IGNORECASE), 0.40, "port_scan"),
    (re.compile(r"denied|forbidden|unauthorized", re.IGNORECASE), 0.10, "access_denied"),
    (re.compile(r"ransomware|encrypt.*files|\.locky|\.wcry", re.IGNORECASE), 0.80, "ransomware"),
    (re.compile(r"cmd\.exe|powershell.*-enc|base64.*decode", re.IGNORECASE), 0.40, "cmd_execution"),
    (re.compile(r"wget\s+http|curl\s+http.*\|\s*bash", re.IGNORECASE), 0.45, "remote_code_exec"),
]

SEVERITY_FROM_SCORE = {
    (0.70, 1.01): LogSeverity.CRITICAL,
    (0.50, 0.70): LogSeverity.ERROR,
    (0.30, 0.50): LogSeverity.WARNING,
    (0.10, 0.30): LogSeverity.NOTICE,
    (0.00, 0.10): LogSeverity.INFO,
}


def compute_anomaly_score(raw_log: str) -> tuple[float, LogSeverity, list[str]]:
    """
    Scores a raw log string for anomaly indicators.
    Returns (score [0–1], severity, list of triggered rule names).
    """
    score = 0.0
    triggered = []

    for pattern, weight, label in ANOMALY_PATTERNS:
        if pattern.search(raw_log):
            score = min(1.0, score + weight)
            triggered.append(label)

    # Clamp to [0, 1]
    score = round(min(score, 1.0), 4)

    severity = LogSeverity.INFO
    for (lo, hi), sev in SEVERITY_FROM_SCORE.items():
        if lo <= score < hi:
            severity = sev
            break

    return score, severity, triggered


def _parse_log(raw_log: str, existing_parsed: Optional[dict]) -> dict:
    """
    Attempts lightweight parsing of common log formats.
    Returns a dict of extracted fields or the existing parsed dict.
    """
    if existing_parsed:
        return existing_parsed

    parsed: dict = {"raw": raw_log[:500]}

    # Try to extract common syslog fields (timestamp, hostname, process)
    syslog_pattern = re.compile(
        r"(?P<month>\w{3})\s+(?P<day>\d+)\s+(?P<time>[\d:]+)\s+(?P<host>\S+)\s+(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?\s*:\s*(?P<message>.*)",
        re.DOTALL,
    )
    match = syslog_pattern.match(raw_log)
    if match:
        parsed.update({k: v for k, v in match.groupdict().items() if v is not None})
        return parsed

    # Try to extract HTTP access log fields
    http_pattern = re.compile(
        r'(?P<ip>[\d.]+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\w+)\s+(?P<uri>\S+)\s+\S+"\s+(?P<status>\d+)\s+(?P<size>\d+)',
    )
    match = http_pattern.match(raw_log)
    if match:
        parsed.update(match.groupdict())

    return parsed


async def ingest_log_entry(
    payload: LogIngest,
    org_id: UUID,
    db: AsyncSession,
) -> LogEntry:
    """
    Parses, scores, and persists a log entry.
    Entries with anomaly_score >= 0.7 are automatically flagged for analyst review.
    """
    anomaly_score, severity, triggered_rules = compute_anomaly_score(payload.raw_log)
    parsed_data = _parse_log(payload.raw_log, payload.parsed_data)

    if triggered_rules:
        parsed_data["_anomaly_rules"] = triggered_rules

    is_flagged = anomaly_score >= 0.70
    log_ts = payload.log_timestamp or datetime.now(timezone.utc)

    entry = LogEntry(
        org_id=org_id,
        source=payload.source,
        raw_log=payload.raw_log,
        parsed_data=parsed_data,
        log_type=payload.log_type,
        severity=severity,
        anomaly_score=anomaly_score,
        ip_src=payload.ip_src,
        ip_dst=payload.ip_dst,
        port_src=payload.port_src,
        port_dst=payload.port_dst,
        user_agent=payload.user_agent,
        is_flagged=is_flagged,
        log_timestamp=log_ts,
    )
    db.add(entry)
    await db.flush()

    if is_flagged:
        logger.warning(
            "High anomaly log flagged: id=%s score=%.2f rules=%s source=%s",
            entry.id, anomaly_score, triggered_rules, payload.source,
        )

    return entry
