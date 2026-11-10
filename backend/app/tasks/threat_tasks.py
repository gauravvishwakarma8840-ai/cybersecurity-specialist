"""
Background tasks for threat intelligence feed synchronization.
Pulls recent malicious indicators and syncs them into the threat database.
"""
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.threat import IndicatorType, ThreatIndicator, ThreatType
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Curated open threat intelligence feed sources
KNOWN_FEED_URLS = [
    {
        "url": "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/3.txt",
        "type": IndicatorType.IP,
        "threat_type": ThreatType.SCANNER,
        "source": "IPsum Threat Feed",
    }
]


async def _async_sync_feeds():
    """Fetches high-confidence IOCs from open intelligence feeds and syncs them for all active orgs."""
    async with AsyncSessionLocal() as db:
        try:
            orgs_res = await db.execute(select(Organization).where(Organization.is_active == True))
            orgs = orgs_res.scalars().all()
            if not orgs:
                logger.info("No active organizations found for threat sync.")
                return

            indicators_to_add = []
            async with httpx.AsyncClient(timeout=15.0) as client:
                for feed in KNOWN_FEED_URLS:
                    try:
                        resp = await client.get(feed["url"])
                        if resp.status_code == 200:
                            lines = resp.text.splitlines()
                            # Take top 30 freshest high-risk indicators
                            valid_lines = [
                                line.strip().split()[0]
                                for line in lines
                                if line.strip() and not line.startswith("#")
                            ][:30]

                            for org in orgs:
                                for val in valid_lines:
                                    # Check if indicator already exists for this org
                                    existing = await db.execute(
                                        select(ThreatIndicator).where(
                                            ThreatIndicator.org_id == org.id,
                                            ThreatIndicator.value == val,
                                        )
                                    )
                                    if not existing.scalar_one_or_none():
                                        indicators_to_add.append(
                                            ThreatIndicator(
                                                org_id=org.id,
                                                indicator_type=feed["type"],
                                                value=val,
                                                threat_type=feed["threat_type"],
                                                confidence_score=0.85,
                                                abuse_confidence=80,
                                                source=feed["source"],
                                                description="Automated feed sync: known malicious scanner/abusive IP",
                                                is_active=True,
                                                last_seen=datetime.now(timezone.utc),
                                            )
                                        )
                    except Exception as feed_err:
                        logger.warning("Could not pull threat feed %s: %s", feed["url"], feed_err)

            if indicators_to_add:
                db.add_all(indicators_to_add)
                await db.commit()
                logger.info("Threat feed sync complete. Added %d new indicators.", len(indicators_to_add))
            else:
                logger.info("Threat feed sync complete. No new indicators added.")

        except Exception as e:
            logger.exception("Threat feed synchronization task failed: %s", e)


@celery_app.task(name="tasks.sync_threat_feeds")
def sync_threat_feeds():
    """Celery task to run threat feed sync."""
    logger.info("Starting Celery threat feed sync task...")
    try:
        asyncio.run(_async_sync_feeds())
    except Exception as exc:
        logger.error("Failed executing sync_threat_feeds: %s", exc)
