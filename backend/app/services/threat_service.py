"""
Threat Intelligence Service — AbuseIPDB and AlienVault OTX enrichment.
Gracefully degrades if API keys are not configured.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.threat import IndicatorType, ThreatIndicator

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 10.0  # seconds


async def enrich_indicator(indicator: ThreatIndicator, db: AsyncSession) -> None:
    """
    Enriches an IOC with external threat intelligence data.
    Supports IP enrichment via AbuseIPDB and domain enrichment via AlienVault OTX.
    Runs best-effort: failures are logged, never raised.
    """
    if indicator.indicator_type == IndicatorType.IP and settings.ABUSEIPDB_API_KEY:
        await _enrich_ip_abuseipdb(indicator)
    elif indicator.indicator_type == IndicatorType.DOMAIN and settings.ALIENVAULT_OTX_API_KEY:
        await _enrich_domain_otx(indicator)


async def _enrich_ip_abuseipdb(indicator: ThreatIndicator) -> None:
    """Queries AbuseIPDB for IP reputation data."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(
                "https://api.abuseipdb.com/api/v2/check",
                headers={
                    "Accept": "application/json",
                    "Key": settings.ABUSEIPDB_API_KEY,
                },
                params={"ipAddress": indicator.value, "maxAgeInDays": 90, "verbose": ""},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

            indicator.abuse_confidence = data.get("abuseConfidenceScore", 0)
            indicator.country_code = data.get("countryCode")
            indicator.is_active = indicator.abuse_confidence > 0

            if indicator.abuse_confidence > 50:
                indicator.confidence_score = min(1.0, indicator.abuse_confidence / 100)

            logger.info(
                "AbuseIPDB enrichment: ip=%s score=%d country=%s",
                indicator.value, indicator.abuse_confidence, indicator.country_code,
            )
    except Exception as e:
        logger.warning("AbuseIPDB enrichment failed for %s: %s", indicator.value, e)


async def _enrich_domain_otx(indicator: ThreatIndicator) -> None:
    """Queries AlienVault OTX for domain reputation data."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(
                f"https://otx.alienvault.com/api/v1/indicators/domain/{indicator.value}/general",
                headers={"X-OTX-API-KEY": settings.ALIENVAULT_OTX_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()

            pulse_count = data.get("pulse_info", {}).get("count", 0)
            if pulse_count > 0:
                indicator.confidence_score = min(1.0, pulse_count / 100)
                indicator.is_active = True

            logger.info(
                "OTX enrichment: domain=%s pulses=%d", indicator.value, pulse_count
            )
    except Exception as e:
        logger.warning("OTX enrichment failed for %s: %s", indicator.value, e)
