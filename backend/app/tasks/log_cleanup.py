"""
日志清理任务模块。

定期删除超过保留期限的日志条目，防止日志数据无限增长。
默认保留 7 天，可通过环境变量 LOG_RETENTION_DAYS 配置。
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete

from app.core.database import async_session
from app.models.log_entry import LogEntry

logger = logging.getLogger(__name__)


async def log_cleanup_loop(retention_days: int = 7):
    """日志清理后台循环，每小时执行一次过期日志删除。

    Args:
        retention_days: 日志保留天数，超过此天数的记录将被删除
    """
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
        await asyncio.sleep(3600)  # 每小时执行一次
