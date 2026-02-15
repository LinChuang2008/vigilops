import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
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


# ── In-memory broadcast for WebSocket (F052) ──────────────────────────
class LogBroadcaster:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers.remove(q)

    async def publish(self, entries: list[dict]):
        for q in list(self._subscribers):
            for entry in entries:
                try:
                    q.put_nowait(entry)
                except asyncio.QueueFull:
                    pass  # drop if consumer is slow


log_broadcaster = LogBroadcaster()


# ── F049 + F050: Log search / filter ──────────────────────────────────
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
    base = select(LogEntry)
    count_base = select(func.count(LogEntry.id))

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

    offset = (page - 1) * page_size
    stmt = base.order_by(LogEntry.timestamp.desc()).offset(offset).limit(page_size)
    rows = await db.execute(stmt)
    items = [LogEntryResponse.model_validate(r) for r in rows.scalars().all()]

    return LogSearchResponse(items=items, total=total, page=page, page_size=page_size)


# ── F053: Log stats ──────────────────────────────────────────────────
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
    conditions = []
    if host_id is not None:
        conditions.append(LogEntry.host_id == host_id)
    if service:
        conditions.append(LogEntry.service == service)
    if start_time:
        conditions.append(LogEntry.timestamp >= start_time)
    if end_time:
        conditions.append(LogEntry.timestamp <= end_time)

    # By level
    level_stmt = select(LogEntry.level, func.count(LogEntry.id).label("count")).group_by(LogEntry.level)
    for cond in conditions:
        level_stmt = level_stmt.where(cond)
    level_rows = await db.execute(level_stmt)
    by_level = [LevelCount(level=row.level or "UNKNOWN", count=row.count) for row in level_rows.all()]

    # By time bucket
    trunc = "hour" if period == "1h" else "day"
    bucket = func.date_trunc(trunc, LogEntry.timestamp).label("time_bucket")
    time_stmt = select(bucket, func.count(LogEntry.id).label("count")).group_by(bucket).order_by(bucket)
    for cond in conditions:
        time_stmt = time_stmt.where(cond)
    time_rows = await db.execute(time_stmt)
    by_time = [TimeCount(time_bucket=row.time_bucket, count=row.count) for row in time_rows.all()]

    return LogStatsResponse(by_level=by_level, by_time=by_time)


# ── F052: WebSocket real-time log stream ──────────────────────────────
# Mounted separately on the app as /ws/logs (see ws_router below)
ws_router = APIRouter()


@ws_router.websocket("/ws/logs")
async def ws_logs(
    websocket: WebSocket,
    host_id: int | None = Query(None),
    service: str | None = Query(None),
    level: str | None = Query(None),
):
    await websocket.accept()
    queue = log_broadcaster.subscribe()
    try:
        while True:
            entry = await queue.get()
            # Apply filters
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
