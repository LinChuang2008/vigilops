"""Notification dispatcher — sends alert notifications via configured channels."""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.alert import Alert, AlertRule
from app.models.notification import NotificationChannel, NotificationLog

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def send_alert_notification(db: AsyncSession, alert: Alert):
    """Send notification for an alert to all enabled channels."""
    # 1. Query rule for cooldown and silence config
    rule_result = await db.execute(select(AlertRule).where(AlertRule.id == alert.rule_id))
    rule = rule_result.scalar_one_or_none()

    # 2. Check silence window
    if rule and rule.silence_start and rule.silence_end:
        now_time = datetime.now().time()
        if rule.silence_start <= rule.silence_end:
            if rule.silence_start <= now_time <= rule.silence_end:
                logger.info(f"Alert {alert.id} silenced (current time in silence window)")
                return
        else:  # crosses midnight, e.g. 23:00 - 06:00
            if now_time >= rule.silence_start or now_time <= rule.silence_end:
                logger.info(f"Alert {alert.id} silenced (current time in silence window)")
                return

    # 3. Check cooldown
    redis = await get_redis()
    cooldown = rule.cooldown_seconds if rule else 300
    cooldown_key = f"alert:cooldown:{alert.rule_id}"
    if await redis.get(cooldown_key):
        await redis.incr(f"alert:cooldown:count:{alert.rule_id}")
        logger.info(f"Alert {alert.id} suppressed by cooldown")
        return

    # 4. Send notifications to all enabled channels
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.is_enabled == True)  # noqa: E712
    )
    channels = result.scalars().all()

    for channel in channels:
        await _send_to_channel(db, alert, channel)

    # 5. Set cooldown after sending
    if cooldown > 0:
        await redis.setex(cooldown_key, cooldown, "1")
        await redis.delete(f"alert:cooldown:count:{alert.rule_id}")


async def _send_to_channel(db: AsyncSession, alert: Alert, channel: NotificationChannel):
    """Send to a single channel with retry."""
    if channel.type != "webhook":
        logger.warning(f"Unsupported channel type: {channel.type}")
        return

    url = channel.config.get("url")
    if not url:
        return

    headers = channel.config.get("headers", {})
    headers.setdefault("Content-Type", "application/json")

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

    log = NotificationLog(
        alert_id=alert.id,
        channel_id=channel.id,
        status="failed",
        retries=0,
    )

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
