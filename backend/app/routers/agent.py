from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/register", response_model=AgentRegisterResponse)
async def register_agent(
    body: AgentRegisterRequest,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    # Idempotent: check if host with same hostname + agent_token_id exists
    result = await db.execute(
        select(Host).where(
            Host.hostname == body.hostname,
            Host.agent_token_id == agent_token.id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update host info
        for field in ["ip_address", "os", "os_version", "arch", "cpu_cores", "memory_total_mb", "agent_version", "tags", "group_name"]:
            val = getattr(body, field)
            if val is not None:
                setattr(existing, field, val)
        existing.status = "online"
        existing.last_heartbeat = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return AgentRegisterResponse(host_id=existing.id, hostname=existing.hostname, status="online", created=False)

    # Create new host
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
    now = datetime.now(timezone.utc)

    # Update host heartbeat in DB
    result = await db.execute(select(Host).where(Host.id == body.host_id))
    host = result.scalar_one_or_none()
    if host:
        host.last_heartbeat = now
        host.status = "online"
        await db.commit()

    # Store in Redis for fast offline detection
    redis = await get_redis()
    await redis.set(f"heartbeat:{body.host_id}", now.isoformat(), ex=300)

    return AgentHeartbeatResponse(status="ok", server_time=now)


@router.post("/metrics", status_code=201)
async def report_metrics(
    body: MetricReport,
    agent_token: AgentToken = Depends(verify_agent_token),
    db: AsyncSession = Depends(get_db),
):
    import json as _json

    now = datetime.now(timezone.utc)
    recorded_at = body.timestamp or now

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
        recorded_at=recorded_at,
    )
    db.add(metric)
    await db.commit()

    # Cache latest metrics in Redis
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
    """Register/find a service by name + target. Returns service_id."""
    name = body.get("name", "")
    target = body.get("target", body.get("url", ""))
    svc_type = body.get("type", "http")
    host_id = body.get("host_id")
    check_interval = body.get("check_interval", 60)
    timeout = body.get("timeout", 10)

    # Find existing
    result = await db.execute(
        select(Service).where(Service.name == name, Service.target == target)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"service_id": existing.id, "created": False}

    svc = Service(
        name=name, type=svc_type, target=target, host_id=host_id,
        check_interval=check_interval, timeout=timeout,
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

    # Update service status
    result = await db.execute(select(Service).where(Service.id == body.service_id))
    service = result.scalar_one_or_none()
    if service:
        service.status = body.status

    await db.commit()
    return {"status": "ok", "check_id": check.id}
