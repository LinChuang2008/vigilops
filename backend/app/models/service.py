"""
服务模型 (Service Model)

定义服务监控和健康检查相关的表结构，支持 HTTP 和 TCP 服务的可用性监控。
包含服务配置、健康检查记录和状态跟踪，为服务可用性监控提供完整的数据支持。

Defines table structures for service monitoring and health checking,
supporting availability monitoring for HTTP and TCP services.
Includes service configuration, health check records, and status tracking.
"""
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Boolean, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Service(Base):
    """
    服务表 (Service Table)
    
    存储被监控的 HTTP 和 TCP 服务信息，包含健康检查配置和当前状态。
    支持服务分类、标签管理和灵活的检查策略配置，为服务可用性监控提供基础数据。
    
    Table for storing monitored HTTP and TCP service information,
    including health check configuration and current status.
    Supports service categorization, tag management, and flexible check strategy configuration.
    """
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 服务名称 (Service Name)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # 服务类型：HTTP/TCP (Service Type: http/tcp)
    target: Mapped[str] = mapped_column(String(500), nullable=False)  # 监控目标：URL 或 host:port (Monitor Target: URL or host:port)
    check_interval: Mapped[int] = mapped_column(Integer, default=60)  # 健康检查间隔秒数 (Health Check Interval in Seconds)
    timeout: Mapped[int] = mapped_column(Integer, default=10)  # 检查超时时间秒数 (Check Timeout in Seconds)
    expected_status: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 期望的 HTTP 状态码 (Expected HTTP Status Code)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否启用监控 (Is Monitoring Enabled)
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # 服务状态：正常/异常/未知 (Service Status: up/down/unknown)
    host_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 关联主机 ID（可选） (Associated Host ID, Optional)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)  # 服务分类：中间件/业务/基础设施 (Service Category: middleware/business/infrastructure)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 服务标签 JSON 数据 (Service Tags JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 创建时间 (Creation Time)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 更新时间 (Update Time)


class ServiceCheck(Base):
    """
    服务检查记录表 (Service Check Record Table)
    
    存储每次健康检查的详细结果，包括响应时间、状态码和错误信息。
    为服务可用性分析、SLA 计算和故障排查提供历史数据支持。
    
    Table for storing detailed results of each health check, including
    response time, status codes, and error information. Provides historical
    data support for service availability analysis, SLA calculation, and troubleshooting.
    """
    __tablename__ = "service_checks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    service_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)  # 服务 ID (Service ID)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 检查结果：正常/异常 (Check Result: up/down)
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)  # 响应时间毫秒数 (Response Time in Milliseconds)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)  # HTTP 状态码 (HTTP Status Code)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 错误信息 (Error Message)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # 检查时间 (Check Time)
