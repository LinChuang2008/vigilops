"""
告警升级模型 (Alert Escalation Model)

定义告警升级规则和升级历史记录的数据结构，支持自动化的告警升级管理。
包含升级规则配置、升级触发条件、升级历史追踪等功能的数据模型。

Defines data structures for alert escalation rules and history records,
supporting automated alert escalation management.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EscalationRule(Base):
    """
    升级规则表 (Escalation Rule Table)
    
    定义告警自动升级的配置规则，包括升级条件、升级级别、时间间隔等。
    支持多级升级策略，实现告警管理的自动化流程。
    
    Table for defining automated alert escalation configuration rules,
    including escalation conditions, levels, and time intervals.
    """
    __tablename__ = "escalation_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    alert_rule_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 告警规则 ID (Alert Rule ID)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 升级规则名称 (Escalation Rule Name)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否启用 (Is Enabled)
    escalation_levels: Mapped[dict] = mapped_column(JSON, nullable=False)  # 升级级别配置 JSON (Escalation Levels Config)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 创建时间 (Creation Time)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 更新时间 (Update Time)


class AlertEscalation(Base):
    """
    告警升级记录表 (Alert Escalation Record Table)
    
    记录告警升级的历史信息，包括升级时间、级别变化、升级原因等。
    提供告警升级过程的完整审计追踪，便于问题分析和流程优化。
    
    Table for recording alert escalation history, including escalation time,
    level changes, and escalation reasons. Provides complete audit trail.
    """
    __tablename__ = "alert_escalations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    alert_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 告警 ID (Alert ID)
    escalation_rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 升级规则 ID (Escalation Rule ID)
    from_severity: Mapped[str] = mapped_column(String(20), nullable=False)  # 原严重程度 (Original Severity)
    to_severity: Mapped[str] = mapped_column(String(20), nullable=False)  # 升级后严重程度 (Escalated Severity)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 升级级别 (Escalation Level)
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 升级时间 (Escalation Time)
    escalated_by_system: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否系统自动升级 (Is System Escalated)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 升级消息 (Escalation Message)