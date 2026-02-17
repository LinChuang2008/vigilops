"""
服务相关请求/响应模型

定义服务列表、健康检查结果等 API 的数据结构。
"""
from datetime import datetime
from pydantic import BaseModel


class ServiceResponse(BaseModel):
    """服务信息响应体。"""
    id: int
    name: str
    type: str
    target: str
    check_interval: int
    timeout: int
    expected_status: int | None = None
    is_active: bool
    status: str
    host_id: int | None = None
    category: str | None = None  # 分类: middleware / business / infrastructure
    tags: dict | None = None
    created_at: datetime
    updated_at: datetime
    uptime_percent: float | None = None  # 24h 可用率

    model_config = {"from_attributes": True}


class ServiceCheckResponse(BaseModel):
    """服务健康检查结果响应体。"""
    id: int
    service_id: int
    status: str
    response_time_ms: float | None = None
    status_code: int | None = None
    error: str | None = None
    checked_at: datetime

    model_config = {"from_attributes": True}


class ServiceCheckReport(BaseModel):
    """Agent 上报服务检查结果的请求体。"""
    service_id: int
    status: str  # up / down
    response_time_ms: float | None = None
    status_code: int | None = None
    error: str | None = None
    checked_at: datetime | None = None
