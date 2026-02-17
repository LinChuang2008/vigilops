"""
AI 分析相关请求/响应模型

定义 AI 洞察、日志分析、对话等 API 的数据结构。
"""
from datetime import datetime
from typing import Optional, Any, Dict, List

from pydantic import BaseModel


class AIInsightResponse(BaseModel):
    """AI 洞察响应体。"""
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
    """手动触发日志分析请求体。"""
    hours: int = 1
    host_id: Optional[int] = None
    level: Optional[str] = None


class AnalyzeLogsResponse(BaseModel):
    """日志分析响应体。"""
    success: bool
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    log_count: int = 0


class ChatRequest(BaseModel):
    """AI 对话请求体。"""
    question: str


class ChatResponse(BaseModel):
    """AI 对话响应体。"""
    answer: str
    sources: list = []
    memory_context: List[Dict[str, Any]] = []
