"""Alert engine — periodically evaluates alert rules against latest metrics."""
import asyncio
import json
import logging
import operator as op
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_

from app.core.database import async_session
from app.core.redis import get_redis
from app.models.alert import Alert, AlertRule
from app.models.host import Host

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 60  # seconds

OPERATORS = {
    ">": op.gt,
    ">=": op.ge,
    "<": op.lt,
    "<=": op.le,
    "==": op.eq,
    "!=": op.ne,
}

# Metrics that can be read from Redis cached latest metrics
METRIC_FIELDS = {"cpu_percent", "memory_percent", "disk_percent", "cpu_load_1", "cpu_load_5", "cpu_load_15"}


async def evaluate_host_rules():
    """Check all enabled host-type alert rules against latest metrics."""
    redis = await get_redis()
    async with async_session() as db:
        # Get enabled host rules
        result = await db.execute(
            select(AlertRule).where(
                and_(AlertRule.is_enabled == True, AlertRule.target_type == "host")  # noqa: E712
            )
        )
        rules = result.scalars().all()
        if not rules:
            return

        # Get all hosts
        result = await db.execute(select(Host))
        hosts = result.scalars().all()

        for host in hosts:
            # Get latest metrics from Redis
            cached = await redis.get(f"metrics:latest:{host.id}")
            if cached:
                try:
                    metrics = json.loads(cached)
                except (json.JSONDecodeError, TypeError):
                    metrics = {}
            else:
                metrics = {}

            for rule in rules:
                await _evaluate_rule(db, redis, rule, host, metrics)

        await db.commit()


async def _evaluate_rule(db, redis, rule: AlertRule, host: Host, metrics: dict):
    """Evaluate a single rule against a single host."""
    # Special metric: host_offline
    if rule.metric == "host_offline":
        is_violated = host.status == "offline"
        current_value = 1.0 if is_violated else 0.0
    elif rule.metric in METRIC_FIELDS:
        current_value = metrics.get(rule.metric)
        if current_value is None:
            return  # no data, skip
        cmp_fn = OPERATORS.get(rule.operator)
        if not cmp_fn:
            return
        is_violated = cmp_fn(float(current_value), rule.threshold)
    else:
        return  # unknown metric

    # Check for existing firing alert for this rule+host
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.rule_id == rule.id,
                Alert.host_id == host.id,
                Alert.status == "firing",
            )
        )
    )
    existing_alert = result.scalar_one_or_none()

    if is_violated:
        if existing_alert:
            return  # already firing, nothing to do

        # Check duration requirement via Redis tracking
        if rule.duration_seconds > 0:
            redis_key = f"alert:pending:{rule.id}:{host.id}"
            first_seen = await redis.get(redis_key)
            now = datetime.now(timezone.utc)
            if first_seen is None:
                await redis.set(redis_key, now.isoformat(), ex=rule.duration_seconds * 2)
                return  # not yet exceeded duration
            first_dt = datetime.fromisoformat(first_seen)
            if (now - first_dt).total_seconds() < rule.duration_seconds:
                return  # still within duration window

            # Duration exceeded, clean up and create alert
            await redis.delete(redis_key)

        # Create alert
        alert = Alert(
            rule_id=rule.id,
            host_id=host.id,
            severity=rule.severity,
            status="firing",
            title=f"{rule.name} - {host.hostname}",
            message=f"{rule.metric} = {current_value} {rule.operator} {rule.threshold}",
            metric_value=float(current_value),
            threshold=rule.threshold,
        )
        db.add(alert)
        await db.flush()  # get alert.id
        logger.info(f"Alert fired: {alert.title}")
        # Send notification
        from app.services.notifier import send_alert_notification
        await send_alert_notification(db, alert)

    else:
        # Condition resolved
        # Clean pending duration tracker
        if rule.duration_seconds > 0:
            await redis.delete(f"alert:pending:{rule.id}:{host.id}")

        if existing_alert:
            existing_alert.status = "resolved"
            existing_alert.resolved_at = datetime.now(timezone.utc)
            logger.info(f"Alert resolved: {existing_alert.title}")
            from app.services.notifier import send_alert_notification
            await send_alert_notification(db, existing_alert)


async def alert_engine_loop():
    """Background loop that periodically evaluates alert rules."""
    logger.info("Alert engine started")
    while True:
        try:
            await evaluate_host_rules()
        except Exception:
            logger.exception("Error in alert engine")
        await asyncio.sleep(CHECK_INTERVAL)
