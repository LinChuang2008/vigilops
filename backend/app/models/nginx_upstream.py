"""
Nginx Upstream 模型 (Nginx Upstream Model)

存储从 Nginx 配置文件中解析出的 upstream 后端服务器信息。
用于服务拓扑发现和负载均衡配置管理，支持后端服务器状态监控和权重管理。

Stores upstream backend server information parsed from Nginx configuration files.
Used for service topology discovery and load balancing configuration management,
supporting backend server status monitoring and weight management.
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NginxUpstream(Base):
    """
    Nginx Upstream 表 (Nginx Upstream Table)
    
    存储 Nginx 负载均衡器的 upstream 后端服务器配置信息。
    通过解析 Nginx 配置文件获取，用于构建服务拓扑图和监控负载均衡状态。
    
    Table for storing Nginx load balancer upstream backend server configuration information.
    Obtained by parsing Nginx configuration files, used for building service topology
    diagrams and monitoring load balancing status.
    """
    __tablename__ = "nginx_upstreams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 服务器 ID (Server ID)
    upstream_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Upstream 名称 (Upstream Name)
    backend_address: Mapped[str] = mapped_column(String(255), nullable=False)  # 后端服务器地址，如 "10.0.0.2:8080" (Backend Server Address)
    weight: Mapped[int] = mapped_column(Integer, default=1)  # 负载均衡权重 (Load Balancing Weight)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="up")  # 服务器状态：运行/宕机/备份 (Server Status: up/down/backup)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 配置解析时间 (Configuration Parse Time)
