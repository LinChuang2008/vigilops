"""
自定义 Runbook 请求/响应模型 (Custom Runbook Request/Response Models)
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RunbookStepSchema(BaseModel):
    """单个执行步骤"""
    name: str = Field(..., min_length=1, max_length=200)
    command: str = Field(..., min_length=1, max_length=2000)
    timeout_sec: int = Field(default=30, ge=1, le=3600)
    rollback_command: Optional[str] = Field(default=None, max_length=2000)


class CustomRunbookCreate(BaseModel):
    """创建自定义 Runbook"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    trigger_keywords: List[str] = Field(default_factory=list)
    risk_level: str = Field(default="manual")
    steps: List[RunbookStepSchema] = Field(..., min_length=1)
    safety_checks: List[str] = Field(default_factory=list)
    is_active: bool = True

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        allowed = {"auto", "confirm", "manual", "block"}
        if v not in allowed:
            raise ValueError(f"risk_level must be one of {allowed}")
        return v

    @field_validator("trigger_keywords")
    @classmethod
    def validate_keywords(cls, v: list) -> list:
        return [kw.strip() for kw in v if kw.strip()]


class CustomRunbookUpdate(BaseModel):
    """更新自定义 Runbook"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    trigger_keywords: Optional[List[str]] = None
    risk_level: Optional[str] = None
    steps: Optional[List[RunbookStepSchema]] = None
    safety_checks: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"auto", "confirm", "manual", "block"}
            if v not in allowed:
                raise ValueError(f"risk_level must be one of {allowed}")
        return v


class CustomRunbookResponse(BaseModel):
    """自定义 Runbook 响应"""
    id: int
    name: str
    description: str
    trigger_keywords: List[str]
    risk_level: str
    steps: list
    safety_checks: List[str]
    created_by: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunbookListResponse(BaseModel):
    """Runbook 列表响应 (含内置+自定义)"""
    items: list
    total: int


class DryRunRequest(BaseModel):
    """Dry-run 请求"""
    variables: dict = Field(default_factory=dict)


class DryRunStepResult(BaseModel):
    """Dry-run 单步结果"""
    step_name: str
    resolved_command: str
    timeout_sec: int
    rollback_command: Optional[str] = None
    safety_check_passed: bool
    safety_message: str = "OK"


class DryRunResponse(BaseModel):
    """Dry-run 响应"""
    runbook_name: str
    risk_level: str
    total_steps: int
    steps: List[DryRunStepResult]
    all_safe: bool
