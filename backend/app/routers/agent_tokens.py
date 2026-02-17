"""
Agent 令牌管理路由

提供 Agent Token 的创建、列表查询和吊销接口（仅管理员可用）。
"""
import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.agent_token import AgentToken
from app.models.user import User
from app.schemas.agent_token import AgentTokenCreate, AgentTokenCreated, AgentTokenResponse

router = APIRouter(prefix="/api/v1/agent-tokens", tags=["agent-tokens"])


def _hash_token(token: str) -> str:
    """计算令牌的 SHA-256 哈希值。"""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("", response_model=AgentTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_agent_token(
    body: AgentTokenCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的 Agent Token（仅管理员）。"""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    # 生成随机令牌，前缀 vop_
    raw_token = f"vop_{secrets.token_hex(24)}"
    token_hash = _hash_token(raw_token)

    agent_token = AgentToken(
        name=body.name,
        token_hash=token_hash,
        token_prefix=raw_token[:8],
        created_by=user.id,
    )
    db.add(agent_token)
    await db.commit()
    await db.refresh(agent_token)

    data = {
        "id": agent_token.id,
        "name": agent_token.name,
        "token_prefix": agent_token.token_prefix,
        "is_active": agent_token.is_active,
        "created_by": agent_token.created_by,
        "created_at": agent_token.created_at,
        "last_used_at": agent_token.last_used_at,
        "token": raw_token,
    }
    return AgentTokenCreated(**data)


@router.get("", response_model=list[AgentTokenResponse])
async def list_agent_tokens(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出所有 Agent Token（仅管理员）。"""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    result = await db.execute(
        select(AgentToken).order_by(AgentToken.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_agent_token(
    token_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """吊销指定的 Agent Token（仅管理员）。"""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    result = await db.execute(select(AgentToken).where(AgentToken.id == token_id))
    agent_token = result.scalar_one_or_none()
    if not agent_token:
        raise HTTPException(status_code=404, detail="Token not found")

    agent_token.is_active = False
    await db.commit()
