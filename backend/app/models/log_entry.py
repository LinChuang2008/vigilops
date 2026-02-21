"""
日志条目模型 (Log Entry Model)

定义日志存储的表结构，支持按主机、服务、级别等多维度检索和分析。
Agent 采集各种服务和系统日志，统一存储到该表中，为日志分析和告警提供数据基础。

Defines the table structure for log storage, supporting multi-dimensional
retrieval and analysis by host, service, level, etc. Agents collect various
service and system logs, storing them uniformly in this table.
"""
from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogEntry(Base):
    """
    日志条目表 (Log Entry Table)
    
    存储 Agent 采集的各种日志数据，包括应用日志、系统日志等。
    支持按时间、主机、服务、日志级别等维度进行高效检索和分析，为运维决策提供日志支撑。
    
    Table for storing various log data collected by agents, including application logs
    and system logs. Supports efficient retrieval and analysis by time, host, service,
    log level, and other dimensions for operational decision support.
    """
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id"), nullable=False, index=True)  # 主机 ID (Host ID)
    service: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)  # 服务名称 (Service Name)
    source: Mapped[str | None] = mapped_column(String(512), nullable=True)  # 日志来源文件路径 (Log Source File Path)
    level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)  # 日志级别：DEBUG/INFO/WARN/ERROR/FATAL (Log Level)
    message: Mapped[str] = mapped_column(Text, nullable=False)  # 日志内容消息 (Log Message Content)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)  # 日志产生时间 (Log Timestamp)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # 记录创建时间 (Record Creation Time)
