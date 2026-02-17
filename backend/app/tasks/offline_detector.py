"""
主机离线检测任务模块。

定期扫描所有在线主机的心跳状态，当心跳超时（默认 5 分钟）时
将主机标记为离线状态，配合告警引擎触发主机离线告警。
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update

from app.core.database import async_session
from app.core.redis import get_redis
from app.models.host import Host

logger = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT = 300  # 心跳超时时间（秒），即 5 分钟
CHECK_INTERVAL = 60  # 检查间隔（秒）


async def check_offline_hosts():
    """扫描所有在线主机的 Redis 心跳记录，将心跳超时的主机标记为离线。"""
    redis = await get_redis()
    async with async_session() as db:
        # 只查询当前状态为在线的主机
        result = await db.execute(
            select(Host).where(Host.status == "online")
        )
        hosts = result.scalars().all()

        now = datetime.now(timezone.utc)
        for host in hosts:
            hb = await redis.get(f"heartbeat:{host.id}")
            if hb is None:
                # Redis 中无心跳记录，回退到数据库中的 last_heartbeat 字段判断
                if host.last_heartbeat and (now - host.last_heartbeat) > timedelta(seconds=HEARTBEAT_TIMEOUT):
                    host.status = "offline"
                    logger.warning(f"Host {host.hostname} (id={host.id}) marked offline (no heartbeat)")
            # Redis 键存在说明主机仍在线（心跳键有 300s TTL，由 Agent 续期）

        await db.commit()


async def offline_detector_loop():
    """离线检测后台循环，定期检查主机心跳状态。"""
    logger.info("Offline detector started")
    while True:
        try:
            await check_offline_hosts()
        except Exception:
            logger.exception("Error in offline detector")
        await asyncio.sleep(CHECK_INTERVAL)
