"""
运维报告路由模块

提供报告的列表查询、详情查看、手动生成和删除接口。
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportResponse, GenerateReportRequest
from app.services.report_generator import generate_report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# 东八区时区
CST = timezone(timedelta(hours=8))


@router.get("", response_model=dict)
async def list_reports(
    report_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取报告列表，支持按类型筛选，分页返回，按创建时间倒序。"""
    q = select(Report)
    count_q = select(func.count(Report.id))

    if report_type:
        q = q.where(Report.report_type == report_type)
        count_q = count_q.where(Report.report_type == report_type)

    total = (await db.execute(count_q)).scalar()
    q = q.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    reports = result.scalars().all()

    return {
        "items": [ReportResponse.model_validate(r).model_dump(mode="json") for r in reports],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取报告详情。"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return ReportResponse.model_validate(report)


@router.post("/generate", response_model=ReportResponse)
async def trigger_generate(
    req: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动触发生成报告。报告在后台生成，立即返回 generating 状态的记录。"""
    now = datetime.now(CST)

    # 计算默认时间段
    if req.period_start and req.period_end:
        period_start = req.period_start
        period_end = req.period_end
    elif req.report_type == "weekly":
        # 默认取过去 7 天
        period_end = datetime(now.year, now.month, now.day, tzinfo=CST)
        period_start = period_end - timedelta(days=7)
    else:
        # 默认取昨天
        yesterday = now.date() - timedelta(days=1)
        period_start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=CST)
        period_end = datetime(now.year, now.month, now.day, tzinfo=CST)

    report = await generate_report(db, req.report_type, period_start, period_end, generated_by=user.id)
    return ReportResponse.model_validate(report)


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除报告（仅管理员可操作）。"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除报告")

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    await db.delete(report)
    await db.commit()
    return {"detail": "报告已删除"}
