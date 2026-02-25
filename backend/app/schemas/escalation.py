"""
告警升级模式定义 (Alert Escalation Schema Definitions)

定义告警升级相关的 API 请求和响应模式，包括数据验证、序列化规则。
提供类型安全的接口定义，确保升级配置和历史记录的数据一致性。

Defines API request and response schemas for alert escalation,
including data validation and serialization rules.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EscalationLevel(BaseModel):
    """升级级别配置 (Escalation Level Configuration)"""
    level: int = Field(..., ge=1, description="升级级别")
    delay_minutes: int = Field(..., ge=1, description="延迟分钟数")
    severity: str = Field(..., description="升级后严重程度")


class EscalationRuleBase(BaseModel):
    """升级规则基础模式 (Escalation Rule Base Schema)"""
    alert_rule_id: int = Field(..., description="告警规则ID")
    name: str = Field(..., min_length=1, max_length=255, description="升级规则名称")
    is_enabled: bool = Field(True, description="是否启用")
    escalation_levels: List[EscalationLevel] = Field(..., description="升级级别配置")


class EscalationRuleCreate(EscalationRuleBase):
    """创建升级规则请求模式 (Create Escalation Rule Request Schema)"""
    pass


class EscalationRuleUpdate(BaseModel):
    """更新升级规则请求模式 (Update Escalation Rule Request Schema)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="升级规则名称")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    escalation_levels: Optional[List[EscalationLevel]] = Field(None, description="升级级别配置")


class EscalationRuleResponse(EscalationRuleBase):
    """升级规则响应模式 (Escalation Rule Response Schema)"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertEscalationBase(BaseModel):
    """告警升级记录基础模式 (Alert Escalation Base Schema)"""
    alert_id: int = Field(..., description="告警ID")
    escalation_rule_id: Optional[int] = Field(None, description="升级规则ID")
    from_severity: str = Field(..., description="原严重程度")
    to_severity: str = Field(..., description="升级后严重程度")
    escalation_level: int = Field(..., ge=1, description="升级级别")
    escalated_by_system: bool = Field(True, description="是否系统自动升级")
    message: Optional[str] = Field(None, description="升级消息")


class AlertEscalationCreate(AlertEscalationBase):
    """创建告警升级记录请求模式 (Create Alert Escalation Request Schema)"""
    pass


class AlertEscalationResponse(AlertEscalationBase):
    """告警升级记录响应模式 (Alert Escalation Response Schema)"""
    id: int
    escalated_at: datetime

    model_config = {"from_attributes": True}


class ManualEscalationRequest(BaseModel):
    """手动升级请求模式 (Manual Escalation Request Schema)"""
    to_severity: str = Field(..., description="目标严重程度")
    message: Optional[str] = Field(None, description="升级原因")


class EscalationStatsResponse(BaseModel):
    """升级统计响应模式 (Escalation Statistics Response Schema)"""
    total_escalations: int = Field(..., description="总升级次数")
    today_escalations: int = Field(..., description="今日升级次数")
    escalations_by_severity: dict = Field(..., description="按严重程度统计")
    escalations_by_level: dict = Field(..., description="按升级级别统计")