"""
通知分发服务模块。

负责将告警通知发送到所有已启用的通知渠道（当前支持 Webhook），
支持静默窗口、冷却时间控制和失败重试机制。
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.alert import Alert, AlertRule
from app.models.notification import NotificationChannel, NotificationLog

logger = logging.getLogger(__name__)

# Webhook 发送最大重试次数
MAX_RETRIES = 3


async def send_alert_notification(db: AsyncSession, alert: Alert):
    """为告警发送通知到所有已启用的通知渠道。

    处理流程：静默窗口检查 → 冷却时间检查 → 发送通知 → 设置冷却。

    Args:
        db: 数据库会话
        alert: 需要发送通知的告警对象
    """
    # 1. 查询关联的告警规则，获取冷却和静默配置
    rule_result = await db.execute(select(AlertRule).where(AlertRule.id == alert.rule_id))
    rule = rule_result.scalar_one_or_none()

    # 2. 检查是否在静默时间窗口内
    if rule and rule.silence_start and rule.silence_end:
        now_time = datetime.now().time()
        if rule.silence_start <= rule.silence_end:
            # 不跨午夜的情况，如 08:00-18:00
            if rule.silence_start <= now_time <= rule.silence_end:
                logger.info(f"Alert {alert.id} silenced (current time in silence window)")
                return
        else:
            # 跨午夜的情况，如 23:00-06:00
            if now_time >= rule.silence_start or now_time <= rule.silence_end:
                logger.info(f"Alert {alert.id} silenced (current time in silence window)")
                return

    # 3. 检查冷却时间（同一规则在冷却期内不重复通知）
    redis = await get_redis()
    cooldown = rule.cooldown_seconds if rule else 300
    cooldown_key = f"alert:cooldown:{alert.rule_id}"
    if await redis.get(cooldown_key):
        await redis.incr(f"alert:cooldown:count:{alert.rule_id}")
        logger.info(f"Alert {alert.id} suppressed by cooldown")
        return

    # 4. 向所有已启用的通知渠道发送通知
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.is_enabled == True)  # noqa: E712
    )
    channels = result.scalars().all()

    for channel in channels:
        await _send_to_channel(db, alert, channel)

    # 5. 发送完成后设置冷却标记
    if cooldown > 0:
        await redis.setex(cooldown_key, cooldown, "1")
        await redis.delete(f"alert:cooldown:count:{alert.rule_id}")


async def _send_to_channel(db: AsyncSession, alert: Alert, channel: NotificationChannel):
    """向单个通知渠道发送告警，支持失败重试。

    Args:
        db: 数据库会话
        alert: 告警对象
        channel: 目标通知渠道
    """
    if channel.type != "webhook":
        logger.warning(f"Unsupported channel type: {channel.type}")
        return

    url = channel.config.get("url")
    if not url:
        return

    headers = channel.config.get("headers", {})
    headers.setdefault("Content-Type", "application/json")

    # 构建 Webhook 请求体
    payload = {
        "alert_id": alert.id,
        "title": alert.title,
        "message": alert.message,
        "severity": alert.severity,
        "status": alert.status,
        "metric_value": alert.metric_value,
        "threshold": alert.threshold,
        "host_id": alert.host_id,
        "service_id": alert.service_id,
        "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
    }

    # 创建通知日志记录
    log = NotificationLog(
        alert_id=alert.id,
        channel_id=channel.id,
        status="failed",
        retries=0,
    )

    # 带重试的发送逻辑
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload, headers=headers)
            log.response_code = resp.status_code
            if 200 <= resp.status_code < 300:
                log.status = "sent"
                break
            log.error = f"HTTP {resp.status_code}"
        except Exception as e:
            log.error = str(e)[:500]
        log.retries = attempt + 1

    log.sent_at = datetime.now(timezone.utc)
    db.add(log)
    await db.commit()

    if log.status == "sent":
        logger.info(f"Notification sent for alert {alert.id} to channel {channel.name}")
    else:
        logger.warning(f"Notification failed for alert {alert.id} to channel {channel.name}: {log.error}")
