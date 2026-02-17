"""
系统设置模型

定义键值对形式的系统配置项表结构。
"""
from sqlalchemy import Column, String, Text, DateTime, func
from app.core.database import Base


class Setting(Base):
    """系统设置表，以键值对形式存储可动态调整的配置。"""
    __tablename__ = "settings"

    key = Column(String(255), primary_key=True, index=True)
    value = Column(Text, nullable=False, default="")
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
