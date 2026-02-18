"""
Redis PubSub 监听器

订阅 vigilops:alert:new 频道，收到告警事件后调用 RemediationAgent 处理。
仅在 AGENT_ENABLED=true 时运行。
"""
import asyncio
import json
import logging

from app.core.redis import get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)

CHANNEL = "vigilops:alert:new"


async def start_listener():
    """启动 Redis PubSub 监听，接收告警事件并触发自动修复。"""
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHANNEL)
    logger.info(f"Remediation listener subscribed to {CHANNEL}")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                alert_id = data.get("alert_id")
                if alert_id is None:
                    logger.warning("Received alert event without alert_id, skipping")
                    continue
                logger.info(f"Received alert event: alert_id={alert_id}")
                # 延迟导入避免循环依赖
                from app.remediation.agent import RemediationAgent
                agent = RemediationAgent(dry_run=settings.agent_dry_run)
                await agent.handle_alert(data)
            except Exception:
                logger.exception("Error handling alert event")
    except asyncio.CancelledError:
        logger.info("Remediation listener shutting down")
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.close()
