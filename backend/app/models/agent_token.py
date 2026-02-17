"""
Agent 令牌模型

定义监控代理认证令牌的表结构。
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentToken(Base):
    """Agent 令牌表，存储代理认证令牌的哈希值和元数据。"""
    __tablename__ = "agent_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # SHA-256 哈希
    token_prefix: Mapped[str] = mapped_column(String(8), nullable=False)  # 前 8 位用于展示
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)  # 创建人 user_id
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
