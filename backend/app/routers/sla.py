"""
SLA 管理路由

提供 SLA 规则管理、状态看板、违规事件和可用性报告接口。
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sla import SLARule, SLAViolation
from app.models.service import Service, ServiceCheck
from app.models.user import User
from app.schemas.sla import (
    SLARuleCreate, SLARuleResponse, SLAStatusResponse,
    SLAViolationResponse, SLAReportResponse, DailyAvailability,
)

router = APIRouter(prefix="/api/v1/sla", tags=["sla"])


def _get_window_start(window: str) -> datetime:
    """根据计算窗口类型返回时间窗口起始时间。"""
    now = datetime.now(timezone.utc)
    if window == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif window == "weekly":
        return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # monthly
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _get_window_days(window: str) -> int:
    """返回计算窗口的天数（用于错误预算计算）。"""
    now = datetime.now(timezone.utc)
    if window == "daily":
        return 1
    elif window == "weekly":
        return 7
    else:  # monthly
        import calendar
        return calendar.monthrange(now.year, now.month)[1]


# ========== SLA 规则管理 ==========

@router.get("/rules", response_model=list)
async def list_sla_rules(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有 SLA 规则列表。"""
    result = await db.execute(select(SLARule).order_by(SLARule.id))
    rules = result.scalars().all()
    items = []
    for r in rules:
        # 查询关联的服务名
        svc = (await db.execute(select(Service.name).where(Service.id == r.service_id))).scalar()
        items.append(SLARuleResponse(
            id=r.id, service_id=r.service_id, name=r.name,
            target_percent=float(r.target_percent),
            calculation_window=r.calculation_window,
            created_at=r.created_at, updated_at=r.updated_at,
            service_name=svc,
        ))
    return items


