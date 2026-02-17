"""日志管理路由模块。

提供日志搜索/筛选、统计分析和 WebSocket 实时日志流功能。
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
    """日志广播器，基于内存队列实现发布-订阅模式。"""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """创建并注册一个新的订阅队列。"""
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """移除订阅队列。"""
        self._subscribers.remove(q)

    async def publish(self, entries: list[dict]):
        """向所有订阅者广播日志条目，消费者过慢时丢弃消息。"""
        for q in list(self._subscribers):
            for entry in entries:
                try:
                    q.put_nowait(entry)
                except asyncio.QueueFull:
                    pass  # 消费者处理过慢，丢弃该条目


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
    """搜索日志条目，支持全文检索、主机/服务/级别/时间范围筛选，分页返回。"""
    base = select(LogEntry)
    count_base = select(func.count(LogEntry.id))

    # 构建动态过滤条件
    conditions = []
    if q:
        conditions.append(LogEntry.message.ilike(f"%{q}%"))
    if host_id is not None:
        conditions.append(LogEntry.host_id == host_id)
    if service:
        conditions.append(LogEntry.service == service)
    if level:
        levels = [l.strip().upper() for l in level.split(",") if l.strip()]
        conditions.append(LogEntry.level.in_(levels))
    if start_time:
        conditions.append(LogEntry.timestamp >= start_time)
    if end_time:
        conditions.append(LogEntry.timestamp <= end_time)

    for cond in conditions:
        base = base.where(cond)
        count_base = count_base.where(cond)

    total_result = await db.execute(count_base)
    total = total_result.scalar() or 0

    # 关联 Host 表以获取主机名
    offset = (page - 1) * page_size
    stmt = (
        select(LogEntry, Host.hostname)
        .outerjoin(Host, LogEntry.host_id == Host.id)
    )
    for cond in conditions:
        stmt = stmt.where(cond)
    stmt = stmt.order_by(LogEntry.timestamp.desc()).offset(offset).limit(page_size)
    rows = await db.execute(stmt)
    items = []
    for log_entry, hostname in rows.all():
        item = LogEntryResponse.model_validate(log_entry)
        item.hostname = hostname
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
    """获取日志统计数据，按级别和时间分桶聚合。"""
    conditions = []
    if host_id is not None:
        conditions.append(LogEntry.host_id == host_id)
    if service:
        conditions.append(LogEntry.service == service)
    if start_time:
        conditions.append(LogEntry.timestamp >= start_time)
    if end_time:
        conditions.append(LogEntry.timestamp <= end_time)

    # 按日志级别统计数量
    level_stmt = select(LogEntry.level, func.count(LogEntry.id).label("count")).group_by(LogEntry.level)
    for cond in conditions:
        level_stmt = level_stmt.where(cond)
    level_rows = await db.execute(level_stmt)
    by_level = [LevelCount(level=row.level or "UNKNOWN", count=row.count) for row in level_rows.all()]

    # 按时间分桶统计数量（小时或天）
    trunc = "hour" if period == "1h" else "day"
    bucket = func.date_trunc(trunc, LogEntry.timestamp).label("time_bucket")
    time_stmt = select(bucket, func.count(LogEntry.id).label("count")).group_by(bucket).order_by(bucket)
    for cond in conditions:
        time_stmt = time_stmt.where(cond)
    time_rows = await db.execute(time_stmt)
    by_time = [TimeCount(time_bucket=row.time_bucket, count=row.count) for row in time_rows.all()]

    return LogStatsResponse(by_level=by_level, by_time=by_time)


# ── WebSocket 实时日志流 (F052) ───────────────────────────────────────
ws_router = APIRouter()


@ws_router.websocket("/ws/logs")
async def ws_logs(
    websocket: WebSocket,
    host_id: int | None = Query(None),
    service: str | None = Query(None),
    level: str | None = Query(None),
):
    """WebSocket 实时日志流，支持按主机、服务和级别过滤推送。"""
    await websocket.accept()
    queue = log_broadcaster.subscribe()
    try:
        while True:
            entry = await queue.get()
            # 按客户端指定的条件过滤
            if host_id is not None and entry.get("host_id") != host_id:
                continue
            if service and entry.get("service") != service:
                continue
            if level:
                levels = [l.strip().upper() for l in level.split(",")]
                if entry.get("level", "").upper() not in levels:
                    continue
            await websocket.send_json(entry)
    except WebSocketDisconnect:
        pass
    finally:
        log_broadcaster.unsubscribe(queue)
