"""
运维报告模型 (Operations Report Model)

定义 AI 自动生成的运维报告（日报/周报）的表结构，提供运维数据的定期汇总和分析。
包含报告内容、生成状态、时间范围等信息，为运维管理提供数据洞察支持。

Defines the table structure for AI-generated operations reports (daily/weekly),
providing regular summaries and analysis of operational data. Includes report content,
generation status, time range, and other information for operational management insights.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Report(Base):
    """
    运维报告表 (Operations Report Table)
    
    存储 AI 自动生成的运维日报和周报，包含系统状态、告警统计、性能趋势等综合分析。
    为运维团队提供定期的系统运行情况总结和数据洞察，支持运维决策和优化。
    
    Table for storing AI-generated daily and weekly operations reports,
    including system status, alert statistics, performance trends, and comprehensive analysis.
    Provides regular system operation summaries and data insights for the operations team.
    """
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    title: Mapped[str] = mapped_column(String(255), nullable=False)  # 报告标题，如 "日报 2026-02-17" (Report Title)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 报告类型：日报/周报 (Report Type: daily/weekly)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 报告统计起始时间 (Period Start Time)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 报告统计结束时间 (Period End Time)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")  # Markdown 格式的报告正文 (Report Content in Markdown)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")  # AI 生成的简短摘要 (AI-Generated Summary)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")  # 生成状态：生成中/已完成/失败 (Generation Status: generating/completed/failed)
    generated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 手动触发时的用户 ID (User ID for Manual Trigger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 报告创建时间 (Report Creation Time)
