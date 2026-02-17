"""
日志条目模型

定义日志存储的表结构，支持按主机、服务、级别等维度检索。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogEntry(Base):
    """日志条目表，存储 Agent 采集的日志数据。"""
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id"), nullable=False, index=True)
    service: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(512), nullable=True)  # 日志来源文件路径
    level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)  # DEBUG/INFO/WARN/ERROR/FATAL
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
