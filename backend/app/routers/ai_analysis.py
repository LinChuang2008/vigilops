"""AI 智能分析路由模块。

提供日志分析、AI 对话、根因分析和系统概览等 AI 驱动的运维分析接口。
所有分析结果会持久化到 ai_insights 表中供后续查阅。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.log_entry import LogEntry
from app.models.ai_insight import AIInsight
from app.models.host import Host
from app.models.host_metric import HostMetric
from app.models.alert import Alert
from app.models.service import Service
from app.models.user import User
from app.services.ai_engine import ai_engine
from app.schemas.ai_insight import (
    AIInsightResponse,
    AnalyzeLogsRequest,
    AnalyzeLogsResponse,
    ChatRequest,
    ChatResponse,
)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/analyze-logs", response_model=AnalyzeLogsResponse)
async def analyze_logs(
    req: AnalyzeLogsRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """手动触发 AI 日志分析。

    根据时间范围、主机和日志级别筛选日志，调用 AI 引擎进行分析，
    并将分析结果保存为 AI 洞察记录。
    """
    since = datetime.now(timezone.utc) - timedelta(hours=req.hours)

    # 构建查询过滤条件
    filters = [LogEntry.timestamp >= since]
    if req.host_id is not None:
        filters.append(LogEntry.host_id == req.host_id)
    if req.level is not None:
        filters.append(LogEntry.level == req.level.upper())

    q = (
        select(LogEntry)
        .where(and_(*filters))
        .order_by(LogEntry.timestamp.desc())
        .limit(500)
    )
    result = await db.execute(q)
    entries = result.scalars().all()

    # 将日志条目转换为字典列表供 AI 引擎使用
    logs_data: List[dict] = [
        {
            "timestamp": str(e.timestamp),
            "level": e.level,
            "host_id": e.host_id,
            "service": e.service,
            "message": e.message,
        }
        for e in entries
    ]

    analysis = await ai_engine.analyze_logs(logs_data)

    # 分析成功时保存洞察记录到数据库
    if not analysis.get("error"):
        insight = AIInsight(
            insight_type="anomaly",
            severity=analysis.get("severity", "info"),
            title=analysis.get("title", "AI 分析结果"),
            summary=analysis.get("summary", ""),
            details=analysis,
            related_host_id=req.host_id,
            status="new",
        )
        db.add(insight)
        await db.commit()

    return AnalyzeLogsResponse(
        success=not analysis.get("error", False),
        analysis=analysis,
        log_count=len(logs_data),
    )


@router.get("/insights", response_model=dict)
async def list_insights(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取 AI 分析洞察列表，支持按严重级别和状态筛选，分页返回。"""
    q = select(AIInsight)
    count_q = select(func.count(AIInsight.id))

    filters = []
    if severity:
        filters.append(AIInsight.severity == severity)
    if status:
        filters.append(AIInsight.status == status)

    if filters:
        q = q.where(and_(*filters))
        count_q = count_q.where(and_(*filters))

    total = (await db.execute(count_q)).scalar()
    q = q.order_by(AIInsight.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    insights = result.scalars().all()

    return {
        "items": [AIInsightResponse.model_validate(i).model_dump(mode="json") for i in insights],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def _build_chat_context(db: AsyncSession) -> Dict[str, Any]:
    """从数据库构建 AI 对话的系统上下文。

    收集最近 1 小时内的错误日志、主机指标、活跃告警和服务状态，
    作为 AI 对话的背景信息。
    """
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    context: Dict[str, Any] = {}

    # 获取最近的 ERROR/WARN 级别日志（最多 50 条）
    log_q = (
        select(LogEntry)
        .where(and_(
            LogEntry.timestamp >= since,
            LogEntry.level.in_(["ERROR", "WARN", "WARNING", "CRITICAL", "FATAL"]),
        ))
        .order_by(LogEntry.timestamp.desc())
        .limit(50)
    )
    log_result = await db.execute(log_q)
    log_entries = log_result.scalars().all()
    context["logs"] = [
        {
            "timestamp": str(e.timestamp),
            "level": e.level,
            "host_id": e.host_id,
            "service": e.service,
            "message": e.message[:200],  # 截断过长消息
        }
        for e in log_entries
    ]

    # 获取每台主机的最新指标（通过子查询找到每主机最新记录时间）
    latest_metric_subq = (
        select(
            HostMetric.host_id,
            func.max(HostMetric.recorded_at).label("max_recorded_at"),
        )
        .where(HostMetric.recorded_at >= since)
        .group_by(HostMetric.host_id)
        .subquery()
    )
    metric_q = (
        select(HostMetric, Host.hostname)
        .join(latest_metric_subq, and_(
            HostMetric.host_id == latest_metric_subq.c.host_id,
            HostMetric.recorded_at == latest_metric_subq.c.max_recorded_at,
        ))
        .outerjoin(Host, HostMetric.host_id == Host.id)
    )
    metric_result = await db.execute(metric_q)
    rows = metric_result.all()
    context["metrics"] = [
        {
            "host_id": m.host_id,
            "hostname": hostname or "unknown",
            "cpu_percent": m.cpu_percent,
            "memory_percent": m.memory_percent,
            "disk_percent": m.disk_percent,
        }
        for m, hostname in rows
    ]

    # 获取触发中的告警（最多 20 条）
    alert_q = (
        select(Alert)
        .where(Alert.status == "firing")
        .order_by(Alert.fired_at.desc())
        .limit(20)
    )
    alert_result = await db.execute(alert_q)
    alerts = alert_result.scalars().all()
    context["alerts"] = [
        {
            "id": a.id,
            "severity": a.severity,
            "title": a.title,
            "message": (a.message or "")[:200],
            "status": a.status,
            "fired_at": str(a.fired_at),
        }
        for a in alerts
    ]

    # 获取活跃服务的健康状态
    svc_q = select(Service).where(Service.is_active == True)
    svc_result = await db.execute(svc_q)
    services = svc_result.scalars().all()
    context["services"] = [
        {
            "name": s.name,
            "type": s.type,
            "target": s.target,
            "status": s.status,
        }
        for s in services
    ]

    return context


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """AI 自然语言对话接口。

    基于当前系统上下文（日志、指标、告警、服务状态）回答用户问题，
    并将对话记录保存为洞察。
    """
    # 从数据库构建系统上下文
    context = await _build_chat_context(db)

    # 调用 AI 引擎
    result = await ai_engine.chat(req.question, context)

    answer = result.get("answer", "")
    sources = result.get("sources", [])

    # 保存对话记录到 ai_insights
    if not result.get("error"):
        insight = AIInsight(
            insight_type="chat",
            severity="info",
            title=req.question[:200],
            summary=answer[:500],
            details={"question": req.question, "answer": answer, "sources": sources},
            status="new",
        )
        db.add(insight)
        await db.commit()

    return ChatResponse(answer=answer, sources=sources)


@router.post("/root-cause", response_model=dict)
async def root_cause_analysis(
    alert_id: int = Query(..., description="Alert ID to analyze"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """针对指定告警进行根因分析。

    收集告警前后 30 分钟的指标和日志数据，调用 AI 引擎进行根因推断。
    """
    # 查询目标告警
    alert_result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = alert_result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    alert_data = {
        "id": alert.id,
        "title": alert.title,
        "severity": alert.severity,
        "status": alert.status,
        "message": alert.message,
        "metric_value": alert.metric_value,
        "threshold": alert.threshold,
        "fired_at": str(alert.fired_at),
        "host_id": alert.host_id,
    }

    # 时间窗口：告警前后各 30 分钟
    window_start = alert.fired_at - timedelta(minutes=30)
    window_end = alert.fired_at + timedelta(minutes=30)

    # 获取关联主机的指标数据
    metrics_data: List[dict] = []
    if alert.host_id:
        metric_q = (
            select(HostMetric)
            .where(and_(
                HostMetric.host_id == alert.host_id,
                HostMetric.recorded_at >= window_start,
                HostMetric.recorded_at <= window_end,
            ))
            .order_by(HostMetric.recorded_at.asc())
            .limit(60)
        )
        metric_result = await db.execute(metric_q)
        metrics = metric_result.scalars().all()
        metrics_data = [
            {
                "host_id": m.host_id,
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "disk_percent": m.disk_percent,
                "cpu_load_1": m.cpu_load_1,
                "net_send_rate_kb": m.net_send_rate_kb,
                "net_recv_rate_kb": m.net_recv_rate_kb,
                "recorded_at": str(m.recorded_at),
            }
            for m in metrics
        ]

    # 获取时间窗口内的关联日志
    log_filters = [
        LogEntry.timestamp >= window_start,
        LogEntry.timestamp <= window_end,
    ]
    if alert.host_id:
        log_filters.append(LogEntry.host_id == alert.host_id)

    log_q = (
        select(LogEntry)
        .where(and_(*log_filters))
        .order_by(LogEntry.timestamp.desc())
        .limit(50)
    )
    log_result = await db.execute(log_q)
    log_entries = log_result.scalars().all()
    logs_data = [
        {
            "timestamp": str(e.timestamp),
            "level": e.level,
            "host_id": e.host_id,
            "service": e.service,
            "message": e.message[:200],
        }
        for e in log_entries
    ]

    # 调用 AI 引擎进行根因分析
    analysis = await ai_engine.analyze_root_cause(alert_data, metrics_data, logs_data)

    # 保存根因分析结果
    if not analysis.get("error"):
        insight = AIInsight(
            insight_type="root_cause",
            severity=alert.severity,
            title=f"根因分析: {alert.title[:200]}",
            summary=analysis.get("root_cause", "")[:500],
            details=analysis,
            related_host_id=alert.host_id,
            related_alert_id=alert.id,
            status="new",
        )
        db.add(insight)
        await db.commit()

    return {
        "alert_id": alert_id,
        "analysis": analysis,
    }


@router.get("/system-summary", response_model=dict)
async def system_summary(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取系统概览快照，用于 AI 前端展示。

    汇总主机、服务、告警、错误日志数量以及平均资源使用率。
    """
    since = datetime.now(timezone.utc) - timedelta(hours=1)

    # 主机统计
    host_total = (await db.execute(select(func.count(Host.id)))).scalar() or 0
    host_online = (await db.execute(
        select(func.count(Host.id)).where(Host.status == "online")
    )).scalar() or 0
    host_offline = host_total - host_online

    # 服务统计
    svc_total = (await db.execute(
        select(func.count(Service.id)).where(Service.is_active == True)
    )).scalar() or 0
    svc_up = (await db.execute(
        select(func.count(Service.id)).where(and_(Service.is_active == True, Service.status == "up"))
    )).scalar() or 0
    svc_down = (await db.execute(
        select(func.count(Service.id)).where(and_(Service.is_active == True, Service.status == "down"))
    )).scalar() or 0

    # 最近 1 小时告警数
    alert_count = (await db.execute(
        select(func.count(Alert.id)).where(Alert.fired_at >= since)
    )).scalar() or 0

    # 最近 1 小时错误日志数
    error_log_count = (await db.execute(
        select(func.count(LogEntry.id)).where(and_(
            LogEntry.timestamp >= since,
            LogEntry.level.in_(["ERROR", "CRITICAL", "FATAL"]),
        ))
    )).scalar() or 0

    # 计算各主机最新指标的平均 CPU 和内存使用率
    latest_metric_subq = (
        select(
            HostMetric.host_id,
            func.max(HostMetric.recorded_at).label("max_recorded_at"),
        )
        .where(HostMetric.recorded_at >= since)
        .group_by(HostMetric.host_id)
        .subquery()
    )
    avg_q = (
        select(
            func.avg(HostMetric.cpu_percent).label("avg_cpu"),
            func.avg(HostMetric.memory_percent).label("avg_mem"),
        )
        .join(latest_metric_subq, and_(
            HostMetric.host_id == latest_metric_subq.c.host_id,
            HostMetric.recorded_at == latest_metric_subq.c.max_recorded_at,
        ))
    )
    avg_result = await db.execute(avg_q)
    avg_row = avg_result.one()
    avg_cpu = round(avg_row.avg_cpu, 1) if avg_row.avg_cpu is not None else None
    avg_mem = round(avg_row.avg_mem, 1) if avg_row.avg_mem is not None else None

    return {
        "hosts": {
            "total": host_total,
            "online": host_online,
            "offline": host_offline,
        },
        "services": {
            "total": svc_total,
            "up": svc_up,
            "down": svc_down,
        },
        "recent_1h": {
            "alert_count": alert_count,
            "error_log_count": error_log_count,
        },
        "avg_usage": {
            "cpu_percent": avg_cpu,
            "memory_percent": avg_mem,
        },
    }
