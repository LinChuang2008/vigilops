"""
AI智能分析路由模块 (AI Intelligent Analysis Router)

功能说明：提供基于DeepSeek AI引擎的智能运维分析服务
核心职责：
  - 日志智能分析（异常检测和模式识别）
  - AI自然语言对话（基于系统上下文问答）
  - 告警根因分析（时间窗口内数据关联分析）
  - 系统概览生成（多维度数据汇总）
  - AI洞察持久化存储（分析结果保存和查询）
依赖关系：依赖AI引擎服务、SQLAlchemy、系统监控数据
API端点：POST /analyze-logs, POST /chat, POST /root-cause, GET /insights, GET /system-summary

Author: VigilOps Team
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
    """
    AI日志智能分析接口 (AI Log Intelligent Analysis)
    
    对指定时间范围内的日志进行AI分析，识别异常模式和潜在问题。
    
    Args:
        req: 日志分析请求（时间范围、主机ID、日志级别筛选）
        db: 数据库会话依赖注入
        _user: 当前登录用户（JWT认证）
    Returns:
        AnalyzeLogsResponse: 分析结果响应（成功状态、分析内容、日志数量）
    流程：
        1. 根据筛选条件查询指定时间范围内的日志（最多500条）
        2. 将日志数据转换为AI引擎可处理的格式
        3. 调用AI引擎进行日志分析和异常检测
        4. 分析成功时创建AIInsight记录持久化结果
        5. 返回分析状态和详细结果
    """
    since = datetime.now(timezone.utc) - timedelta(hours=req.hours)

    # 构建日志查询过滤条件 (Build log query filter conditions)
    filters = [LogEntry.timestamp >= since]  # 时间范围过滤
    if req.host_id is not None:
        filters.append(LogEntry.host_id == req.host_id)  # 按主机过滤
    if req.level is not None:
        filters.append(LogEntry.level == req.level.upper())  # 按日志级别过滤

    # 查询符合条件的日志，限制500条防止AI处理超载 (Query matching logs, limit 500 to prevent AI overload)
    q = (
        select(LogEntry)
        .where(and_(*filters))
        .order_by(LogEntry.timestamp.desc())  # 按时间倒序，优先分析最新日志
        .limit(500)
    )
    result = await db.execute(q)
    entries = result.scalars().all()

    # 将日志条目转换为AI引擎可处理的格式 (Convert log entries to AI engine compatible format)
    logs_data: List[dict] = [
        {
            "timestamp": str(e.timestamp),  # 时间戳转字符串
            "level": e.level,              # 日志级别
            "host_id": e.host_id,          # 主机ID
            "service": e.service,          # 服务名称
            "message": e.message,          # 日志消息内容
        }
        for e in entries
    ]

    # 调用AI引擎进行日志分析，识别异常模式 (Call AI engine for log analysis and anomaly detection)
    analysis = await ai_engine.analyze_logs(logs_data)

    # 分析成功时保存AI洞察到数据库供后续查阅 (Save AI insight to database for future reference when analysis succeeds)
    if not analysis.get("error"):
        insight = AIInsight(
            insight_type="anomaly",  # 异常检测类型
            severity=analysis.get("severity", "info"),
            title=analysis.get("title", "AI 分析结果"),
            summary=analysis.get("summary", ""),  # 分析摘要
            details=analysis,  # 完整分析结果
            related_host_id=req.host_id,  # 关联主机
            status="new",  # 新生成状态
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
    """
    AI洞察列表查询接口 (AI Insights List Query)
    
    分页查询AI分析生成的洞察记录，支持严重级别和状态筛选。
    
    Args:
        page: 页码，从1开始
        page_size: 每页数量，限制1-100之间
        severity: 严重级别筛选（critical/high/medium/low/info）
        status: 洞察状态筛选（new/reviewed/archived）
        db: 数据库会话依赖注入
        _user: 当前登录用户（JWT认证）
    Returns:
        dict: 包含洞察列表、总数、分页信息的响应
    流程：
        1. 根据筛选条件构建查询和计数语句
        2. 执行分页查询获取AI洞察记录
        3. 按创建时间倒序排列（最新洞察在前）
        4. 返回分页结果和元数据
    """
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
    """
    构建AI对话系统上下文 (Build AI Chat System Context)
    
    从数据库收集最近系统状态信息，为AI对话提供实时上下文。
    
    Args:
        db: 数据库会话对象
    Returns:
        Dict[str, Any]: 系统上下文字典，包含日志、指标、告警、服务状态
    收集数据：
        1. 最近1小时的错误/警告级别日志（最多50条）
        2. 各主机的最新性能指标（CPU、内存、磁盘使用率）
        3. 当前触发状态的告警（最多20条）
        4. 活跃服务的健康状态信息
    用途：为AI对话提供系统实时状态，提高回答的准确性和相关性
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
    """
    AI智能对话接口 (AI Intelligent Chat)
    
    基于系统实时状态进行自然语言对话，回答运维相关问题。
    
    Args:
        req: 对话请求（用户问题）
        db: 数据库会话依赖注入
        _user: 当前登录用户（JWT认证）
    Returns:
        ChatResponse: 对话响应（AI回答、参考来源、记忆上下文）
    流程：
        1. 构建系统实时上下文（日志、指标、告警、服务状态）
        2. 调用AI引擎基于上下文回答用户问题
        3. 保存对话记录为AIInsight用于历史查阅
        4. 返回AI回答和相关参考信息
    特点：结合系统状态的智能问答，非简单的聊天机器人
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

    # 附加记忆上下文（可选字段）
    memory_context = result.get("memory_context", [])
    return ChatResponse(answer=answer, sources=sources, memory_context=memory_context)


@router.post("/root-cause", response_model=dict)
async def root_cause_analysis(
    alert_id: int = Query(..., description="Alert ID to analyze"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    告警根因分析接口 (Alert Root Cause Analysis)
    
    对指定告警进行智能根因分析，基于时间窗口内的关联数据推断原因。
    
    Args:
        alert_id: 告警记录ID
        db: 数据库会话依赖注入
        _user: 当前登录用户（JWT认证）
    Returns:
        dict: 根因分析结果和记忆上下文
    Raises:
        HTTPException 404: 告警记录不存在
    流程：
        1. 查询目标告警的详细信息
        2. 收集告警前后30分钟的主机性能指标
        3. 收集同时间窗口内的相关日志数据
        4. 调用AI引擎进行时序关联分析
        5. 保存根因分析结果为AIInsight
        6. 返回分析结论和建议措施
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

    # 定义根因分析时间窗口：告警前后各30分钟 (Define root cause analysis time window: 30 minutes before and after alert)
    window_start = alert.fired_at - timedelta(minutes=30)
    window_end = alert.fired_at + timedelta(minutes=30)

    # 收集告警主机在时间窗口内的性能指标数据 (Collect host performance metrics within time window)
    metrics_data: List[dict] = []
    if alert.host_id:
        metric_q = (
            select(HostMetric)
            .where(and_(
                HostMetric.host_id == alert.host_id,
                HostMetric.recorded_at >= window_start,  # 窗口起始时间
                HostMetric.recorded_at <= window_end,    # 窗口结束时间
            ))
            .order_by(HostMetric.recorded_at.asc())  # 按时间升序，用于时序分析
            .limit(60)  # 最多60个数据点，约1分钟间隔
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

    # 附加记忆上下文
    memory_context = analysis.pop("memory_context", [])
    return {
        "alert_id": alert_id,
        "analysis": analysis,
        "memory_context": memory_context,
    }


@router.get("/system-summary", response_model=dict)
async def system_summary(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    系统概览快照接口 (System Summary Snapshot)
    
    生成系统整体状态快照，为AI分析前端提供数据概览。
    
    Args:
        db: 数据库会话依赖注入
        _user: 当前登录用户（JWT认证）
    Returns:
        dict: 系统概览数据（主机、服务、告警、日志、资源使用率统计）
    统计维度：
        1. 主机统计（总数、在线数、离线数）
        2. 服务统计（总数、正常数、异常数）
        3. 最近1小时告警和错误日志数量
        4. 各主机最新指标的平均CPU和内存使用率
    用途：为AI分析页面提供系统健康度总览和关键指标摘要
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
