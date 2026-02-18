"""
服务器管理路由

提供服务器 CRUD、详情钻取等接口。
Cycle 8 Day 2: 从 topology.py 独立为专用路由。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.server import Server
from app.models.server_service import ServerService
from app.models.service_group import ServiceGroup
from app.models.nginx_upstream import NginxUpstream
from app.models.user import User
from app.schemas.topology import (
    ServerCreate, ServerResponse, ServerSummary,
    ServerServiceResponse, ServerServiceDetail,
    NginxUpstreamResponse,
)

router = APIRouter(prefix="/api/v1/servers", tags=["servers"])


@router.get("")
async def list_servers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    服务器列表（L1 视图）。
    返回分页的服务器列表，附带每台服务器的服务数量和最新 CPU/内存均值。
    """
    query = select(Server)
    count_query = select(func.count()).select_from(Server)

    if status:
        query = query.where(Server.status == status)
        count_query = count_query.where(Server.status == status)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            Server.hostname.ilike(pattern) | Server.label.ilike(pattern) | Server.ip_address.ilike(pattern)
        )
        count_query = count_query.where(
            Server.hostname.ilike(pattern) | Server.label.ilike(pattern) | Server.ip_address.ilike(pattern)
        )

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Server.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    servers = result.scalars().all()

    items = []
    for s in servers:
        svc_count = (await db.execute(
            select(func.count()).select_from(ServerService).where(ServerService.server_id == s.id)
        )).scalar() or 0

        agg = (await db.execute(
            select(func.avg(ServerService.cpu_percent), func.avg(ServerService.mem_mb))
            .where(ServerService.server_id == s.id)
        )).one()

        items.append(ServerSummary(
            **ServerResponse.model_validate(s).model_dump(),
            service_count=svc_count,
            cpu_avg=round(agg[0], 2) if agg[0] is not None else None,
            mem_avg=round(agg[1], 2) if agg[1] is not None else None,
        ))

    return {"items": [i.model_dump() for i in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{server_id}")
async def get_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    服务器详情（L2 钻取）。
    返回服务器基本信息 + 运行的服务列表 + nginx upstream 列表。
    """
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    svc_stmt = (
        select(ServerService, ServiceGroup.name.label("group_name"))
        .outerjoin(ServiceGroup, ServerService.group_id == ServiceGroup.id)
        .where(ServerService.server_id == server_id)
    )
    svc_rows = (await db.execute(svc_stmt)).all()
    services = [
        ServerServiceDetail(
            **ServerServiceResponse.model_validate(row.ServerService).model_dump(),
            group_name=row.group_name,
        ).model_dump()
        for row in svc_rows
    ]

    ups_stmt = select(NginxUpstream).where(NginxUpstream.server_id == server_id)
    ups = (await db.execute(ups_stmt)).scalars().all()
    upstreams = [NginxUpstreamResponse.model_validate(u).model_dump() for u in ups]

    return {
        "server": ServerResponse.model_validate(server).model_dump(),
        "services": services,
        "nginx_upstreams": upstreams,
    }


@router.post("", response_model=ServerResponse, status_code=201)
async def create_server(
    body: ServerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """注册新服务器。"""
    existing = (await db.execute(
        select(Server).where(Server.hostname == body.hostname)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"hostname '{body.hostname}' 已存在")

    server = Server(**body.model_dump())
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return ServerResponse.model_validate(server)


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int,
    body: ServerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新服务器信息。"""
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    if body.hostname != server.hostname:
        dup = (await db.execute(
            select(Server).where(Server.hostname == body.hostname)
        )).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=400, detail=f"hostname '{body.hostname}' 已被占用")

    for field, value in body.model_dump().items():
        setattr(server, field, value)

    await db.commit()
    await db.refresh(server)
    return ServerResponse.model_validate(server)


@router.delete("/{server_id}")
async def delete_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除服务器及其关联的 server_services 和 nginx_upstreams。"""
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    await db.execute(delete(ServerService).where(ServerService.server_id == server_id))
    await db.execute(delete(NginxUpstream).where(NginxUpstream.server_id == server_id))
    await db.delete(server)
    await db.commit()
    return {"detail": f"服务器 '{server.hostname}' 已删除"}