@router.post("/rules", response_model=SLARuleResponse)
async def create_sla_rule(
    body: SLARuleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建 SLA 规则（关联服务，设定目标可用率）。"""
    # 检查服务是否存在
    svc = (await db.execute(select(Service).where(Service.id == body.service_id))).scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")
    # 检查是否已有规则
    existing = (await db.execute(
        select(SLARule).where(SLARule.service_id == body.service_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="该服务已有 SLA 规则")

    rule = SLARule(
        service_id=body.service_id, name=body.name,
        target_percent=body.target_percent,
        calculation_window=body.calculation_window,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return SLARuleResponse(
        id=rule.id, service_id=rule.service_id, name=rule.name,
        target_percent=float(rule.target_percent),
        calculation_window=rule.calculation_window,
        created_at=rule.created_at, updated_at=rule.updated_at,
        service_name=svc.name,
    )


@router.delete("/rules/{rule_id}")
async def delete_sla_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除 SLA 规则。"""
    rule = (await db.execute(select(SLARule).where(SLARule.id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    await db.delete(rule)
    await db.commit()
    return {"detail": "已删除"}


# ========== SLA 状态看板 ==========

@router.get("/status", response_model=list)
async def sla_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SLA 状态看板：计算每个 SLA 规则的实时可用率和错误预算。"""
    result = await db.execute(select(SLARule).order_by(SLARule.id))
    rules = result.scalars().all()
    items = []
    for r in rules:
        svc = (await db.execute(select(Service).where(Service.id == r.service_id))).scalar_one_or_none()
        if not svc:
            continue
        window_start = _get_window_start(r.calculation_window)

        # 查询总检查数和 down 检查数
        total = (await db.execute(
            select(func.count()).select_from(ServiceCheck).where(
                ServiceCheck.service_id == r.service_id,
                ServiceCheck.checked_at >= window_start,
            )
        )).scalar() or 0

        down = (await db.execute(
            select(func.count()).select_from(ServiceCheck).where(
                ServiceCheck.service_id == r.service_id,
                ServiceCheck.checked_at >= window_start,
                ServiceCheck.status == "down",
            )
        )).scalar() or 0

        if total == 0:
            items.append(SLAStatusResponse(
                rule_id=r.id, service_id=r.service_id,
                service_name=svc.name,
                target_percent=float(r.target_percent),
                actual_percent=None, is_met=None,
                error_budget_remaining_minutes=None,
                calculation_window=r.calculation_window,
                total_checks=0, down_checks=0,
            ))
            continue

        actual = round((total - down) / total * 100, 4)
        target = float(r.target_percent)
        is_met = actual >= target

        # 错误预算计算
        window_days = _get_window_days(r.calculation_window)
        total_minutes = window_days * 24 * 60
        allowed_downtime = total_minutes * (1 - target / 100)
        used_downtime = down * svc.check_interval / 60
        remaining = round(allowed_downtime - used_downtime, 2)

        items.append(SLAStatusResponse(
            rule_id=r.id, service_id=r.service_id,
            service_name=svc.name,
            target_percent=target, actual_percent=actual,
            is_met=is_met,
            error_budget_remaining_minutes=remaining,
            calculation_window=r.calculation_window,
            total_checks=total, down_checks=down,
        ))
    return items


# ========== 违规事件 ==========

@router.get("/violations", response_model=list)
async def list_violations(
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询 SLA 违规事件列表。"""
    query = select(SLAViolation).order_by(SLAViolation.started_at.desc())
    if start_date:
        query = query.where(SLAViolation.started_at >= datetime.fromisoformat(start_date))
    if end_date:
        end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)
        query = query.where(SLAViolation.started_at < end_dt)

    result = await db.execute(query)
    violations = result.scalars().all()
    items = []
    for v in violations:
        svc_name = (await db.execute(select(Service.name).where(Service.id == v.service_id))).scalar()
        items.append(SLAViolationResponse(
            id=v.id, sla_rule_id=v.sla_rule_id, service_id=v.service_id,
            service_name=svc_name,
            started_at=v.started_at, ended_at=v.ended_at,
            duration_seconds=v.duration_seconds,
            description=v.description, created_at=v.created_at,
        ))
    return items


# ========== 可用性报告 ==========

@router.get("/report", response_model=SLAReportResponse)
async def sla_report(
    service_id: int = Query(..., description="服务 ID"),
    period: str = Query("monthly", description="报告周期"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成可用性报告：30 天每日可用率趋势 + 违规事件 + 总结。"""
    # 确定时间范围
    if start_date and end_date:
        dt_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        dt_end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) + timedelta(days=1)
    else:
        dt_end = datetime.now(timezone.utc)
        dt_start = dt_end - timedelta(days=30)

    # 查询服务和 SLA 规则
    svc = (await db.execute(select(Service).where(Service.id == service_id))).scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=404, detail="服务不存在")
    rule = (await db.execute(
        select(SLARule).where(SLARule.service_id == service_id)
    )).scalar_one_or_none()
    target = float(rule.target_percent) if rule else 99.9

    # 计算每日可用率趋势
    daily_trend = []
    current = dt_start.replace(hour=0, minute=0, second=0, microsecond=0)
    total_all = 0
    down_all = 0
    while current < dt_end:
        next_day = current + timedelta(days=1)
        total = (await db.execute(
            select(func.count()).select_from(ServiceCheck).where(
                ServiceCheck.service_id == service_id,
                ServiceCheck.checked_at >= current,
                ServiceCheck.checked_at < next_day,
            )
        )).scalar() or 0
        down = (await db.execute(
            select(func.count()).select_from(ServiceCheck).where(
                ServiceCheck.service_id == service_id,
                ServiceCheck.checked_at >= current,
                ServiceCheck.checked_at < next_day,
                ServiceCheck.status == "down",
            )
        )).scalar() or 0
        total_all += total
        down_all += down
        avail = round((total - down) / total * 100, 4) if total > 0 else None
        daily_trend.append(DailyAvailability(
            date=current.strftime("%Y-%m-%d"), availability=avail,
        ))
        current = next_day

    # 查询违规事件
    viol_result = await db.execute(
        select(SLAViolation).where(
            SLAViolation.service_id == service_id,
            SLAViolation.started_at >= dt_start,
            SLAViolation.started_at < dt_end,
        ).order_by(SLAViolation.started_at.desc())
    )
    violations = [
        SLAViolationResponse(
            id=v.id, sla_rule_id=v.sla_rule_id, service_id=v.service_id,
            started_at=v.started_at, ended_at=v.ended_at,
            duration_seconds=v.duration_seconds,
            description=v.description, created_at=v.created_at,
        )
        for v in viol_result.scalars().all()
    ]

    overall = round((total_all - down_all) / total_all * 100, 4) if total_all > 0 else None
    total_downtime = round(down_all * svc.check_interval / 60, 2)

    # 生成总结
    if overall is None:
        summary = "该服务在报告期间内无检查数据。"
    elif overall >= target:
        summary = f"服务 {svc.name} 在报告期间内可用率 {overall}%，达到 SLA 目标 {target}%。"
    else:
        summary = f"服务 {svc.name} 在报告期间内可用率 {overall}%，未达到 SLA 目标 {target}%，累计停机 {total_downtime} 分钟。"

    return SLAReportResponse(
        service_id=service_id, service_name=svc.name,
        target_percent=target,
        period_start=dt_start.strftime("%Y-%m-%d"),
        period_end=(dt_end - timedelta(days=1)).strftime("%Y-%m-%d"),
        overall_availability=overall,
        daily_trend=daily_trend,
        violations=violations,
        total_downtime_minutes=total_downtime,
        summary=summary,
    )
