"""
修复操作相关请求/响应模型。
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class RemediationLogResponse(BaseModel):
    """修复日志响应体。"""
    id: int
    alert_id: int
    host_id: Optional[int]
    status: str
    risk_level: Optional[str]
    runbook_name: Optional[str]
    diagnosis_json: Optional[Dict[str, Any]]
    command_results_json: Optional[List[Any]]
    verification_passed: Optional[bool]
    blocked_reason: Optional[str]
    triggered_by: str
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class RemediationStatsResponse(BaseModel):
    """修复统计响应体。"""
    total: int
    success: int
    failed: int
    pending: int
    success_rate: float
    avg_duration_seconds: Optional[float]
    today_count: int
    week_count: int


class RemediationApproveRequest(BaseModel):
    """审批修复请求体。"""
    comment: Optional[str] = None
