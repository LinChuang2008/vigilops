"""
AI 反馈模型

用于存储用户对 AI 分析结果的反馈，用于改进 AI 服务质量。
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class AIFeedback(Base):
    """AI 反馈表"""
    __tablename__ = "ai_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # AI 交互信息
    session_id = Column(String(100), nullable=True, index=True)  # 对话会话 ID
    message_id = Column(String(100), nullable=True, index=True)   # 消息 ID
    ai_response = Column(Text, nullable=False)  # AI 回答内容
    user_question = Column(Text, nullable=True)  # 用户问题
    
    # 反馈内容
    rating = Column(Integer, nullable=False)  # 评分：1(很差) 2(差) 3(一般) 4(好) 5(很好)
    feedback_type = Column(String(50), nullable=False, default="general")  # 反馈类型：general/accuracy/relevance/clarity
    feedback_text = Column(Text, nullable=True)  # 文字反馈
    is_helpful = Column(Boolean, nullable=True)  # 是否有帮助
    
    # 上下文信息
    context = Column(JSONB, nullable=True)  # 问题上下文（如相关告警、系统状态等）
    ai_confidence = Column(Float, nullable=True)  # AI 回答的置信度
    response_time_ms = Column(Integer, nullable=True)  # AI 响应时间（毫秒）
    
    # 处理状态
    is_reviewed = Column(Boolean, default=False)  # 是否已审核
    reviewer_notes = Column(Text, nullable=True)  # 审核备注
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    user = relationship("User", back_populates="ai_feedback")


class AIFeedbackSummary(Base):
    """AI 反馈统计表（定期汇总）"""
    __tablename__ = "ai_feedback_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 统计周期
    period_type = Column(String(20), nullable=False)  # daily/weekly/monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # 统计数据
    total_feedback = Column(Integer, default=0)
    avg_rating = Column(Float, nullable=True)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    
    # 按类型统计
    feedback_by_type = Column(JSONB, nullable=True)  # {"general": 10, "accuracy": 5, ...}
    rating_distribution = Column(JSONB, nullable=True)  # {"1": 2, "2": 5, "3": 10, ...}
    
    # 性能指标
    avg_response_time_ms = Column(Float, nullable=True)
    avg_confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)