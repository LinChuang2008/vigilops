"""
AI 反馈相关请求/响应模型
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AIFeedbackCreate(BaseModel):
    """创建 AI 反馈请求体"""
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    ai_response: str = Field(..., description="AI 回答内容")
    user_question: Optional[str] = None
    
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    feedback_type: str = Field(default="general", description="反馈类型")
    feedback_text: Optional[str] = None
    is_helpful: Optional[bool] = None
    
    context: Optional[Dict[str, Any]] = None
    ai_confidence: Optional[float] = Field(None, ge=0, le=1)
    response_time_ms: Optional[int] = None


class AIFeedbackUpdate(BaseModel):
    """更新 AI 反馈请求体"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_type: Optional[str] = None
    feedback_text: Optional[str] = None
    is_helpful: Optional[bool] = None
    is_reviewed: Optional[bool] = None
    reviewer_notes: Optional[str] = None


class AIFeedbackResponse(BaseModel):
    """AI 反馈响应体"""
    id: int
    user_id: int
    session_id: Optional[str]
    message_id: Optional[str]
    ai_response: str
    user_question: Optional[str]
    
    rating: int
    feedback_type: str
    feedback_text: Optional[str]
    is_helpful: Optional[bool]
    
    context: Optional[Dict[str, Any]]
    ai_confidence: Optional[float]
    response_time_ms: Optional[int]
    
    is_reviewed: bool
    reviewer_notes: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class AIFeedbackList(BaseModel):
    """AI 反馈列表响应"""
    total: int
    items: List[AIFeedbackResponse]


class AIFeedbackStats(BaseModel):
    """AI 反馈统计"""
    total_feedback: int
    avg_rating: Optional[float]
    helpful_percentage: Optional[float]
    rating_distribution: Dict[str, int]
    feedback_by_type: Dict[str, int]
    avg_response_time_ms: Optional[float]
    avg_confidence: Optional[float]
    trends: Dict[str, Any]  # 趋势数据


class QuickFeedback(BaseModel):
    """快速反馈请求体（只需评分）"""
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    ai_response: str
    rating: int = Field(..., ge=1, le=5)
    is_helpful: Optional[bool] = None


class FeedbackTrend(BaseModel):
    """反馈趋势数据"""
    date: str
    avg_rating: Optional[float]
    feedback_count: int
    helpful_count: int


class AIPerformanceReport(BaseModel):
    """AI 性能报告"""
    period: str
    total_interactions: int
    feedback_rate: float  # 反馈率
    satisfaction_score: float  # 满意度评分
    improvement_suggestions: List[str]
    common_issues: List[Dict[str, Any]]
    top_rated_responses: List[Dict[str, Any]]