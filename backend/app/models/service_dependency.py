"""
服务依赖关系模型

定义服务之间的依赖/调用关系，用于拓扑图可视化。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ServiceDependency(Base):
    """服务依赖关系表，记录服务间的调用和依赖关系。"""
    __tablename__ = "service_dependencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_service_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_service_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dependency_type: Mapped[str] = mapped_column(String(50), default="calls")  # calls / depends_on / publishes_to
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
