from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_auth import verify_agent_token
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.agent_token import AgentToken
from app.models.host import Host
from app.schemas.agent import (
    AgentRegisterRequest,
    AgentRegisterResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
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
