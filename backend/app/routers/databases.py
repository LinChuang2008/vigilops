"""F064: Database list, detail, and historical metrics endpoints."""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.db_metric import MonitoredDatabase, DbMetric

router = APIRouter(prefix="/api/v1/databases", tags=["databases"])


def _parse_period(period: str) -> timedelta:
    """Parse period string like '1h', '24h', '7d' to timedelta."""
    p = period.strip().lower()
    if p.endswith("h"):
        return timedelta(hours=int(p[:-1]))
    if p.endswith("d"):
        return timedelta(days=int(p[:-1]))
    if p.endswith("m"):
        return timedelta(minutes=int(p[:-1]))
    return timedelta(hours=1)


@router.get("")
async def list_databases(
    host_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List monitored databases with latest metrics."""
    query = select(MonitoredDatabase).order_by(desc(MonitoredDatabase.updated_at))
    if host_id:
        query = query.where(MonitoredDatabase.host_id == host_id)
    result = await db.execute(query)
    databases = result.scalars().all()

    items = []
    for mdb in databases:
        # Get latest metric
        latest = await db.execute(
            select(DbMetric)
            .where(DbMetric.database_id == mdb.id)
            .order_by(desc(DbMetric.recorded_at))
            .limit(1)
        )
        metric = latest.scalar_one_or_none()
        item = {
            "id": mdb.id,
            "host_id": mdb.host_id,
            "name": mdb.name,
            "db_type": mdb.db_type,
            "status": mdb.status,
            "created_at": mdb.created_at.isoformat() if mdb.created_at else None,
            "updated_at": mdb.updated_at.isoformat() if mdb.updated_at else None,
        }
        if metric:
            item["latest_metrics"] = {
                "connections_total": metric.connections_total,
                "connections_active": metric.connections_active,
                "database_size_mb": metric.database_size_mb,
                "slow_queries": metric.slow_queries,
                "tables_count": metric.tables_count,
                "transactions_committed": metric.transactions_committed,
                "transactions_rolled_back": metric.transactions_rolled_back,
                "qps": metric.qps,
                "recorded_at": metric.recorded_at.isoformat() if metric.recorded_at else None,
            }
        items.append(item)

    return {"databases": items, "total": len(items)}


@router.get("/{database_id}")
async def get_database(
    database_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get database detail."""
    result = await db.execute(select(MonitoredDatabase).where(MonitoredDatabase.id == database_id))
    mdb = result.scalar_one_or_none()
    if not mdb:
        raise HTTPException(status_code=404, detail="Database not found")

    # Latest metric
    latest = await db.execute(
        select(DbMetric).where(DbMetric.database_id == mdb.id).order_by(desc(DbMetric.recorded_at)).limit(1)
    )
    metric = latest.scalar_one_or_none()

    data = {
        "id": mdb.id,
        "host_id": mdb.host_id,
        "name": mdb.name,
        "db_type": mdb.db_type,
        "status": mdb.status,
        "created_at": mdb.created_at.isoformat() if mdb.created_at else None,
        "updated_at": mdb.updated_at.isoformat() if mdb.updated_at else None,
    }
    if metric:
        data["latest_metrics"] = {
            "connections_total": metric.connections_total,
            "connections_active": metric.connections_active,
            "database_size_mb": metric.database_size_mb,
            "slow_queries": metric.slow_queries,
            "tables_count": metric.tables_count,
            "transactions_committed": metric.transactions_committed,
            "transactions_rolled_back": metric.transactions_rolled_back,
            "qps": metric.qps,
            "recorded_at": metric.recorded_at.isoformat() if metric.recorded_at else None,
        }
    return data


@router.get("/{database_id}/metrics")
async def get_database_metrics(
    database_id: int,
    period: str = Query("1h"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get historical metrics for a database."""
    # Verify database exists
    result = await db.execute(select(MonitoredDatabase).where(MonitoredDatabase.id == database_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Database not found")

    delta = _parse_period(period)
    since = datetime.now(timezone.utc) - delta

    result = await db.execute(
        select(DbMetric)
        .where(DbMetric.database_id == database_id, DbMetric.recorded_at >= since)
        .order_by(DbMetric.recorded_at)
    )
    metrics = result.scalars().all()

    return {
        "database_id": database_id,
        "period": period,
        "metrics": [
            {
                "connections_total": m.connections_total,
                "connections_active": m.connections_active,
                "database_size_mb": m.database_size_mb,
                "slow_queries": m.slow_queries,
                "tables_count": m.tables_count,
                "transactions_committed": m.transactions_committed,
                "transactions_rolled_back": m.transactions_rolled_back,
                "qps": m.qps,
                "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
            }
            for m in metrics
        ],
    }
