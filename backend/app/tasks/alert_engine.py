"""
告警引擎任务模块。

后台定时评估所有已启用的告警规则，将最新主机指标与规则阈值进行比对，
触发或恢复告警，并通过通知服务发送告警通知。
"""
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

CHECK_INTERVAL = 60  # 检查间隔（秒）

# 支持的比较运算符映射
OPERATORS = {
    ">": op.gt,
    ">=": op.ge,
    "<": op.lt,
    "<=": op.le,
    "==": op.eq,
    "!=": op.ne,
}

# 可从 Redis 缓存中读取的主机指标字段
METRIC_FIELDS = {"cpu_percent", "memory_percent", "disk_percent", "cpu_load_1", "cpu_load_5", "cpu_load_15"}


async def evaluate_host_rules():
    """评估所有已启用的主机类型告警规则，对每台主机逐一检查。"""
    redis = await get_redis()
    async with async_session() as db:
        # 查询所有已启用的主机类型告警规则
        result = await db.execute(
            select(AlertRule).where(
                and_(AlertRule.is_enabled == True, AlertRule.target_type == "host")  # noqa: E712
            )
        )
        rules = result.scalars().all()
        if not rules:
            return

        # 获取所有主机
        result = await db.execute(select(Host))
        hosts = result.scalars().all()

        for host in hosts:
            # 从 Redis 获取该主机的最新指标缓存
            cached = await redis.get(f"metrics:latest:{host.id}")
            if cached:
                try:
                    metrics = json.loads(cached)
                except (json.JSONDecodeError, TypeError):
                    metrics = {}
            else:
                metrics = {}

            # 对每条规则逐一评估
            for rule in rules:
                await _evaluate_rule(db, redis, rule, host, metrics)

        await db.commit()


async def _evaluate_rule(db, redis, rule: AlertRule, host: Host, metrics: dict):
    """评估单条规则在单台主机上是否触发告警。

    处理逻辑：
    1. 获取当前指标值并与阈值比较
    2. 如果违规且有持续时间要求，通过 Redis 跟踪首次违规时间
    3. 达到持续时间后创建告警并发送通知
    4. 如果恢复正常，自动解除告警
    """
    # 特殊指标：主机离线状态
    if rule.metric == "host_offline":
        is_violated = host.status == "offline"
        current_value = 1.0 if is_violated else 0.0
    elif rule.metric in METRIC_FIELDS:
        current_value = metrics.get(rule.metric)
        if current_value is None:
            return  # 无数据则跳过
        cmp_fn = OPERATORS.get(rule.operator)
        if not cmp_fn:
            return
        is_violated = cmp_fn(float(current_value), rule.threshold)
    else:
        return  # 未知指标类型，跳过

    # 查询该规则+主机是否已有触发中的告警
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
            return  # 已在触发状态，无需重复处理

        # 持续时间检查：通过 Redis 记录首次违规时间
        if rule.duration_seconds > 0:
            redis_key = f"alert:pending:{rule.id}:{host.id}"
            first_seen = await redis.get(redis_key)
            now = datetime.now(timezone.utc)
            if first_seen is None:
                # 首次违规，记录时间戳并等待
                await redis.set(redis_key, now.isoformat(), ex=rule.duration_seconds * 2)
                return
            first_dt = datetime.fromisoformat(first_seen)
            if (now - first_dt).total_seconds() < rule.duration_seconds:
                return  # 尚未达到持续时间要求

            # 持续时间已满，清理跟踪键
            await redis.delete(redis_key)

        # 创建新告警
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
        await db.flush()  # 刷新以获取 alert.id
        logger.info(f"Alert fired: {alert.title}")
        # 发送告警通知
        from app.services.notifier import send_alert_notification
        await send_alert_notification(db, alert)

    else:
        # 条件恢复正常，清理持续时间跟踪
        if rule.duration_seconds > 0:
            await redis.delete(f"alert:pending:{rule.id}:{host.id}")

        # 如果存在触发中的告警，标记为已恢复
        if existing_alert:
            existing_alert.status = "resolved"
            existing_alert.resolved_at = datetime.now(timezone.utc)
            logger.info(f"Alert resolved: {existing_alert.title}")
            from app.services.notifier import send_alert_notification
            await send_alert_notification(db, existing_alert)


async def alert_engine_loop():
    """告警引擎后台循环，定期执行告警规则评估。"""
    logger.info("Alert engine started")
    while True:
        try:
            await evaluate_host_rules()
        except Exception:
            logger.exception("Error in alert engine")
        await asyncio.sleep(CHECK_INTERVAL)
