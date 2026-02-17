"""
服务拓扑路由

提供服务依赖关系的拓扑图数据接口，支持自动推断和手动管理依赖关系。
"""
import re
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.service import Service
from app.models.host import Host
from app.models.service_dependency import ServiceDependency
from app.models.user import User

router = APIRouter(prefix="/api/v1/topology", tags=["topology"])


class DependencyCreate(BaseModel):
    """创建依赖关系的请求体"""
    source_service_id: int
    target_service_id: int
    dependency_type: str = "calls"
    description: Optional[str] = None


class DependencyResponse(BaseModel):
    """依赖关系响应"""
    id: int
    source_service_id: int
    target_service_id: int
    dependency_type: str
    description: Optional[str] = None


def _classify_service(name: str) -> str:
    """根据服务名称推断分组类别。"""
    name_lower = name.lower()
    if any(k in name_lower for k in ("postgres", "mysql", "mariadb", "mongo")):
        return "database"
    if any(k in name_lower for k in ("redis", "memcache")):
        return "cache"
    if any(k in name_lower for k in ("rabbitmq", "kafka", "mq")):
        return "mq"
    if any(k in name_lower for k in ("nginx", "frontend", "web")):
        return "web"
    if any(k in name_lower for k in ("backend", "api")):
        return "api"
    return "other"


def _infer_edges(services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    自动推断服务间的依赖关系（不写入数据库）。
    规则：
    - 同一 host_id 的服务建立 co-located 关系
    - backend/api → postgres/redis/mysql/rabbitmq 建立 depends_on
    - frontend → backend/api 建立 calls
    """
    edges: List[Dict[str, Any]] = []
    seen = set()

    # 按 host 分组
    host_groups: Dict[Optional[int], List[Dict[str, Any]]] = {}
    for svc in services:
        hid = svc.get("host_id")
        if hid is not None:
            host_groups.setdefault(hid, []).append(svc)

    # 同主机 co-located
    for hid, group in host_groups.items():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                key = (min(a["id"], b["id"]), max(a["id"], b["id"]))
                if key not in seen:
                    seen.add(key)
                    edges.append({
                        "source": a["id"], "target": b["id"],
                        "type": "co-located", "description": "同主机部署"
                    })

    # 名称匹配推断
    db_pattern = re.compile(r"postgres|redis|mysql|rabbitmq|mariadb|mongo|memcache", re.I)
    api_pattern = re.compile(r"backend|api", re.I)
    fe_pattern = re.compile(r"frontend", re.I)

    db_services = [s for s in services if db_pattern.search(s["name"])]
    api_services = [s for s in services if api_pattern.search(s["name"])]
    fe_services = [s for s in services if fe_pattern.search(s["name"])]

    # api/backend → 数据库/缓存/消息队列
    for api_svc in api_services:
        for db_svc in db_services:
            key = (api_svc["id"], db_svc["id"])
            if key not in seen:
                seen.add(key)
                edges.append({
                    "source": api_svc["id"], "target": db_svc["id"],
                    "type": "depends_on", "description": "数据依赖"
                })

    # frontend → backend/api
    for fe_svc in fe_services:
        for api_svc in api_services:
            key = (fe_svc["id"], api_svc["id"])
            if key not in seen:
                seen.add(key)
                edges.append({
                    "source": fe_svc["id"], "target": api_svc["id"],
                    "type": "calls", "description": "API调用"
                })

    return edges


@router.get("")
async def get_topology(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取服务拓扑图数据，包含节点和边。"""
    # 查询所有服务，关联主机名
    stmt = (
        select(
            Service.id, Service.name, Service.type, Service.status,
            Service.host_id, Host.hostname
        )
        .outerjoin(Host, Service.host_id == Host.id)
        .where(Service.is_active == True)
    )
    result = await db.execute(stmt)
    rows = result.all()

    nodes = []
    services_data = []
    for row in rows:
        svc_id, name, svc_type, status, host_id, hostname = row
        node = {
            "id": svc_id,
            "name": name,
            "type": svc_type,
            "status": status or "unknown",
            "host": hostname or "",
            "group": _classify_service(name),
        }
        nodes.append(node)
        services_data.append({"id": svc_id, "name": name, "host_id": host_id})

    # 查询数据库中的依赖关系
    dep_result = await db.execute(select(ServiceDependency))
    deps = dep_result.scalars().all()

    if deps:
        # 使用数据库中存储的依赖关系
        edges = [
            {
                "source": d.source_service_id,
                "target": d.target_service_id,
                "type": d.dependency_type,
                "description": d.description or "",
            }
            for d in deps
        ]
    else:
        # 自动推断依赖关系
        edges = _infer_edges(services_data)

    return {"nodes": nodes, "edges": edges}


@router.post("/dependencies")
async def create_dependency(
    body: DependencyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动添加服务依赖关系。"""
    # 验证两个服务都存在
    for sid in (body.source_service_id, body.target_service_id):
        svc = await db.get(Service, sid)
        if not svc:
            raise HTTPException(status_code=404, detail=f"服务 {sid} 不存在")

    dep = ServiceDependency(
        source_service_id=body.source_service_id,
        target_service_id=body.target_service_id,
        dependency_type=body.dependency_type,
        description=body.description,
    )
    db.add(dep)
    await db.commit()
    await db.refresh(dep)
    return DependencyResponse(
        id=dep.id,
        source_service_id=dep.source_service_id,
        target_service_id=dep.target_service_id,
        dependency_type=dep.dependency_type,
        description=dep.description,
    )


@router.delete("/dependencies/{dep_id}")
async def delete_dependency(
    dep_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除指定的服务依赖关系。"""
    dep = await db.get(ServiceDependency, dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail="依赖关系不存在")
    await db.delete(dep)
    await db.commit()
    return {"detail": "已删除"}
