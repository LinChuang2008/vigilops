"""
仪表盘 WebSocket 实时推送模块。

提供 WebSocket 端点，每 30 秒向前端推送仪表盘汇总数据，
包括主机指标、服务状态、告警计数和日志统计。
"""
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, and_, func

from app.core.database import async_session
from app.models.host import Host
from app.models.host_metric import HostMetric
from app.models.service import Service
from app.models.alert import Alert
from app.models.log_entry import LogEntry

logger = logging.getLogger(__name__)

router = APIRouter()

# 推送间隔（秒）
PUSH_INTERVAL = 30


async def _collect_dashboard_data() -> dict:
    """收集仪表盘汇总数据，复用 system_summary 和 _build_chat_context 的查询逻辑。"""
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(hours=1)

        # 主机统计
        host_total = (await db.execute(select(func.count(Host.id)))).scalar() or 0
        host_online = (await db.execute(
            select(func.count(Host.id)).where(Host.status == "online")
        )).scalar() or 0

        # 服务统计
        svc_total = (await db.execute(
            select(func.count(Service.id)).where(Service.is_active == True)
        )).scalar() or 0
        svc_up = (await db.execute(
            select(func.count(Service.id)).where(
                and_(Service.is_active == True, Service.status == "up")
            )
        )).scalar() or 0
        svc_down = (await db.execute(
            select(func.count(Service.id)).where(
                and_(Service.is_active == True, Service.status == "down")
            )
        )).scalar() or 0

        # 最近 1 小时告警数
        alert_count = (await db.execute(
            select(func.count(Alert.id)).where(Alert.fired_at >= since)
        )).scalar() or 0

        # 活跃告警数
        firing_count = (await db.execute(
            select(func.count(Alert.id)).where(Alert.status == "firing")
        )).scalar() or 0

        # 最近 1 小时错误日志数
        error_log_count = (await db.execute(
            select(func.count(LogEntry.id)).where(and_(
                LogEntry.timestamp >= since,
                LogEntry.level.in_(["ERROR", "CRITICAL", "FATAL"]),
            ))
        )).scalar() or 0

        # 各主机最新指标的平均值
        latest_metric_subq = (
            select(
                HostMetric.host_id,
                func.max(HostMetric.recorded_at).label("max_recorded_at"),
            )
            .where(HostMetric.recorded_at >= since)
            .group_by(HostMetric.host_id)
            .subquery()
        )

        # 查询每台主机最新指标
        metric_q = (
            select(HostMetric)
            .join(latest_metric_subq, and_(
                HostMetric.host_id == latest_metric_subq.c.host_id,
                HostMetric.recorded_at == latest_metric_subq.c.max_recorded_at,
            ))
        )
        metric_result = await db.execute(metric_q)
        metrics = metric_result.scalars().all()

        # 计算平均值
        avg_cpu = None
        avg_mem = None
        avg_disk = None
        if metrics:
            cpu_vals = [m.cpu_percent for m in metrics if m.cpu_percent is not None]
            mem_vals = [m.memory_percent for m in metrics if m.memory_percent is not None]
            disk_vals = [m.disk_percent for m in metrics if m.disk_percent is not None]
            if cpu_vals:
                avg_cpu = round(sum(cpu_vals) / len(cpu_vals), 1)
            if mem_vals:
                avg_mem = round(sum(mem_vals) / len(mem_vals), 1)
            if disk_vals:
                avg_disk = round(sum(disk_vals) / len(disk_vals), 1)

        # 计算健康评分
        health_score = _calc_health_score(avg_cpu, avg_mem, avg_disk, svc_down)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hosts": {
                "total": host_total,
                "online": host_online,
                "offline": host_total - host_online,
            },
            "services": {
                "total": svc_total,
                "up": svc_up,
                "down": svc_down,
            },
            "alerts": {
                "total": alert_count,
                "firing": firing_count,
            },
            "recent_1h": {
                "alert_count": alert_count,
                "error_log_count": error_log_count,
            },
            "avg_usage": {
                "cpu_percent": avg_cpu,
                "memory_percent": avg_mem,
                "disk_percent": avg_disk,
            },
            "health_score": health_score,
        }


def _calc_health_score(
    avg_cpu: float | None,
    avg_mem: float | None,
    avg_disk: float | None,
    svc_down: int,
) -> int:
    """计算系统综合健康评分（0-100）。

    算法：score = 100 - (cpu_weight * cpu + mem_weight * mem + disk_weight * disk + svc_penalty)
    - cpu_weight=0.3, mem_weight=0.3, disk_weight=0.2
    - svc_penalty = 异常服务数 * 5
    """
    cpu = avg_cpu if avg_cpu is not None else 0
    mem = avg_mem if avg_mem is not None else 0
    disk = avg_disk if avg_disk is not None else 0
    penalty = svc_down * 5

    score = 100 - (0.3 * cpu + 0.3 * mem + 0.2 * disk + penalty)
    return max(0, min(100, round(score)))


@router.websocket("/api/v1/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    """仪表盘 WebSocket 端点，每 30 秒推送一次汇总数据。"""
    await websocket.accept()
    logger.info("仪表盘 WebSocket 客户端已连接")
    try:
        while True:
            try:
                data = await _collect_dashboard_data()
                await websocket.send_text(json.dumps(data, ensure_ascii=False))
            except Exception as e:
                logger.error(f"收集仪表盘数据失败: {e}")
            await asyncio.sleep(PUSH_INTERVAL)
    except WebSocketDisconnect:
        logger.info("仪表盘 WebSocket 客户端已断开")
    except Exception as e:
        logger.error(f"仪表盘 WebSocket 异常: {e}")
