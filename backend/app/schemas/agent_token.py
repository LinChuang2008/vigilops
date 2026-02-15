from datetime import datetime
from pydantic import BaseModel


class AgentTokenCreate(BaseModel):
    name: str


class AgentTokenResponse(BaseModel):
    id: int
    name: str
    token_prefix: str
    is_active: bool
    created_by: int
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentTokenCreated(AgentTokenResponse):
    """Returned only on creation - includes the full token (only time it's visible)."""
    token: str
