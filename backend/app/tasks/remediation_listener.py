"""
自动修复监听后台任务入口

在 main.py lifespan 中被调用，启动 Redis PubSub 监听循环。
"""
import logging

from app.remediation.listener import start_listener

logger = logging.getLogger(__name__)


async def remediation_listener_loop():
    """后台任务入口：启动 remediation listener。"""
    logger.info("Remediation listener task started")
    await start_listener()
