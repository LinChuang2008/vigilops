"""
服务器-服务关联模型

服务器 ↔ 服务组 多对多关系 + 运行状态。
"""
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ServerService(Base):
    """服务器-服务关联表，记录每台服务器上运行的服务及其状态。"""
    __tablename__ = "server_services"
    __table_args__ = (
        UniqueConstraint("server_id", "group_id", "port", name="uq_server_service_port"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")  # running/stopped/error
    cpu_percent: Mapped[float] = mapped_column(Float, default=0)
    mem_mb: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
