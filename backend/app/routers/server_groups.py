"""
服务组管理路由

提供服务组 CRUD、详情（含服务器分布）等接口。
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
from app.models.user import User
from app.schemas.topology import (
    ServiceGroupCreate, ServiceGroupResponse, ServiceGroupDetail,
    ServerResponse,
    ServerServiceCreate, ServerServiceResponse,
)

router = APIRouter(prefix="/api/v1/server-groups", tags=["server-groups"])


@router.get("")
async def list_service_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """服务组列表，附带每组的服务器数量。"""
    query = select(ServiceGroup)
    count_query = select(func.count()).select_from(ServiceGroup)

    if category:
        query = query.where(ServiceGroup.category == category)
        count_query = count_query.where(ServiceGroup.category == category)

    count = (await db.execute(count_query)).scalar() or 0
    stmt = query.order_by(ServiceGroup.id).offset((page - 1) * page_size).limit(page_size)
    groups = (await db.execute(stmt)).scalars().all()

    items = []
    for g in groups:
        server_count = (await db.execute(
            select(func.count(func.distinct(ServerService.server_id)))
            .where(ServerService.group_id == g.id)
        )).scalar() or 0
        d = ServiceGroupResponse.model_validate(g).model_dump()
        d["server_count"] = server_count
        items.append(d)

    return {"items": items, "total": count, "page": page, "page_size": page_size}


@router.get("/{group_id}")
async def get_service_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """服务组详情，含关联的服务器列表。"""
    group = await db.get(ServiceGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="服务组不存在")

    # 查询该服务组关联的所有服务器
    stmt = (
        select(Server)
        .join(ServerService, ServerService.server_id == Server.id)
        .where(ServerService.group_id == group_id)
        .distinct()
    )
    servers = (await db.execute(stmt)).scalars().all()

    return ServiceGroupDetail(
        **ServiceGroupResponse.model_validate(group).model_dump(),
        servers=[ServerResponse.model_validate(s) for s in servers],
    )


@router.post("", response_model=ServiceGroupResponse, status_code=201)
async def create_service_group(
    body: ServiceGroupCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建服务组。"""
    existing = (await db.execute(
        select(ServiceGroup).where(ServiceGroup.name == body.name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"服务组 '{body.name}' 已存在")

    group = ServiceGroup(**body.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return ServiceGroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=ServiceGroupResponse)
async def update_service_group(
    group_id: int,
    body: ServiceGroupCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新服务组。"""
    group = await db.get(ServiceGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="服务组不存在")

    if body.name != group.name:
        dup = (await db.execute(
            select(ServiceGroup).where(ServiceGroup.name == body.name)
        )).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=400, detail=f"服务组 '{body.name}' 已被占用")

    for field, value in body.model_dump().items():
        setattr(group, field, value)

    await db.commit()
    await db.refresh(group)
    return ServiceGroupResponse.model_validate(group)


@router.delete("/{group_id}")
async def delete_service_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除服务组及其关联记录。"""
    group = await db.get(ServiceGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="服务组不存在")

    await db.execute(delete(ServerService).where(ServerService.group_id == group_id))
    await db.delete(group)
    await db.commit()
    return {"detail": f"服务组 '{group.name}' 已删除"}


# ==================== Server-Service 关联管理 ====================

@router.post("/{group_id}/servers", response_model=ServerServiceResponse, status_code=201)
async def add_server_to_group(
    group_id: int,
    body: ServerServiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """将服务器添加到服务组（创建 server_service 关联）。"""
    group = await db.get(ServiceGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="服务组不存在")

    server = await db.get(Server, body.server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    # 强制 group_id 与路径一致
    assoc = ServerService(
        server_id=body.server_id,
        group_id=group_id,
        port=body.port,
        pid=body.pid,
        status=body.status,
        cpu_percent=body.cpu_percent,
        mem_mb=body.mem_mb,
    )
    db.add(assoc)
    await db.commit()
    await db.refresh(assoc)
    return ServerServiceResponse.model_validate(assoc)


@router.delete("/{group_id}/servers/{server_id}")
async def remove_server_from_group(
    group_id: int,
    server_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从服务组移除服务器。"""
    result = await db.execute(
        select(ServerService).where(
            ServerService.group_id == group_id,
            ServerService.server_id == server_id,
        )
    )
    assocs = result.scalars().all()
    if not assocs:
        raise HTTPException(status_code=404, detail="关联不存在")

    for a in assocs:
        await db.delete(a)
    await db.commit()
    return {"detail": "已移除"}
