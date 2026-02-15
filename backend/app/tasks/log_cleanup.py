import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete

from app.core.database import async_session
from app.models.log_entry import LogEntry

logger = logging.getLogger(__name__)


async def log_cleanup_loop(retention_days: int = 7):
    """F051: Periodically delete log entries older than retention_days."""
    while True:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
            async with async_session() as db:
                result = await db.execute(
                    delete(LogEntry).where(LogEntry.timestamp < cutoff)
                )
                deleted = result.rowcount
                await db.commit()
                if deleted:
                    logger.info("Log cleanup: deleted %d entries older than %d days", deleted, retention_days)
        except Exception:
            logger.exception("Log cleanup error")
        await asyncio.sleep(3600)  # every hour
