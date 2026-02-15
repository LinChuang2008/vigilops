import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update

from app.core.database import async_session
from app.core.redis import get_redis
from app.models.host import Host

logger = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT = 300  # 5 minutes
CHECK_INTERVAL = 60  # check every 60 seconds


async def check_offline_hosts():
    """Scan Redis heartbeats and mark hosts offline if expired."""
    redis = await get_redis()
    async with async_session() as db:
        result = await db.execute(
            select(Host).where(Host.status == "online")
        )
        hosts = result.scalars().all()

        now = datetime.now(timezone.utc)
        for host in hosts:
            hb = await redis.get(f"heartbeat:{host.id}")
            if hb is None:
                # No Redis entry - check DB last_heartbeat
                if host.last_heartbeat and (now - host.last_heartbeat) > timedelta(seconds=HEARTBEAT_TIMEOUT):
                    host.status = "offline"
                    logger.warning(f"Host {host.hostname} (id={host.id}) marked offline (no heartbeat)")
            # If Redis key exists, host is still alive (key has 300s TTL)

        await db.commit()


async def offline_detector_loop():
    """Background loop that periodically checks for offline hosts."""
    logger.info("Offline detector started")
    while True:
        try:
            await check_offline_hosts()
        except Exception:
            logger.exception("Error in offline detector")
        await asyncio.sleep(CHECK_INTERVAL)
