"""
Nginx Upstream 模型

存储从 Nginx 配置解析出的 upstream 后端信息。
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NginxUpstream(Base):
    """Nginx Upstream 表，存储 upstream 后端配置。"""
    __tablename__ = "nginx_upstreams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    upstream_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    backend_address: Mapped[str] = mapped_column(String(255), nullable=False)  # "10.0.0.2:8080"
    weight: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="up")  # up/down/backup
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
