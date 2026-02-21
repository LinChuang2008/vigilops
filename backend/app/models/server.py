"""
服务器模型 (Server Model)

定义多服务器拓扑中的服务器表结构，用于管理集群中的物理和虚拟服务器。
支持服务器标签管理、状态跟踪和模拟数据标记，为服务拓扑构建提供基础设施信息。

Defines the server table structure for multi-server topology, managing physical
and virtual servers in clusters. Supports server tag management, status tracking,
and simulation data marking for service topology construction.
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Server(Base):
    """
    服务器表 (Server Table)
    
    存储拓扑系统中的物理服务器和虚拟服务器信息，支持集群化部署和多服务器管理。
    每个服务器包含基本信息、标签、状态和最后活跃时间，为服务拓扑图提供基础设施视图。
    
    Table for storing physical and virtual server information in the topology system,
    supporting clustered deployment and multi-server management. Each server contains
    basic information, tags, status, and last activity time for infrastructure visualization.
    """
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)  # 服务器主机名 (Server Hostname)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IP 地址（支持 IPv6） (IP Address)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 显示标签，如 "Web-01" (Display Label)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)  # 服务器标签 JSON，如 {"env":"prod","region":"cn-east"} (Server Tags JSON)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")  # 在线状态：在线/离线/未知 (Status: online/offline/unknown)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # 最后活跃时间 (Last Seen Time)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否为模拟数据 (Is Simulated Data)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 创建时间 (Creation Time)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 更新时间 (Update Time)
