"""
告警模型

定义告警规则和告警事件的表结构。
"""
from datetime import datetime, time
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, JSON, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AlertRule(Base):
    """告警规则表，定义触发告警的条件。"""
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")  # critical / warning / info
    metric: Mapped[str] = mapped_column(String(100), nullable=False)  # cpu_percent, memory_percent 等
    operator: Mapped[str] = mapped_column(String(10), nullable=False, default=">")  # >, <, >=, <=, ==, !=
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)  # 持续超过阈值的秒数
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否为内置规则
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default="host")  # host / service
    target_filter: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 可选过滤条件
    # 日志关键字告警字段
    rule_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="metric")  # metric / log_keyword / db_metric
    log_keyword: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    log_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    log_service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # 数据库告警字段
    db_metric_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    db_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 冷却期与静默窗口
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300)
    silence_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)  # 静默开始时间
    silence_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)  # 静默结束时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Alert(Base):
    """告警事件表，记录已触发的告警。"""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    host_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    service_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical / warning / info
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="firing")  # firing / resolved / acknowledged / remediated
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 触发时的指标值
    threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 触发时的阈值
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 确认人 user_id
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
