"""
报告定时生成任务

每天凌晨 2:00 自动生成日报，每周一凌晨 3:00 自动生成周报。
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_

from app.core.database import async_session
from app.models.report import Report
from app.services.report_generator import generate_report

logger = logging.getLogger(__name__)

# 东八区时区
CST = timezone(timedelta(hours=8))


async def _report_exists(db, report_type: str, period_start: datetime, period_end: datetime) -> bool:
    """检查同一时段的报告是否已存在（避免重复生成）。"""
    result = await db.execute(
        select(Report.id).where(and_(
            Report.report_type == report_type,
            Report.period_start == period_start,
            Report.period_end == period_end,
            Report.status.in_(["generating", "completed"]),
        )).limit(1)
    )
    return result.scalar() is not None


async def report_scheduler_loop():
    """报告定时生成主循环。每分钟检查一次是否需要生成报告。"""
    logger.info("报告定时任务已启动")
    while True:
        try:
            now = datetime.now(CST)

            # 每天 2:00 生成前一天的日报
            if now.hour == 2 and now.minute == 0:
                yesterday = now.date() - timedelta(days=1)
                period_start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=CST)
                period_end = datetime(now.year, now.month, now.day, tzinfo=CST)

                async with async_session() as db:
                    if not await _report_exists(db, "daily", period_start, period_end):
                        logger.info("开始生成日报: %s", yesterday)
                        await generate_report(db, "daily", period_start, period_end)

            # 每周一 3:00 生成上一周的周报
            if now.weekday() == 0 and now.hour == 3 and now.minute == 0:
                week_end = now.date()
                week_start = week_end - timedelta(days=7)
                period_start = datetime(week_start.year, week_start.month, week_start.day, tzinfo=CST)
                period_end = datetime(week_end.year, week_end.month, week_end.day, tzinfo=CST)

                async with async_session() as db:
                    if not await _report_exists(db, "weekly", period_start, period_end):
                        logger.info("开始生成周报: %s ~ %s", week_start, week_end)
                        await generate_report(db, "weekly", period_start, period_end)

        except Exception as e:
            logger.error("报告定时任务异常: %s", str(e))

        await asyncio.sleep(60)  # 每分钟检查一次
