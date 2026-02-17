"""
Agent 数据上报路由

提供 Agent 注册、心跳、指标上报、服务检查、日志写入、数据库指标等接口。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import re
from app.core.agent_auth import verify_agent_token
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.agent_token import AgentToken
from app.models.host import Host
from app.models.host_metric import HostMetric
from app.models.service import Service, ServiceCheck
from app.schemas.service import ServiceCheckReport
from app.schemas.agent import (
    AgentRegisterRequest,
    AgentRegisterResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    MetricReport,
)
from app.models.log_entry import LogEntry
from app.models.db_metric import MonitoredDatabase, DbMetric
from app.schemas.log_entry import LogBatchRequest, LogBatchResponse

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def _auto_classify_service(name: str) -> str:
    """根据服务名自动分类: middleware / business / infrastructure"""
    lower = name.lower()
    # 中间件：数据库、缓存、消息队列、注册中心、搜索引擎等
    if re.search(r'postgres|mysql|redis|rabbitmq|oracle|clickhouse|nacos|kafka|mongo|memcache|elasticsearch|mq', lower):
        return "middleware"
    # 基础设施：Web 服务器、代理、系统服务等
    if re.search(r'nginx|httpd|apache|caddy|traefik|haproxy|keepalived|crond|ntpd|envoy', lower):
        return "infrastructure"
    # 业务系统：后端、前端、应用服务等
    if re.search(r'backend|frontend|api|service|app|admin|job', lower):
        return "business"
    # 默认归为业务系统
    return "business"


@router.post("/register", response_model=AgentRegisterResponse)
async def register_agent(
    body: AgentRegisterRequest,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    """Agent 注册接口，幂等操作：已存在则更新信息，不存在则新建主机。"""
    # 查找是否已有相同 hostname + token 的主机
    result = await db.execute(
        select(Host).where(
            Host.hostname == body.hostname,
            Host.agent_token_id == agent_token.id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # 更新已有主机信息
        for field in ["ip_address", "os", "os_version", "arch", "cpu_cores", "memory_total_mb", "agent_version", "tags", "group_name"]:
            val = getattr(body, field)
            if val is not None:
                setattr(existing, field, val)
        existing.status = "online"
        existing.last_heartbeat = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return AgentRegisterResponse(host_id=existing.id, hostname=existing.hostname, status="online", created=False)

    # 创建新主机
    host = Host(
        hostname=body.hostname,
        ip_address=body.ip_address,
        os=body.os,
        os_version=body.os_version,
        arch=body.arch,
        cpu_cores=body.cpu_cores,
        memory_total_mb=body.memory_total_mb,
        agent_version=body.agent_version,
        tags=body.tags,
        group_name=body.group_name,
        agent_token_id=agent_token.id,
        status="online",
        last_heartbeat=datetime.now(timezone.utc),
    )
    db.add(host)
    await db.commit()
    await db.refresh(host)

    return AgentRegisterResponse(host_id=host.id, hostname=host.hostname, status="online", created=True)


@router.post("/heartbeat", response_model=AgentHeartbeatResponse)
async def heartbeat(
    body: AgentHeartbeatRequest,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    """Agent 心跳接口，更新主机在线状态并写入 Redis 用于离线检测。"""
    now = datetime.now(timezone.utc)

    # 更新数据库中的心跳时间
    result = await db.execute(select(Host).where(Host.id == body.host_id))
    host = result.scalar_one_or_none()
    if host:
        host.last_heartbeat = now
        host.status = "online"
        await db.commit()

    # 写入 Redis，设置 300 秒过期用于离线检测
    redis = await get_redis()
    await redis.set(f"heartbeat:{body.host_id}", now.isoformat(), ex=300)

    return AgentHeartbeatResponse(status="ok", server_time=now)


@router.post("/metrics", status_code=201)
async def report_metrics(
    body: MetricReport,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    """Agent 上报主机性能指标，同时缓存最新值到 Redis。"""
    import json as _json

    now = datetime.now(timezone.utc)
    recorded_at = body.timestamp or now

    # 持久化到数据库
    metric = HostMetric(
        host_id=body.host_id,
        cpu_percent=body.cpu_percent,
        cpu_load_1=body.cpu_load_1,
        cpu_load_5=body.cpu_load_5,
        cpu_load_15=body.cpu_load_15,
        memory_used_mb=body.memory_used_mb,
        memory_percent=body.memory_percent,
        disk_used_mb=body.disk_used_mb,
        disk_total_mb=body.disk_total_mb,
        disk_percent=body.disk_percent,
        net_bytes_sent=body.net_bytes_sent,
        net_bytes_recv=body.net_bytes_recv,
        net_send_rate_kb=body.net_send_rate_kb,
        net_recv_rate_kb=body.net_recv_rate_kb,
        net_packet_loss_rate=body.net_packet_loss_rate,
        recorded_at=recorded_at,
    )
    db.add(metric)
    await db.commit()

    # 缓存最新指标到 Redis，供仪表盘实时展示
    redis = await get_redis()
    latest = body.model_dump(exclude={"host_id", "timestamp"}, exclude_none=True)
    latest["recorded_at"] = recorded_at.isoformat()
    await redis.set(f"metrics:latest:{body.host_id}", _json.dumps(latest), ex=600)

    return {"status": "ok", "metric_id": metric.id}


@router.post("/services/register", status_code=200)
async def register_service(
    body: dict,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    """注册或查找服务，返回 service_id，幂等操作。"""
    name = body.get("name", "")
    target = body.get("target", body.get("url", ""))
    svc_type = body.get("type", "http")
    host_id = body.get("host_id")
    check_interval = body.get("check_interval", 60)
    timeout = body.get("timeout", 10)

    # 查找已有服务
    result = await db.execute(
        select(Service).where(Service.name == name, Service.target == target)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"service_id": existing.id, "created": False}

    # 自动分类
    category = _auto_classify_service(name)

    svc = Service(
        name=name, type=svc_type, target=target, host_id=host_id,
        check_interval=check_interval, timeout=timeout,
        category=category,
    )
    db.add(svc)
    await db.commit()
    await db.refresh(svc)
    return {"service_id": svc.id, "created": True}


@router.post("/services", status_code=201)
async def report_service_check(
    body: ServiceCheckReport,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    """Agent 上报服务健康检查结果。"""
    now = datetime.now(timezone.utc)

    check = ServiceCheck(
        service_id=body.service_id,
        status=body.status,
        response_time_ms=body.response_time_ms,
        status_code=body.status_code,
        error=body.error,
        checked_at=body.checked_at or now,
    )
    db.add(check)

    # 同步更新服务状态
    result = await db.execute(select(Service).where(Service.id == body.service_id))
    service = result.scalar_one_or_none()
    if service:
        service.status = body.status

    await db.commit()
    return {"status": "ok", "check_id": check.id}


@router.post("/db-metrics", status_code=201)
async def report_db_metrics(
    body: dict,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    """Agent 上报数据库性能指标，自动创建或更新被监控数据库记录。"""
    now = datetime.now(timezone.utc)
    host_id = body.get("host_id")
    db_name = body.get("db_name", "")
    db_type = body.get("db_type", "postgres")

    if not host_id or not db_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="host_id and db_name required")

    # 查找或创建被监控数据库记录
    result = await db.execute(
        select(MonitoredDatabase).where(
            MonitoredDatabase.host_id == host_id,
            MonitoredDatabase.name == db_name,
        )
    )
    monitored_db = result.scalar_one_or_none()
    if not monitored_db:
        monitored_db = MonitoredDatabase(
            host_id=host_id,
            name=db_name,
            db_type=db_type,
            status="healthy",
        )
        db.add(monitored_db)
        await db.flush()
    else:
        monitored_db.updated_at = now
        monitored_db.status = "healthy"

    # 更新 Oracle 慢查询详情
    slow_queries_detail = body.get("slow_queries_detail")
    if slow_queries_detail is not None:
        monitored_db.slow_queries_detail = slow_queries_detail

    # 写入指标记录
    metric = DbMetric(
        database_id=monitored_db.id,
        connections_total=body.get("connections_total"),
        connections_active=body.get("connections_active"),
        database_size_mb=body.get("database_size_mb"),
        slow_queries=body.get("slow_queries"),
        tables_count=body.get("tables_count"),
        transactions_committed=body.get("transactions_committed"),
        transactions_rolled_back=body.get("transactions_rolled_back"),
        qps=body.get("qps"),
        tablespace_used_pct=body.get("tablespace_used_pct"),
        recorded_at=now,
    )
    db.add(metric)
    await db.commit()

    # 检查数据库指标告警规则
    try:
        await _check_db_metric_alerts(monitored_db.id, body, db)
    except Exception:
        pass

    return {"status": "ok", "database_id": monitored_db.id, "metric_id": metric.id}


async def _check_db_metric_alerts(database_id: int, body: dict, db: AsyncSession):
    """检查数据库指标是否触发告警规则。"""
    from app.models.alert import AlertRule, Alert
    import operator as op_module

    result = await db.execute(
        select(AlertRule).where(
            AlertRule.rule_type == "db_metric",
            AlertRule.is_enabled == True,
        )
    )
    rules = result.scalars().all()

    ops = {">": op_module.gt, ">=": op_module.ge, "<": op_module.lt, "<=": op_module.le, "==": op_module.eq, "!=": op_module.ne}

    for rule in rules:
        if rule.db_id and rule.db_id != database_id:
            continue
        metric_name = rule.db_metric_name
        if not metric_name:
            continue
        value = body.get(metric_name)
        if value is None:
            continue
        compare = ops.get(rule.operator, op_module.gt)
        if compare(float(value), rule.threshold):
            alert = Alert(
                rule_id=rule.id,
                host_id=body.get("host_id"),
                severity=rule.severity,
                status="firing",
                title=f"数据库告警: {rule.name}",
                message=f"{metric_name} = {value} {rule.operator} {rule.threshold}",
                metric_value=float(value),
                threshold=rule.threshold,
            )
            db.add(alert)

    await db.commit()


@router.post("/logs", response_model=LogBatchResponse, status_code=201)
async def ingest_logs(
    body: LogBatchRequest,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    """批量写入日志条目，同时广播到 WebSocket 订阅者并检查日志关键字告警。"""
    from sqlalchemy.dialects.postgresql import insert
    from app.routers.logs import log_broadcaster

    if not body.logs:
        return LogBatchResponse(received=0)

    rows = [item.model_dump() for item in body.logs]
    await db.execute(insert(LogEntry), rows)
    await db.commit()

    # 广播到 WebSocket 实时日志订阅者
    broadcast_entries = []
    for item in body.logs:
        entry = item.model_dump()
        entry["timestamp"] = entry["timestamp"].isoformat()
        broadcast_entries.append(entry)
    await log_broadcaster.publish(broadcast_entries)

    # 检查日志关键字告警规则
    try:
        await _check_log_keyword_alerts(body.logs, db)
    except Exception:
        pass  # 不影响日志写入

    return LogBatchResponse(received=len(rows))


async def _check_log_keyword_alerts(logs: list, db: AsyncSession):
    """匹配日志内容与日志关键字告警规则，触发告警。"""
    from app.models.alert import AlertRule, Alert

    result = await db.execute(
        select(AlertRule).where(
            AlertRule.rule_type == "log_keyword",
            AlertRule.is_enabled == True,
        )
    )
    rules = result.scalars().all()
    if not rules:
        return

    for log_item in logs:
        msg = (log_item.message or "").lower()
        level = (log_item.level or "").upper()
        svc = log_item.service or ""

        for rule in rules:
            keyword = (rule.log_keyword or "").lower()
            if not keyword or keyword not in msg:
                continue
            if rule.log_level and rule.log_level.upper() != level:
                continue
            if rule.log_service and rule.log_service != svc:
                continue

            alert = Alert(
                rule_id=rule.id,
                host_id=log_item.host_id,
                severity=rule.severity,
                status="firing",
                title=f"日志关键字告警: {rule.name}",
                message=f"匹配关键字 '{rule.log_keyword}' in: {log_item.message[:200]}",
            )
            db.add(alert)

    await db.commit()
