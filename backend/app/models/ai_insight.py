"""
AI 洞察模型

定义 AI 分析结果的表结构，存储异常检测、根因分析、对话等结果。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIInsight(Base):
    """AI 洞察表，存储 AI 引擎产生的分析结果。"""
    __tablename__ = "ai_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)  # anomaly / root_cause / chat
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")  # info / warning / critical
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 完整分析结果 JSON
    related_host_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("hosts.id"), nullable=True)
    related_alert_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("alerts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")  # new / acknowledged / resolved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
