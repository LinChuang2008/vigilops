from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── AlertRule ──

class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    severity: str = "warning"
    metric: str = ""
    operator: str = ">"
    threshold: float = 0
    duration_seconds: int = 300
    is_enabled: bool = True
    target_type: str = "host"
    target_filter: Optional[dict] = None
    rule_type: str = "metric"
    log_keyword: Optional[str] = None
    log_level: Optional[str] = None
    log_service: Optional[str] = None
    db_metric_name: Optional[str] = None
    db_id: Optional[int] = None
    cooldown_seconds: int = 300
    silence_start: Optional[str] = None
    silence_end: Optional[str] = None


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    metric: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    duration_seconds: Optional[int] = None
    is_enabled: Optional[bool] = None
    target_filter: Optional[dict] = None
    rule_type: Optional[str] = None
    log_keyword: Optional[str] = None
    log_level: Optional[str] = None
    log_service: Optional[str] = None
    db_metric_name: Optional[str] = None
    db_id: Optional[int] = None
    cooldown_seconds: Optional[int] = None
    silence_start: Optional[str] = None
    silence_end: Optional[str] = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    severity: str
    metric: str
    operator: str
    threshold: float
    duration_seconds: int
    is_builtin: bool
    is_enabled: bool
    target_type: str
    target_filter: Optional[dict]
    rule_type: Optional[str] = "metric"
    log_keyword: Optional[str] = None
    log_level: Optional[str] = None
    log_service: Optional[str] = None
    db_metric_name: Optional[str] = None
    db_id: Optional[int] = None
    cooldown_seconds: int = 300
    silence_start: Optional[str] = None
    silence_end: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Alert ──

class AlertResponse(BaseModel):
    id: int
    rule_id: int
    host_id: Optional[int]
    service_id: Optional[int]
    severity: str
    status: str
    title: str
    message: Optional[str]
    metric_value: Optional[float]
    threshold: Optional[float]
    fired_at: datetime
    resolved_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
