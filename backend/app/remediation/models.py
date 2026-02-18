"""
修复模块的 Pydantic 数据模型。

用于模块内部数据传递，与 SQLAlchemy ORM 模型互补。
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

UTC = timezone.utc
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, enum.Enum):
    """三级风险分类。"""
    AUTO = "auto"
    CONFIRM = "confirm"
    BLOCK = "block"


class Diagnosis(BaseModel):
    """AI 诊断结果。"""
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_runbook: Optional[str] = None
    reasoning: str = ""
    additional_context: dict[str, Any] = Field(default_factory=dict)


class RunbookStep(BaseModel):
    """Runbook 中的单条命令。"""
    description: str
    command: str
    timeout_seconds: int = 30


class RunbookDefinition(BaseModel):
    """完整的 Runbook 定义。"""
    name: str
    description: str
    match_alert_types: list[str]
    match_keywords: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.CONFIRM
    commands: list[RunbookStep]
    verify_commands: list[RunbookStep] = Field(default_factory=list)
    cooldown_seconds: int = 300


class CommandResult(BaseModel):
    """单条命令的执行结果。"""
    command: str
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    executed: bool = True
    duration_ms: int = 0


class RemediationAlert(BaseModel):
    """传入修复模块的告警数据（从 VigilOps Alert ORM 转换）。"""
    alert_id: int
    alert_type: str
    severity: str = "warning"
    host: str = "unknown"
    host_id: Optional[int] = None
    message: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def summary(self) -> str:
        return f"[{self.severity}] {self.alert_type} on {self.host}: {self.message}"


class RemediationResult(BaseModel):
    """修复流程的最终结果。"""
    alert_id: int
    success: bool
    runbook_name: Optional[str] = None
    diagnosis: Optional[Diagnosis] = None
    risk_level: Optional[RiskLevel] = None
    command_results: list[CommandResult] = Field(default_factory=list)
    verification_passed: Optional[bool] = None
    blocked_reason: Optional[str] = None
    escalated: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def summary(self) -> str:
        if self.blocked_reason:
            return f"BLOCKED: {self.blocked_reason}"
        status = "SUCCESS" if self.success else "FAILED"
        rb = self.runbook_name or "none"
        return f"{status} via runbook={rb}, verified={self.verification_passed}"
