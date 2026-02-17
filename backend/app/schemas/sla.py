"""
SLA 相关请求/响应模型

定义 SLA 规则、状态看板、违规事件和可用性报告的数据结构。
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class SLARuleCreate(BaseModel):
    """创建 SLA 规则的请求体。"""
    service_id: int
    name: str
    target_percent: float = 99.90
    calculation_window: str = "monthly"


class SLARuleResponse(BaseModel):
    """SLA 规则响应体。"""
    id: int
    service_id: int
    name: str
    target_percent: float
    calculation_window: str
    created_at: datetime
    updated_at: datetime
    service_name: Optional[str] = None

    model_config = {"from_attributes": True}


class SLAStatusResponse(BaseModel):
    """SLA 状态看板响应体，含实时可用率计算结果。"""
    rule_id: int
    service_id: int
    service_name: str
    target_percent: float
    actual_percent: Optional[float] = None  # None 表示无数据
    is_met: Optional[bool] = None
    error_budget_remaining_minutes: Optional[float] = None
    calculation_window: str
    total_checks: int = 0
    down_checks: int = 0


class SLAViolationResponse(BaseModel):
    """SLA 违规事件响应体。"""
    id: int
    sla_rule_id: int
    service_id: int
    service_name: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DailyAvailability(BaseModel):
    """每日可用率数据点。"""
    date: str
    availability: Optional[float] = None


class SLAReportResponse(BaseModel):
    """可用性报告响应体。"""
    service_id: int
    service_name: str
    target_percent: float
    period_start: str
    period_end: str
    overall_availability: Optional[float] = None
    daily_trend: List[DailyAvailability] = []
    violations: List[SLAViolationResponse] = []
    total_downtime_minutes: float = 0
    summary: str = ""
