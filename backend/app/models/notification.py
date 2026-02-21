"""
通知模型 (Notification Model)

定义通知渠道和通知发送日志的表结构，支持多种通知方式的配置管理和发送记录。
为告警通知系统提供渠道管理、消息发送和状态跟踪功能。

Defines table structures for notification channels and notification sending logs,
supporting configuration management and sending records for various notification methods.
Provides channel management, message sending, and status tracking functions for the alert notification system.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Boolean, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationChannel(Base):
    """
    通知渠道表 (Notification Channel Table)
    
    存储各种通知方式的配置信息，如 Webhook、钉钉、飞书、企微、邮件等。
    每个渠道包含名称、类型、配置参数和启用状态，为通知系统提供灵活的渠道管理。
    
    Table for storing configuration information for various notification methods
    such as Webhook, DingTalk, Feishu, WeCom, email, etc. Each channel contains
    name, type, configuration parameters, and enabled status.
    """
    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 渠道名称 (Channel Name)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="webhook")  # 渠道类型：webhook/dingtalk/feishu/wecom/email (Channel Type)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)  # 渠道配置 JSON，如 {"url": "...", "headers": {...}} (Channel Configuration JSON)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否启用该渠道 (Is Channel Enabled)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 创建时间 (Creation Time)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 更新时间 (Update Time)


class NotificationLog(Base):
    """
    通知发送日志表 (Notification Log Table)
    
    记录每次通知发送的详细结果，包括发送状态、响应码、错误信息和重试次数。
    为通知系统提供发送历史追踪和故障排查能力，支持通知可靠性分析。
    
    Table for recording detailed results of each notification sending, including
    sending status, response codes, error information, and retry counts.
    Provides sending history tracking and troubleshooting capabilities for the notification system.
    """
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    alert_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)  # 告警 ID (Alert ID)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 通知渠道 ID (Channel ID)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 发送状态：成功/失败 (Send Status: sent/failed)
    response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # HTTP 响应码 (HTTP Response Code)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 错误信息描述 (Error Message Description)
    retries: Mapped[int] = mapped_column(Integer, default=0)  # 重试次数 (Retry Count)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 发送时间 (Send Time)
