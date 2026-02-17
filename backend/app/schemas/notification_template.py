"""
通知模板请求/响应模型

定义通知模板 CRUD 操作的数据结构。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationTemplateCreate(BaseModel):
    """创建通知模板请求体。"""
    name: str
    channel_type: str  # webhook / email / dingtalk / feishu / wecom / all
    subject_template: Optional[str] = None
    body_template: str
    is_default: bool = False


class NotificationTemplateUpdate(BaseModel):
    """更新通知模板请求体（所有字段可选）。"""
    name: Optional[str] = None
    channel_type: Optional[str] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    is_default: Optional[bool] = None


class NotificationTemplateResponse(BaseModel):
    """通知模板响应体。"""
    id: int
    name: str
    channel_type: str
    subject_template: Optional[str]
    body_template: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
