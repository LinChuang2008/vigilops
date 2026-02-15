import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.redis import get_redis
from app.models.host import Host
from app.models.host_metric import HostMetric
from app.models.user import User
from app.schemas.host import HostWithMetrics, HostResponse, HostMetricResponse

router = APIRouter(prefix="/api/v1/hosts", tags=["hosts"])


@router.get("")
async def list_hosts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    group_name: str | None = None,
    search: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Host)
    count_query = select(func.count()).select_from(Host)

    if status:
        query = query.where(Host.status == status)
        count_query = count_query.where(Host.status == status)
    if group_name:
        query = query.where(Host.group_name == group_name)
        count_query = count_query.where(Host.group_name == group_name)
    if search:
        query = query.where(Host.hostname.ilike(f"%{search}%"))
        count_query = count_query.where(Host.hostname.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar()

    query = query.order_by(Host.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    hosts = result.scalars().all()

    # Attach latest metrics from Redis
    redis = await get_redis()
    items = []
    for h in hosts:
        data = HostWithMetrics.model_validate(h)
        cached = await redis.get(f"metrics:latest:{h.id}")
        if cached:
            data.latest_metrics = json.loads(cached)
        items.append(data)

    return {"items": [item.model_dump() for item in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{host_id}", response_model=HostWithMetrics)
async def get_host(
    host_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    data = HostWithMetrics.model_validate(host)
    redis = await get_redis()
    cached = await redis.get(f"metrics:latest:{host.id}")
    if cached:
        data.latest_metrics = json.loads(cached)
    return data


@router.get("/{host_id}/metrics", response_model=list[HostMetricResponse])
async def get_host_metrics(
    host_id: int,
    hours: int = Query(1, ge=1, le=720),
    interval: str = Query("raw", regex="^(raw|5min|1h|1d)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone, timedelta

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    if interval == "raw":
        query = (
            select(HostMetric)
            .where(HostMetric.host_id == host_id, HostMetric.recorded_at >= since)
            .order_by(HostMetric.recorded_at.asc())
            .limit(1000)
        )
        result = await db.execute(query)
        return result.scalars().all()

    # For aggregated intervals, use raw SQL with date_trunc
    interval_map = {"5min": "5 minutes", "1h": "1 hour", "1d": "1 day"}
    trunc = interval_map[interval]

    from sqlalchemy import text
    sql = text(f"""
        SELECT
            0 as id, :host_id as host_id,
            avg(cpu_percent) as cpu_percent,
            avg(cpu_load_1) as cpu_load_1,
            avg(cpu_load_5) as cpu_load_5,
            avg(cpu_load_15) as cpu_load_15,
            avg(memory_used_mb)::int as memory_used_mb,
            avg(memory_percent) as memory_percent,
            avg(disk_used_mb)::int as disk_used_mb,
            avg(disk_total_mb)::int as disk_total_mb,
            avg(disk_percent) as disk_percent,
            avg(net_bytes_sent)::bigint as net_bytes_sent,
            avg(net_bytes_recv)::bigint as net_bytes_recv,
            date_trunc('{trunc.split()[1]}', recorded_at) as recorded_at
        FROM host_metrics
        WHERE host_id = :host_id AND recorded_at >= :since
        GROUP BY date_trunc('{trunc.split()[1]}', recorded_at)
        ORDER BY recorded_at ASC
        LIMIT 500
    """)
    result = await db.execute(sql, {"host_id": host_id, "since": since})
    rows = result.mappings().all()
    return [HostMetricResponse(**dict(r)) for r in rows]
