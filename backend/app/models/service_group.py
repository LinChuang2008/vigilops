"""
服务组模型

跨主机同名服务归组（如多台机器上的 redis、nginx）。
"""
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ServiceGroup(Base):
    """服务组表，跨主机同名服务归组。"""
    __tablename__ = "service_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)  # 服务名（如 "redis"）
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # web/db/cache/app/other
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
