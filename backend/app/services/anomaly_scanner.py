import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy import select, and_

from app.core.config import settings
from app.core.database import async_session
from app.models.log_entry import LogEntry
from app.models.ai_insight import AIInsight
from app.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)


async def scan_recent_logs(hours: int = 1) -> None:
    """Scan recent WARN/ERROR logs and run AI analysis."""
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        async with async_session() as db:
            q = (
                select(LogEntry)
                .where(
                    and_(
                        LogEntry.timestamp >= since,
                        LogEntry.level.in_(["WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"]),
                    )
                )
                .order_by(LogEntry.timestamp.desc())
                .limit(500)
            )
            result = await db.execute(q)
            entries = result.scalars().all()

            if not entries:
                logger.info("Anomaly scan: no WARN/ERROR logs in last %d hour(s)", hours)
                return

            logs_data: List[dict] = [
                {
                    "timestamp": str(e.timestamp),
                    "level": e.level,
                    "host_id": e.host_id,
                    "service": e.service,
                    "message": e.message,
                }
                for e in entries
            ]

            logger.info("Anomaly scan: analyzing %d log entries", len(logs_data))
            analysis = await ai_engine.analyze_logs(logs_data)

            if not analysis.get("error"):
                insight = AIInsight(
                    insight_type="anomaly",
                    severity=analysis.get("severity", "info"),
                    title=analysis.get("title", "定时扫描结果"),
                    summary=analysis.get("summary", ""),
                    details=analysis,
                    status="new",
                )
                db.add(insight)
                await db.commit()
                logger.info("Anomaly scan: saved insight - %s", analysis.get("title"))
            else:
                logger.warning("Anomaly scan: AI analysis returned error")

    except Exception as e:
        logger.error("Anomaly scan failed: %s", str(e))


async def anomaly_scanner_loop(interval_minutes: int = 30) -> None:
    """Background loop that periodically scans for log anomalies."""
    logger.info("Anomaly scanner started (interval=%dm, enabled=%s)", interval_minutes, settings.ai_auto_scan)
    while True:
        await asyncio.sleep(interval_minutes * 60)
        if settings.ai_auto_scan:
            await scan_recent_logs(hours=1)
        else:
            logger.debug("Anomaly auto-scan is disabled, skipping")
