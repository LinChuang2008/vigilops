"""Notification dispatcher — sends alert notifications via configured channels."""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.notification import NotificationChannel, NotificationLog

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def send_alert_notification(db: AsyncSession, alert: Alert):
    """Send notification for an alert to all enabled channels."""
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.is_enabled == True)  # noqa: E712
    )
    channels = result.scalars().all()

    for channel in channels:
        await _send_to_channel(db, alert, channel)


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
