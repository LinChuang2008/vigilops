"""
SLA 模型

定义 SLA 规则和违规事件的表结构。
"""
from datetime import datetime

from sqlalchemy import String, Integer, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SLARule(Base):
    """SLA 规则表，存储服务的 SLA 目标配置。"""
    __tablename__ = "sla_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=99.90)
    calculation_window: Mapped[str] = mapped_column(String(20), default="monthly")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SLAViolation(Base):
    """SLA 违规事件表，记录服务不可用的时段。"""
    __tablename__ = "sla_violations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sla_rule_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
