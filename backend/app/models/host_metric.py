"""
主机指标模型 (Host Metric Model)

定义主机性能指标的表结构，包括 CPU、内存、磁盘、网络等核心系统资源数据。
Agent 定期采集并上报这些指标，用于监控分析、告警触发和性能优化决策。

Defines the table structure for host performance metrics, including CPU, memory,
disk, network, and other core system resource data. Agents regularly collect
and report these metrics for monitoring analysis, alert triggering, and performance optimization.
"""
from datetime import datetime

from sqlalchemy import Integer, Float, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HostMetric(Base):
    """
    主机指标表 (Host Metric Table)
    
    存储 Agent 定期上报的主机性能指标数据，涵盖 CPU、内存、磁盘、网络等关键资源。
    为系统监控、告警判断、性能分析和容量规划提供基础数据支持。
    
    Table for storing host performance metric data regularly reported by agents,
    covering key resources such as CPU, memory, disk, and network.
    Provides foundational data support for system monitoring, alert decisions,
    performance analysis, and capacity planning.
    """
    __tablename__ = "host_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    host_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)  # 主机 ID (Host ID)
    # CPU 指标 (CPU Metrics)
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)  # CPU 使用率百分比 (CPU Usage Percentage)
    cpu_load_1: Mapped[float | None] = mapped_column(Float, nullable=True)  # 1分钟负载平均值 (1-minute Load Average)
    cpu_load_5: Mapped[float | None] = mapped_column(Float, nullable=True)  # 5分钟负载平均值 (5-minute Load Average)
    cpu_load_15: Mapped[float | None] = mapped_column(Float, nullable=True)  # 15分钟负载平均值 (15-minute Load Average)
    # 内存指标 (Memory Metrics)
    memory_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 已使用内存 MB (Used Memory in MB)
    memory_percent: Mapped[float | None] = mapped_column(Float, nullable=True)  # 内存使用率百分比 (Memory Usage Percentage)
    # 磁盘指标 (Disk Metrics)
    disk_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 磁盘已用空间 MB (Used Disk Space in MB)
    disk_total_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 磁盘总空间 MB (Total Disk Space in MB)
    disk_percent: Mapped[float | None] = mapped_column(Float, nullable=True)  # 磁盘使用率百分比 (Disk Usage Percentage)
    # 网络指标 (Network Metrics)
    net_bytes_sent: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 累计发送字节数 (Total Bytes Sent)
    net_bytes_recv: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 累计接收字节数 (Total Bytes Received)
    net_send_rate_kb: Mapped[float | None] = mapped_column(Float, nullable=True)  # 发送速率 KB/s (Send Rate in KB/s)
    net_recv_rate_kb: Mapped[float | None] = mapped_column(Float, nullable=True)  # 接收速率 KB/s (Receive Rate in KB/s)
    net_packet_loss_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # 网络丢包率百分比 (Packet Loss Rate Percentage)
    # 关联拓扑服务器（可选） (Related Topology Server, Optional)
    server_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # 拓扑服务器 ID (Topology Server ID)
    # 记录时间 (Record Time)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # 指标记录时间 (Metric Record Time)
