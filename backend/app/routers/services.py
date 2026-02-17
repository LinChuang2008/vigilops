"""
服务监控路由

提供服务列表、详情、健康检查历史等接口。
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.service import Service, ServiceCheck
from app.models.user import User
from app.schemas.service import ServiceResponse, ServiceCheckResponse

router = APIRouter(prefix="/api/v1/services", tags=["services"])


async def _calc_uptime(db: AsyncSession, service_id: int, hours: int = 24) -> float | None:
    """计算指定服务在最近 N 小时内的可用率（百分比）。"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    total = (await db.execute(
        select(func.count()).select_from(ServiceCheck)
        .where(ServiceCheck.service_id == service_id, ServiceCheck.checked_at >= since)
    )).scalar()
    if not total:
        return None
    up = (await db.execute(
        select(func.count()).select_from(ServiceCheck)
        .where(ServiceCheck.service_id == service_id, ServiceCheck.checked_at >= since, ServiceCheck.status == "up")
    )).scalar()
    return round(up / total * 100, 2)


@router.get("")
async def list_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分页查询服务列表，支持按状态和分类筛选，附带 24h 可用率。"""
    query = select(Service)
    count_query = select(func.count()).select_from(Service)

    if status:
        query = query.where(Service.status == status)
        count_query = count_query.where(Service.status == status)
    if category:
        query = query.where(Service.category == category)
        count_query = count_query.where(Service.category == category)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Service.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    services = result.scalars().all()

    items = []
    for s in services:
        data = ServiceResponse.model_validate(s)
        data.uptime_percent = await _calc_uptime(db, s.id)
        items.append(data.model_dump())

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个服务详情。"""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    data = ServiceResponse.model_validate(service)
    data.uptime_percent = await _calc_uptime(db, service.id)
    return data


@router.get("/{service_id}/checks", response_model=list[ServiceCheckResponse])
async def get_service_checks(
    service_id: int,
    hours: int = Query(24, ge=1, le=720),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询服务健康检查历史记录。"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(ServiceCheck)
        .where(ServiceCheck.service_id == service_id, ServiceCheck.checked_at >= since)
        .order_by(ServiceCheck.checked_at.desc())
        .limit(500)
    )
    return result.scalars().all()
