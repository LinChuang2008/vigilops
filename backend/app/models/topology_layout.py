"""
拓扑图布局模型

存储用户自定义的拓扑图节点位置。
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, JSON, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TopologyLayout(Base):
    """拓扑图布局表，存储用户自定义的节点位置"""
    __tablename__ = "topology_layouts"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_topology_layout_user_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="default")
    positions: Mapped[dict] = mapped_column(JSON, default=dict)  # {"node_id": {"x": 100, "y": 200}}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
