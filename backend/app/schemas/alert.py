from datetime import datetime
from pydantic import BaseModel


# ── AlertRule ──

class AlertRuleCreate(BaseModel):
    name: str
    description: str | None = None
    severity: str = "warning"
    metric: str
    operator: str = ">"
    threshold: float
    duration_seconds: int = 300
    is_enabled: bool = True
    target_type: str = "host"
    target_filter: dict | None = None


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    severity: str | None = None
    metric: str | None = None
    operator: str | None = None
    threshold: float | None = None
    duration_seconds: int | None = None
    is_enabled: bool | None = None
    target_filter: dict | None = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    severity: str
    metric: str
    operator: str
    threshold: float
    duration_seconds: int
    is_builtin: bool
    is_enabled: bool
    target_type: str
    target_filter: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Alert ──

class AlertResponse(BaseModel):
    id: int
    rule_id: int
    host_id: int | None
    service_id: int | None
    severity: str
    status: str
    title: str
    message: str | None
    metric_value: float | None
    threshold: float | None
    fired_at: datetime
    resolved_at: datetime | None
    acknowledged_at: datetime | None
    acknowledged_by: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
