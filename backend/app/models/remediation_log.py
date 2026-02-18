"""
修复日志模型

记录每次自动修复的完整轨迹：诊断结果、执行命令、验证结果。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RemediationLog(Base):
    """修复日志表，记录每次自动修复的完整生命周期。"""
    __tablename__ = "remediation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    host_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending/diagnosing/executing/verifying/success/failed/escalated/pending_approval/approved/rejected
    risk_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # auto/confirm/block
    runbook_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    diagnosis_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    command_results_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    verification_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")  # auto/manual
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
