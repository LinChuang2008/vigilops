"""F065: Database metrics cleanup and aggregation."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete

from app.core.database import async_session
from app.models.db_metric import DbMetric

logger = logging.getLogger(__name__)


async def db_metric_cleanup_loop(retention_days: int = 30):
    """Periodically delete db metrics older than retention_days."""
    while True:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
            async with async_session() as db:
                result = await db.execute(
                    delete(DbMetric).where(DbMetric.recorded_at < cutoff)
                )
                deleted = result.rowcount
                await db.commit()
                if deleted:
                    logger.info("DB metric cleanup: deleted %d entries older than %d days", deleted, retention_days)
        except Exception:
            logger.exception("DB metric cleanup error")
        await asyncio.sleep(3600)  # every hour
