from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.log_entry import LogEntry
from app.models.ai_insight import AIInsight
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
    """Manually trigger AI analysis on recent logs."""
    since = datetime.now(timezone.utc) - timedelta(hours=req.hours)

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

    # Save insight to DB
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
    """Get recent AI analysis insights."""
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


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    req: ChatRequest,
    _user: User = Depends(get_current_user),
):
    """Natural language query (placeholder)."""
    answer = await ai_engine.chat(req.question)
    return ChatResponse(answer=answer, sources=[])
