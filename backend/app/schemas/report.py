"""
运维报告相关请求/响应模型

定义报告列表、详情和生成请求的数据结构。
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class GenerateReportRequest(BaseModel):
    """手动触发生成报告的请求体。"""
    report_type: str = "daily"  # "daily" / "weekly"
    period_start: Optional[datetime] = None  # 不传则自动计算
    period_end: Optional[datetime] = None


class ReportResponse(BaseModel):
    """单个报告的响应模型。"""
    id: int
    title: str
    report_type: str
    period_start: datetime
    period_end: datetime
    content: str
    summary: str
    status: str
    generated_by: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    """报告列表的分页响应模型。"""
    items: List[ReportResponse]
    total: int
    page: int
    page_size: int
