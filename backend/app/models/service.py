"""
服务模型

定义服务监控和健康检查相关的表结构。
"""
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Boolean, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Service(Base):
    """服务表，存储被监控的 HTTP/TCP 服务信息。"""
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # http / tcp
    target: Mapped[str] = mapped_column(String(500), nullable=False)  # URL 或 host:port
    check_interval: Mapped[int] = mapped_column(Integer, default=60)  # 检查间隔（秒）
    timeout: Mapped[int] = mapped_column(Integer, default=10)  # 超时时间（秒）
    expected_status: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 期望的 HTTP 状态码
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # up / down / unknown
    host_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 关联主机（可选）
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)  # 分类: middleware / business / infrastructure
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ServiceCheck(Base):
    """服务检查记录表，存储每次健康检查的结果。"""
    __tablename__ = "service_checks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # up / down
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
