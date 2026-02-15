from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertResponse

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=dict)
async def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    host_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = select(Alert)
    count_q = select(func.count(Alert.id))

    filters = []
    if status:
        filters.append(Alert.status == status)
    if severity:
        filters.append(Alert.severity == severity)
    if host_id:
        filters.append(Alert.host_id == host_id)

    if filters:
        q = q.where(and_(*filters))
        count_q = count_q.where(and_(*filters))

    total = (await db.execute(count_q)).scalar()
    q = q.order_by(Alert.fired_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    alerts = result.scalars().all()

    return {
        "items": [AlertResponse.model_validate(a).model_dump(mode="json") for a in alerts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/ack", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="Alert already resolved")

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user.id
    await db.commit()
    await db.refresh(alert)
    return alert
