"""
Agent 令牌请求/响应模型

定义 Agent Token 创建和查询的数据结构。
"""
from datetime import datetime
from pydantic import BaseModel


class AgentTokenCreate(BaseModel):
    """创建 Agent Token 请求体。"""
    name: str


class AgentTokenResponse(BaseModel):
    """Agent Token 响应体（不含明文令牌）。"""
    id: int
    name: str
    token_prefix: str
    is_active: bool
    created_by: int
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentTokenCreated(AgentTokenResponse):
    """创建成功时返回的响应体，包含完整令牌（仅此一次可见）。"""
    token: str
