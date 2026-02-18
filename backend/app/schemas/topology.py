"""
拓扑相关请求/响应模型

定义多服务器拓扑 API 的数据结构。
"""
from datetime import datetime
from pydantic import BaseModel


# ── Server ──────────────────────────────────────────

class ServerCreate(BaseModel):
    """创建/注册服务器请求体。"""
    hostname: str
    ip_address: str | None = None
    label: str | None = None
    tags: dict | None = None
    is_simulated: bool = False


class ServerResponse(BaseModel):
    """服务器基本信息响应体。"""
    id: int
    hostname: str
    ip_address: str | None = None
    label: str | None = None
    tags: dict | None = None
    status: str
    last_seen: datetime | None = None
    is_simulated: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerSummary(ServerResponse):
    """带摘要指标的服务器响应体。"""
    service_count: int = 0
    cpu_avg: float | None = None
    mem_avg: float | None = None
    alert_count: int = 0


# ── ServiceGroup ────────────────────────────────────

class ServiceGroupCreate(BaseModel):
    """创建服务组请求体。"""
    name: str
    category: str | None = None


class ServiceGroupResponse(BaseModel):
    """服务组响应体。"""
    id: int
    name: str
    category: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceGroupDetail(ServiceGroupResponse):
    """带服务器分布的服务组详情。"""
    servers: list[ServerResponse] = []


# ── ServerService ───────────────────────────────────

class ServerServiceCreate(BaseModel):
    """创建服务器-服务关联请求体。"""
    server_id: int
    group_id: int
    port: int | None = None
    pid: int | None = None
    status: str = "running"
    cpu_percent: float = 0
    mem_mb: float = 0


class ServerServiceResponse(BaseModel):
    """服务器-服务关联响应体。"""
    id: int
    server_id: int
    group_id: int
    port: int | None = None
    pid: int | None = None
    status: str
    cpu_percent: float
    mem_mb: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerServiceDetail(ServerServiceResponse):
    """带服务组名称的关联详情。"""
    group_name: str | None = None


# ── NginxUpstream ───────────────────────────────────

class NginxUpstreamCreate(BaseModel):
    """创建 Nginx Upstream 请求体。"""
    server_id: int
    upstream_name: str
    backend_address: str
    weight: int = 1
    status: str = "up"


class NginxUpstreamResponse(BaseModel):
    """Nginx Upstream 响应体。"""
    id: int
    server_id: int
    upstream_name: str
    backend_address: str
    weight: int
    status: str
    parsed_at: datetime

    model_config = {"from_attributes": True}


# ── Topology Graph ──────────────────────────────────

class TopologyEdge(BaseModel):
    """拓扑图中的连线。"""
    from_server: str
    to_server: str
    via: str  # nginx_upstream
    upstream: str | None = None


class TopologyResponse(BaseModel):
    """全局拓扑响应体。"""
    servers: list[ServerSummary]
    edges: list[TopologyEdge]
