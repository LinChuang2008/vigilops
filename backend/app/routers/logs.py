"""
日志管理路由 (Log Management Router)

功能说明：提供完整的日志管理功能，包括搜索查询、统计分析和实时推送
核心职责：
  - 多维度日志搜索和过滤（关键字、主机、服务、级别、时间范围）
  - 日志统计分析（按级别和时间分桶聚合）
  - WebSocket 实时日志流推送和客户端订阅管理
  - 基于内存的发布-订阅模式实现高性能日志广播
依赖关系：依赖 LogEntry 和 Host 数据模型，集成 WebSocket 通信
API端点：GET /api/v1/logs, GET /api/v1/logs/stats, WebSocket /ws/logs

Author: VigilOps Team
"""

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.host import Host
from app.models.log_entry import LogEntry
from app.models.user import User
from app.schemas.log_entry import (
    LogEntryResponse,
    LogSearchResponse,
    LogStatsResponse,
    LevelCount,
    TimeCount,
)

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


# ── 内存级广播器，用于 WebSocket 实时日志推送 (F052) ──────────────────
class LogBroadcaster:
    """
    日志广播器 (Log Broadcaster)
    
    基于内存队列实现的发布-订阅模式，用于向多个 WebSocket 客户端实时推送日志数据。
    采用异步非阻塞设计，当客户端消费速度过慢时会自动丢弃消息，避免内存溢出。
    
    特性：
    - 支持多订阅者同时接收日志流
    - 队列满时自动丢弃消息，保护服务器资源
    - 线程安全的订阅者管理
    """

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []  # 维护所有活跃的订阅队列

    def subscribe(self) -> asyncio.Queue:
        """
        创建新的订阅队列 (Create New Subscription)
        
        为每个 WebSocket 连接创建独立的异步队列，用于接收广播消息。
        队列设置最大容量以防止内存无限增长。
        
        Returns:
            asyncio.Queue: 新创建的订阅队列，最大容量 256 条消息
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=256)  # 限制队列大小防止内存泄漏
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """
        移除订阅队列 (Remove Subscription)
        
        当 WebSocket 连接断开时，清理对应的订阅队列，释放资源。
        
        Args:
            q: 要移除的订阅队列
        """
        if q in self._subscribers:  # 防止重复移除导致异常
            self._subscribers.remove(q)

    async def publish(self, entries: list[dict]):
        """
        向所有订阅者广播日志条目 (Broadcast Log Entries)
        
        将新的日志条目推送给所有活跃的订阅者。采用非阻塞策略，
        如果某个订阅者的队列已满（通常是客户端处理过慢），则丢弃该条目。
        
        Args:
            entries: 要广播的日志条目列表，每个条目为字典格式
        """
        # 使用 list() 创建快照，避免迭代过程中列表被修改
        for q in list(self._subscribers):
            for entry in entries:
                try:
                    q.put_nowait(entry)  # 非阻塞放入队列
                except asyncio.QueueFull:
                    pass  # 消费者处理过慢，丢弃该条目避免阻塞整个广播流程


log_broadcaster = LogBroadcaster()


# ── 日志搜索与筛选 (F049 + F050) ─────────────────────────────────────
@router.get("", response_model=LogSearchResponse)
async def search_logs(
    q: str | None = Query(None, description="Full-text search keyword"),
    host_id: int | None = Query(None),
    service: str | None = Query(None),
    level: str | None = Query(None, description="Comma-separated levels, e.g. ERROR,WARN"),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    搜索日志条目 (Search Log Entries)
    
    支持多维度日志检索和过滤，用于日志分析和故障排查。
    提供全文搜索、精确匹配和时间范围筛选，支持分页查询大量日志数据。
    
    Args:
        q: 全文搜索关键字，在日志消息中模糊匹配
        host_id: 按主机ID精确筛选
        service: 按服务名筛选（如 nginx, mysql 等）
        level: 日志级别筛选，支持多值逗号分隔（如 "ERROR,WARN"）
        start_time: 查询起始时间
        end_time: 查询结束时间
        page: 页码，从1开始
        page_size: 每页条数，限制1-200条
        _user: 当前认证用户
        db: 数据库会话
        
    Returns:
        LogSearchResponse: 包含日志条目列表、总数和分页信息
    """
    # 构建基础查询和计数查询
    base = select(LogEntry)
    count_base = select(func.count(LogEntry.id))

    # 构建动态过滤条件列表
    conditions = []
    if q:  # 全文搜索：在消息内容中模糊匹配关键字
        conditions.append(LogEntry.message.ilike(f"%{q}%"))
    if host_id is not None:  # 主机筛选：精确匹配主机ID
        conditions.append(LogEntry.host_id == host_id)
    if service:  # 服务筛选：精确匹配服务名
        conditions.append(LogEntry.service == service)
    if level:  # 日志级别筛选：支持多个级别同时查询
        levels = [l.strip().upper() for l in level.split(",") if l.strip()]
        conditions.append(LogEntry.level.in_(levels))
    if start_time:  # 时间范围筛选：大于等于起始时间
        conditions.append(LogEntry.timestamp >= start_time)
    if end_time:  # 时间范围筛选：小于等于结束时间
        conditions.append(LogEntry.timestamp <= end_time)

    # 将过滤条件应用到主查询和计数查询
    for cond in conditions:
        base = base.where(cond)
        count_base = count_base.where(cond)

    # 执行计数查询获取符合条件的总记录数
    total_result = await db.execute(count_base)
    total = total_result.scalar() or 0

    # 构建分页查询，关联 Host 表获取主机名
    offset = (page - 1) * page_size  # 计算跳过的记录数
    stmt = (
        select(LogEntry, Host.hostname)
        .outerjoin(Host, LogEntry.host_id == Host.id)  # 左连接获取主机名，允许主机不存在
    )
    
    # 应用所有过滤条件
    for cond in conditions:
        stmt = stmt.where(cond)
        
    # 按时间倒序排列（最新的日志在前）+ 分页
    stmt = stmt.order_by(LogEntry.timestamp.desc()).offset(offset).limit(page_size)
    rows = await db.execute(stmt)
    
    # 构建响应数据，将数据库记录转换为 API 响应格式
    items = []
    for log_entry, hostname in rows.all():
        item = LogEntryResponse.model_validate(log_entry)  # 使用 Pydantic 模型验证
        item.hostname = hostname  # 添加主机名信息
        items.append(item)

    return LogSearchResponse(items=items, total=total, page=page, page_size=page_size)


