"""
运维报告模型

定义 AI 生成的运维报告（日报/周报）的表结构。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Report(Base):
    """运维报告表，存储 AI 自动生成的日报和周报。"""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)  # "日报 2026-02-17"
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "daily" / "weekly"
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 报告覆盖起始时间
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 报告覆盖结束时间
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")  # Markdown 报告正文
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")  # AI 生成的简短摘要
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")  # generating/completed/failed
    generated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 手动触发时的 user_id
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
