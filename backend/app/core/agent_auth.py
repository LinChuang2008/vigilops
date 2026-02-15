import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent_token import AgentToken

agent_security = HTTPBearer()


async def verify_agent_token(
    credentials: HTTPAuthorizationCredentials = Depends(agent_security),
    db: AsyncSession = Depends(get_db),
) -> AgentToken:
    """Dependency that validates an agent bearer token."""
    raw_token = credentials.credentials
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

    # Update last_used_at
    await db.execute(
        update(AgentToken)
        .where(AgentToken.id == agent_token.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return agent_token
