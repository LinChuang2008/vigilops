"""
服务拓扑路由

提供服务依赖关系的拓扑图数据接口。
节点按主机分组，边仅包含有意义的依赖关系（calls / depends_on），
不再生成 co-located 全连接（同主机关系通过前端分组背景表示）。
"""
import re
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
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
    """根据服务名称推断分组类别"""
    name_lower = name.lower()
    if any(k in name_lower for k in ("postgres", "mysql", "mariadb", "mongo", "oracle")):
        return "database"
    if any(k in name_lower for k in ("redis", "memcache")):
        return "cache"
    if any(k in name_lower for k in ("rabbitmq", "kafka", "mq")):
        return "mq"
    if any(k in name_lower for k in ("clickhouse",)):
        return "olap"
    if any(k in name_lower for k in ("nacos",)):
        return "registry"
    if any(k in name_lower for k in ("nginx", "frontend", "web")):
        return "web"
    if any(k in name_lower for k in ("backend", "api")):
        return "api"
    return "app"


def _infer_edges(services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    自动推断有意义的服务依赖关系（不含 co-located）。
    规则：
    - backend/api → postgres/redis/mysql/rabbitmq/clickhouse 建立 depends_on
    - frontend → 同项目前缀的 backend/api 建立 calls
    - 业务服务 → nacos 建立 depends_on（注册中心）
    - 业务服务 → rabbitmq 建立 depends_on（消息队列）
    """
    edges: List[Dict[str, Any]] = []
    seen = set()

    def add_edge(src_id: int, tgt_id: int, etype: str, desc: str):
        key = (src_id, tgt_id, etype)
        if key not in seen:
            seen.add(key)
            edges.append({"source": src_id, "target": tgt_id, "type": etype, "description": desc})

    # 分类
    infra_pattern = re.compile(r"postgres|redis|mysql|rabbitmq|mariadb|mongo|oracle|clickhouse|memcache", re.I)
    api_pattern = re.compile(r"backend|api", re.I)
    fe_pattern = re.compile(r"frontend", re.I)
    nacos_pattern = re.compile(r"nacos", re.I)
    mq_pattern = re.compile(r"rabbitmq|\bmq\b", re.I)
    app_pattern = re.compile(r"service|app|admin|job", re.I)

    infra_services = [s for s in services if infra_pattern.search(s["name"])]
    api_services = [s for s in services if api_pattern.search(s["name"])]
    fe_services = [s for s in services if fe_pattern.search(s["name"])]
    nacos_services = [s for s in services if nacos_pattern.search(s["name"])]
    mq_services = [s for s in services if mq_pattern.search(s["name"])]
    # 业务应用（不含前端和基础设施）
    biz_services = [s for s in services if
                    (api_pattern.search(s["name"]) or app_pattern.search(s["name"]))
                    and not infra_pattern.search(s["name"])
                    and not fe_pattern.search(s["name"])
                    and not nacos_pattern.search(s["name"])]

    # 提取项目前缀用于匹配 frontend ↔ backend
    def get_prefix(name: str) -> str:
        """提取服务名前缀（如 vigilops-frontend-1 → vigilops）"""
        parts = re.split(r'[-_]', name.lower())
        return parts[0] if parts else ""

    # frontend → 同前缀 backend
    for fe in fe_services:
        fe_prefix = get_prefix(fe["name"])
        for api in api_services:
            if get_prefix(api["name"]) == fe_prefix:
                add_edge(fe["id"], api["id"], "calls", "API 调用")

    # backend/api → 同前缀数据库/缓存
    db_cache_pattern = re.compile(r"postgres|redis|mysql|mariadb|mongo|oracle", re.I)
    for api in api_services:
        api_prefix = get_prefix(api["name"])
        for infra in infra_services:
            if db_cache_pattern.search(infra["name"]) and get_prefix(infra["name"]) == api_prefix:
                add_edge(api["id"], infra["id"], "depends_on", "数据依赖")

    # 业务服务 → nacos（取第一个 nacos 即可）
    if nacos_services:
        nacos_main = nacos_services[0]
        for biz in biz_services:
            add_edge(biz["id"], nacos_main["id"], "depends_on", "服务注册")

    # 业务服务 → rabbitmq（取第一个）
    if mq_services:
        mq_main = mq_services[0]
        for biz in biz_services:
            if not mq_pattern.search(biz["name"]):
                add_edge(biz["id"], mq_main["id"], "depends_on", "消息队列")

    # 业务 app → 同前缀 backend（如 scip_visitor_service → scip-backend 等）
    # 通用：xxl-job-admin → 各业务服务
    xxl_services = [s for s in services if "xxl" in s["name"].lower()]
    for xxl in xxl_services:
        for biz in biz_services:
            if biz["id"] != xxl["id"]:
                add_edge(xxl["id"], biz["id"], "calls", "任务调度")

    return edges


@router.get("")
async def get_topology(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    获取服务拓扑图数据。
    返回节点（含主机分组）和边（仅有意义的依赖关系）。
    """
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

    # 去重：同名服务只保留一个节点（nacos 多端口场景）
    seen_names: Dict[str, int] = {}
    nodes = []
    services_data = []
    name_to_id: Dict[str, int] = {}

    for row in rows:
        svc_id, name, svc_type, status, host_id, hostname = row
        # 提取基础名（去掉端口后缀）
        base_name = re.sub(r'\s*\(:\d+\)$', '', name).strip()
        if base_name in seen_names:
            # 跳过重复，但记录 ID 映射
            continue
        seen_names[base_name] = svc_id
        name_to_id[name] = svc_id

        node = {
            "id": svc_id,
            "name": name,
            "type": svc_type,
            "status": status or "unknown",
            "host": hostname or "",
            "host_id": host_id,
            "group": _classify_service(name),
        }
        nodes.append(node)
        services_data.append({"id": svc_id, "name": name, "host_id": host_id})

    # 收集主机信息
    hosts_map: Dict[int, str] = {}
    for node in nodes:
        hid = node.get("host_id")
        if hid and hid not in hosts_map:
            hosts_map[hid] = node["host"]

    # 查询数据库中的依赖关系
    dep_result = await db.execute(select(ServiceDependency))
    deps = dep_result.scalars().all()

    if deps:
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
        edges = _infer_edges(services_data)

    # 返回主机列表供前端分组
    hosts = [{"id": hid, "name": hname} for hid, hname in hosts_map.items()]

    return {"nodes": nodes, "edges": edges, "hosts": hosts}


@router.post("/dependencies")
async def create_dependency(
    body: DependencyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动添加服务依赖关系"""
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
    """删除指定的服务依赖关系"""
    dep = await db.get(ServiceDependency, dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail="依赖关系不存在")
    await db.delete(dep)
    await db.commit()
    return {"detail": "已删除"}
