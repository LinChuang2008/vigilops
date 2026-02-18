"""
服务器模型

定义多服务器拓扑中的服务器表结构。
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Server(Base):
    """服务器表，存储拓扑中的物理/虚拟服务器信息。"""
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 显示名（如 "Web-01"）
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)  # {"env":"prod","region":"cn-east"}
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")  # online/offline/unknown
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)  # 标记模拟数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
