"""
VigilOps 后端应用入口模块。

负责 FastAPI 应用的初始化、中间件配置、路由注册，
以及在应用生命周期内启动和关闭后台任务（离线检测、告警引擎、日志清理等）。
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import get_redis, close_redis
from app.models import User, AgentToken, Host, HostMetric, Service, ServiceCheck, Alert, AlertRule, NotificationChannel, NotificationLog, NotificationTemplate, LogEntry, MonitoredDatabase, DbMetric, AIInsight, AuditLog, Report, ServiceDependency, SLARule, SLAViolation  # noqa: F401 — register models
from app.routers import auth
from app.routers import agent_tokens
from app.routers import agent
from app.routers import hosts
from app.routers import services
from app.routers import alert_rules
from app.routers import alerts
from app.routers import notifications
from app.routers import settings
from app.routers import logs
from app.routers import databases
from app.routers import ai_analysis
from app.routers import users
from app.routers import audit_logs
from app.routers import reports
from app.routers import notification_templates
from app.routers import dashboard_ws
from app.routers import dashboard
from app.routers import topology
from app.routers import sla


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器，负责启动时初始化资源和后台任务，关闭时清理释放。"""
    import asyncio
    import os
    from app.tasks.offline_detector import offline_detector_loop
    from app.tasks.alert_engine import alert_engine_loop
    from app.tasks.log_cleanup import log_cleanup_loop
    from app.tasks.db_metric_cleanup import db_metric_cleanup_loop
    from app.services.alert_seed import seed_builtin_rules
    from app.core.database import async_session

    # 启动阶段：自动创建数据库表结构
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化内置告警规则（CPU、内存、磁盘等默认规则）
    async with async_session() as session:
        await seed_builtin_rules(session)

    # 启动后台定时任务
    task = asyncio.create_task(offline_detector_loop())
    alert_task = asyncio.create_task(alert_engine_loop())
    retention_days = int(os.environ.get("LOG_RETENTION_DAYS", "7"))
    log_cleanup_task = asyncio.create_task(log_cleanup_loop(retention_days))
    db_retention = int(os.environ.get("DB_METRIC_RETENTION_DAYS", "30"))
    db_cleanup_task = asyncio.create_task(db_metric_cleanup_loop(db_retention))

    # 启动 AI 异常扫描后台任务
    from app.services.anomaly_scanner import anomaly_scanner_loop
    anomaly_task = asyncio.create_task(anomaly_scanner_loop())

    # 启动报告定时生成任务
    from app.tasks.report_scheduler import report_scheduler_loop
    report_task = asyncio.create_task(report_scheduler_loop())

    yield

    # 关闭阶段：取消所有后台任务并释放连接
    task.cancel()
    alert_task.cancel()
    log_cleanup_task.cancel()
    db_cleanup_task.cancel()
    anomaly_task.cancel()
    report_task.cancel()
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="VigilOps",
    description="AI-powered infrastructure monitoring platform",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置 CORS 中间件，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有 API 路由
app.include_router(auth.router)
app.include_router(agent_tokens.router)
app.include_router(agent.router)
app.include_router(hosts.router)
app.include_router(services.router)
app.include_router(alert_rules.router)
app.include_router(alerts.router)
app.include_router(notifications.router)
app.include_router(settings.router)
app.include_router(logs.router)
app.include_router(logs.ws_router)
app.include_router(databases.router)
app.include_router(ai_analysis.router)
app.include_router(users.router)
app.include_router(audit_logs.router)
app.include_router(reports.router)
app.include_router(notification_templates.router)
app.include_router(dashboard_ws.router)
app.include_router(dashboard.router)
app.include_router(topology.router)
app.include_router(sla.router)


@app.get("/health")
async def health():
    """健康检查接口，验证 API、数据库和 Redis 的连通性。"""
    checks = {"api": "ok"}

    # 数据库连通性检查
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Redis 连通性检查
    try:
        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    # 所有组件正常则返回 ok，否则返回 degraded
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}
