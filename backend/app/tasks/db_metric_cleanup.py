"""
数据库指标清理任务模块。

定期删除超过保留期限的数据库监控指标数据，防止数据无限增长。
默认保留 30 天，可通过环境变量 DB_METRIC_RETENTION_DAYS 配置。
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete

from app.core.database import async_session
from app.models.db_metric import DbMetric

logger = logging.getLogger(__name__)


async def db_metric_cleanup_loop(retention_days: int = 30):
    """数据库指标清理后台循环，每小时执行一次过期数据删除。

    Args:
        retention_days: 数据保留天数，超过此天数的记录将被删除
    """
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
        await asyncio.sleep(3600)  # 每小时执行一次
