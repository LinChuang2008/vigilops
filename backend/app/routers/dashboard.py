"""
仪表盘数据接口模块。

提供仪表盘趋势数据查询接口，返回最近 24 小时每小时的聚合指标。
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.host_metric import HostMetric
from app.models.alert import Alert
from app.models.log_entry import LogEntry
from app.models.user import User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/trends")
async def get_trends(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取最近 24 小时每小时的趋势数据。

    返回每小时的平均 CPU、平均内存、告警数和错误日志数。
    """
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    # 每小时平均 CPU 和内存（使用 date_trunc 按小时分组）
    metric_sql = text("""
        SELECT
            date_trunc('hour', recorded_at) AS hour,
            avg(cpu_percent) AS avg_cpu,
            avg(memory_percent) AS avg_mem
        FROM host_metrics
        WHERE recorded_at >= :since
        GROUP BY date_trunc('hour', recorded_at)
        ORDER BY hour ASC
    """)
    metric_result = await db.execute(metric_sql, {"since": since})
    metric_rows = metric_result.mappings().all()

    # 每小时告警数
    alert_sql = text("""
        SELECT
            date_trunc('hour', fired_at) AS hour,
            count(*) AS cnt
        FROM alerts
        WHERE fired_at >= :since
        GROUP BY date_trunc('hour', fired_at)
        ORDER BY hour ASC
    """)
    alert_result = await db.execute(alert_sql, {"since": since})
    alert_rows = alert_result.mappings().all()

    # 每小时错误日志数
    log_sql = text("""
        SELECT
            date_trunc('hour', timestamp) AS hour,
            count(*) AS cnt
        FROM log_entries
        WHERE timestamp >= :since AND level IN ('ERROR', 'CRITICAL', 'FATAL')
        GROUP BY date_trunc('hour', timestamp)
        ORDER BY hour ASC
    """)
    log_result = await db.execute(log_sql, {"since": since})
    log_rows = log_result.mappings().all()

    # 构建 24 小时时间轴
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hours = []
    for i in range(24):
        h = now - timedelta(hours=23 - i)
        hours.append(h)

    # 将数据库结果映射到时间轴
    metric_map = {row["hour"].replace(tzinfo=timezone.utc): row for row in metric_rows}
    alert_map = {row["hour"].replace(tzinfo=timezone.utc): row["cnt"] for row in alert_rows}
    log_map = {row["hour"].replace(tzinfo=timezone.utc): row["cnt"] for row in log_rows}

    result = []
    for h in hours:
        m = metric_map.get(h)
        result.append({
            "hour": h.isoformat(),
            "avg_cpu": round(float(m["avg_cpu"]), 1) if m and m["avg_cpu"] is not None else None,
            "avg_mem": round(float(m["avg_mem"]), 1) if m and m["avg_mem"] is not None else None,
            "alert_count": int(alert_map.get(h, 0)),
            "error_log_count": int(log_map.get(h, 0)),
        })

    return {"trends": result}
