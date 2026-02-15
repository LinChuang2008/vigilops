from datetime import datetime

from pydantic import BaseModel


class LogEntryItem(BaseModel):
    host_id: int
    service: str | None = None
    source: str | None = None
    level: str | None = None
    message: str
    timestamp: datetime


class LogBatchRequest(BaseModel):
    logs: list[LogEntryItem]


class LogBatchResponse(BaseModel):
    received: int


class LogEntryResponse(BaseModel):
    id: int
    host_id: int
    service: str | None = None
    source: str | None = None
    level: str | None = None
    message: str
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class LogSearchResponse(BaseModel):
    items: list[LogEntryResponse]
    total: int
    page: int
    page_size: int


class LevelCount(BaseModel):
    level: str
    count: int


class TimeCount(BaseModel):
    time_bucket: datetime
    count: int


class LogStatsResponse(BaseModel):
    by_level: list[LevelCount]
    by_time: list[TimeCount]
