"""
主机指标模型

定义主机性能指标的表结构，包括 CPU、内存、磁盘、网络等数据。
"""
from datetime import datetime

from sqlalchemy import Integer, Float, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HostMetric(Base):
    """主机指标表，存储 Agent 上报的性能数据。"""
    __tablename__ = "host_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    # CPU 指标
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_load_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_load_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_load_15: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 内存指标
    memory_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 磁盘指标
    disk_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_total_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 网络指标
    net_bytes_sent: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    net_bytes_recv: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    net_send_rate_kb: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_recv_rate_kb: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_packet_loss_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 关联拓扑服务器（可选）
    server_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # 记录时间
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
