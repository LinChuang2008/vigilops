"""
服务器-服务关联模型 (Server-Service Association Model)

定义服务器与服务组的多对多关系表，记录每台服务器上运行的服务实例及其运行状态。
包含端口、进程 ID、资源使用情况等详细信息，为服务拓扑和监控提供基础数据。

Defines a many-to-many relationship table between servers and service groups,
recording service instances running on each server and their operational status.
Includes port, process ID, resource usage, and other detailed information.
"""
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ServerService(Base):
    """
    服务器-服务关联表 (Server-Service Association Table)
    
    记录服务器与服务组之间的多对多关联关系，以及每个服务实例的运行状态。
    每条记录代表一个服务器上运行的一个服务实例，包含端口、进程信息和资源使用情况。
    
    Table for recording many-to-many associations between servers and service groups,
    along with the operational status of each service instance. Each record represents
    a service instance running on a server, including port, process info, and resource usage.
    """
    __tablename__ = "server_services"
    __table_args__ = (
        UniqueConstraint("server_id", "group_id", "port", name="uq_server_service_port"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 服务器 ID (Server ID)
    group_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 服务组 ID (Service Group ID)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 服务监听端口 (Service Port)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 进程 ID (Process ID)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")  # 运行状态：运行中/已停止/错误 (Status: running/stopped/error)
    cpu_percent: Mapped[float] = mapped_column(Float, default=0)  # CPU 使用率百分比 (CPU Usage Percentage)
    mem_mb: Mapped[float] = mapped_column(Float, default=0)  # 内存使用量 MB (Memory Usage in MB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 状态更新时间 (Status Update Time)
