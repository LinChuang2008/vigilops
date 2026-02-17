"""
Agent 令牌认证模块

验证监控代理上报数据时携带的 Bearer Token，并更新最近使用时间。
"""
import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent_token import AgentToken

# Agent 专用 Bearer Token 认证方案
agent_security = HTTPBearer()


async def verify_agent_token(
    credentials: HTTPAuthorizationCredentials = Depends(agent_security),
    db: AsyncSession = Depends(get_db),
) -> AgentToken:
    """验证 Agent Bearer Token，返回对应的 AgentToken 记录。"""
    raw_token = credentials.credentials
    # 计算 SHA-256 哈希与数据库存储的哈希比对
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    result = await db.execute(
        select(AgentToken).where(
            AgentToken.token_hash == token_hash,
            AgentToken.is_active == True,  # noqa: E712
        )
    )
    agent_token = result.scalar_one_or_none()
    if agent_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked agent token")

    # 更新令牌最后使用时间
    await db.execute(
        update(AgentToken)
        .where(AgentToken.id == agent_token.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return agent_token
