"""
日志相关请求/响应模型

定义日志查询、批量写入、统计等 API 的数据结构。
"""
from datetime import datetime

from pydantic import BaseModel


class LogEntryItem(BaseModel):
    """单条日志条目（Agent 上报用）。"""
    host_id: int
    service: str | None = None
    source: str | None = None
    level: str | None = None
    message: str
    timestamp: datetime


class LogBatchRequest(BaseModel):
    """批量日志上报请求体。"""
    logs: list[LogEntryItem]


class LogBatchResponse(BaseModel):
    """批量日志上报响应体。"""
    received: int


class LogEntryResponse(BaseModel):
    """日志条目查询响应体。"""
    id: int
    host_id: int
    hostname: str | None = None
    service: str | None = None
    source: str | None = None
    level: str | None = None
    message: str
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class LogSearchResponse(BaseModel):
    """日志搜索分页响应体。"""
    items: list[LogEntryResponse]
    total: int
    page: int
    page_size: int


class LevelCount(BaseModel):
    """按日志级别统计的计数项。"""
    level: str
    count: int


class TimeCount(BaseModel):
    """按时间桶统计的计数项。"""
    time_bucket: datetime
    count: int


class LogStatsResponse(BaseModel):
    """日志统计响应体。"""
    by_level: list[LevelCount]
    by_time: list[TimeCount]
