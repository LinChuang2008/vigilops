from datetime import datetime
from typing import Optional, Any, Dict

from pydantic import BaseModel


class AIInsightResponse(BaseModel):
    id: int
    insight_type: str
    severity: str
    title: str
    summary: str
    details: Optional[Dict[str, Any]] = None
    related_host_id: Optional[int] = None
    related_alert_id: Optional[int] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyzeLogsRequest(BaseModel):
    hours: int = 1
    host_id: Optional[int] = None
    level: Optional[str] = None


class AnalyzeLogsResponse(BaseModel):
    success: bool
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    log_count: int = 0


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list = []
