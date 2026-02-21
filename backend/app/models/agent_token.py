"""
Agent 令牌模型 (Agent Token Model)

定义监控代理认证令牌的表结构，用于管理和验证监控 Agent 的身份认证。
每个 Agent Token 存储加密的令牌哈希值以及相关的元数据信息。

Agent tokens are used for authenticating monitoring agents that report data to the system.
Tokens are hashed for security and include metadata for management purposes.
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentToken(Base):
    """
    Agent 令牌表 (Agent Token Table)
    
    存储代理认证令牌的哈希值和元数据，用于验证监控 Agent 的身份。
    每个令牌包含名称、哈希值、创建信息和使用状态等字段。
    
    Table structure for storing agent authentication tokens with hash values and metadata.
    Used to validate the identity of monitoring agents reporting system data.
    """
    __tablename__ = "agent_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 令牌名称 (Token Name)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # SHA-256 哈希值 (SHA-256 Hash)
    token_prefix: Mapped[str] = mapped_column(String(8), nullable=False)  # 令牌前缀，用于界面展示 (Token Prefix for Display)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)  # 创建人用户 ID (Creator User ID)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否激活状态 (Active Status)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 创建时间 (Creation Time)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # 最后使用时间 (Last Used Time)
