"""
通知相关请求/响应模型

定义通知渠道和通知日志的数据结构。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationChannelCreate(BaseModel):
    """创建通知渠道请求体。"""
    name: str
    type: str = "webhook"
    config: dict  # {"url": "...", "headers": {...}}
    is_enabled: bool = True


class NotificationChannelUpdate(BaseModel):
    """更新通知渠道请求体（所有字段可选）。"""
    name: Optional[str] = None
    config: Optional[dict] = None
    is_enabled: Optional[bool] = None


class NotificationChannelResponse(BaseModel):
    """通知渠道响应体。"""
    id: int
    name: str
    type: str
    config: dict
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationLogResponse(BaseModel):
    """通知发送日志响应体。"""
    id: int
    alert_id: int
    channel_id: int
    status: str
    response_code: Optional[int]
    error: Optional[str]
    retries: int
    sent_at: datetime

    model_config = {"from_attributes": True}