# ── 日志统计 (F053) ──────────────────────────────────────────────────
@router.get("/stats", response_model=LogStatsResponse)
async def log_stats(
    host_id: int | None = Query(None),
    service: str | None = Query(None),
    period: str = Query("1h", description="Time bucket: 1h or 1d"),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取日志统计数据 (Get Log Statistics)
    
    提供日志数据的聚合统计分析，支持按日志级别分组和时间分桶统计。
    用于日志监控仪表盘的图表展示和趋势分析。
    
    Args:
        host_id: 可选的主机ID筛选
        service: 可选的服务名筛选
        period: 时间分桶粒度，支持 "1h"（按小时）或 "1d"（按天）
        start_time: 统计起始时间
        end_time: 统计结束时间
        _user: 当前认证用户
        db: 数据库会话
        
    Returns:
        LogStatsResponse: 包含按级别统计和时间序列统计的响应对象
    """
    # 构建筛选条件，与搜索接口保持一致
    conditions = []
    if host_id is not None:
        conditions.append(LogEntry.host_id == host_id)
    if service:
        conditions.append(LogEntry.service == service)
    if start_time:
        conditions.append(LogEntry.timestamp >= start_time)
    if end_time:
        conditions.append(LogEntry.timestamp <= end_time)

    # 按日志级别统计数量 (Statistics by log level)
    # 用于饼图或柱状图展示不同级别日志的分布
    level_stmt = select(LogEntry.level, func.count(LogEntry.id).label("count")).group_by(LogEntry.level)
    for cond in conditions:
        level_stmt = level_stmt.where(cond)
    level_rows = await db.execute(level_stmt)
    by_level = [LevelCount(level=row.level or "UNKNOWN", count=row.count) for row in level_rows.all()]

    # 按时间分桶统计数量 (Statistics by time buckets)
    # 用于时间序列图展示日志数量的时间趋势
    trunc = "hour" if period == "1h" else "day"  # 根据 period 选择分桶粒度
    bucket = func.date_trunc(trunc, LogEntry.timestamp).label("time_bucket")  # PostgreSQL 时间截断函数
    time_stmt = select(bucket, func.count(LogEntry.id).label("count")).group_by(bucket).order_by(bucket)
    for cond in conditions:
        time_stmt = time_stmt.where(cond)
    time_rows = await db.execute(time_stmt)
    by_time = [TimeCount(time_bucket=row.time_bucket, count=row.count) for row in time_rows.all()]

    return LogStatsResponse(by_level=by_level, by_time=by_time)


# ── WebSocket 实时日志流 (F052) ───────────────────────────────────────
ws_router = APIRouter()  # 独立的 WebSocket 路由器


@ws_router.websocket("/ws/logs")
async def ws_logs(
    websocket: WebSocket,
    host_id: int | None = Query(None),
    service: str | None = Query(None),
    level: str | None = Query(None),
):
    """
    WebSocket 实时日志流 (WebSocket Real-time Log Stream)
    
    建立 WebSocket 连接，向客户端实时推送新产生的日志条目。
    支持客户端侧过滤条件，只推送符合条件的日志，减少网络流量。
    
    连接流程：
    1. 客户端发起 WebSocket 连接
    2. 服务器接受连接并订阅日志广播
    3. 持续接收和过滤日志条目
    4. 向客户端推送符合条件的日志
    5. 连接断开时自动清理订阅
    
    Args:
        websocket: WebSocket 连接对象
        host_id: 可选的主机ID过滤条件
        service: 可选的服务名过滤条件
        level: 可选的日志级别过滤条件，支持多值逗号分隔
        
    Note:
        此函数会一直运行直到客户端断开连接
    """
    await websocket.accept()  # 接受 WebSocket 连接请求
    queue = log_broadcaster.subscribe()  # 订阅日志广播队列
    
    try:
        while True:  # 持续监听和推送日志
            entry = await queue.get()  # 从广播队列中获取新日志条目
            
            # 按客户端指定的条件进行服务端过滤
            if host_id is not None and entry.get("host_id") != host_id:
                continue  # 主机ID不匹配，跳过此条目
            if service and entry.get("service") != service:
                continue  # 服务名不匹配，跳过此条目
            if level:
                levels = [l.strip().upper() for l in level.split(",")]
                if entry.get("level", "").upper() not in levels:
                    continue  # 日志级别不匹配，跳过此条目
                    
            # 向客户端推送符合条件的日志条目
            await websocket.send_json(entry)
    except WebSocketDisconnect:
        pass  # 客户端主动断开连接，正常情况
    finally:
        # 连接结束时清理资源，取消订阅避免内存泄漏
        log_broadcaster.unsubscribe(queue)
