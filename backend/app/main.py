"""
VigilOps 后端应用入口模块 (VigilOps Backend Application Entry Module)

VigilOps 运维监控平台的主应用入口，负责 FastAPI 应用的完整生命周期管理。
包含应用初始化、中间件配置、路由注册、后台任务启动等核心功能。

Main application entry point for the VigilOps operations monitoring platform,
responsible for complete FastAPI application lifecycle management.
Includes application initialization, middleware configuration, route registration, and background task startup.

主要功能 (Main Features):
- 数据库表自动创建和初始化 (Automatic database table creation and initialization)
- 内置告警规则种子数据 (Built-in alert rule seed data)
- 后台任务管理：离线检测、告警引擎、日志清理等 (Background task management)
- AI 异常检测和自动修复 (AI anomaly detection and auto-remediation)
- WebSocket 实时数据推送 (Real-time data push via WebSocket)
- 健康检查和监控 (Health checks and monitoring)
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings as app_settings
from app.core.database import engine, Base
from app.core.redis import get_redis, close_redis
# 导入所有模型以确保 SQLAlchemy 表注册 (Import all models to ensure SQLAlchemy table registration)
from app.models import User, AgentToken, Host, HostMetric, Service, ServiceCheck, Alert, AlertRule, NotificationChannel, NotificationLog, NotificationTemplate, LogEntry, MonitoredDatabase, DbMetric, AIInsight, AuditLog, Report, ServiceDependency, SLARule, SLAViolation  # noqa: F401
# 导入所有路由模块 (Import all router modules)
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
from app.routers import remediation
from app.routers import servers
from app.routers import server_groups


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器 (Application Lifecycle Manager)
    
    管理 VigilOps 应用的完整生命周期，包括启动时的初始化和关闭时的清理。
    负责数据库表创建、内置数据初始化、后台任务启动和资源释放。
    
    Manages the complete lifecycle of the VigilOps application, including initialization
    at startup and cleanup at shutdown. Responsible for database table creation,
    built-in data initialization, background task startup, and resource cleanup.
    """
    import asyncio
    import os
    from app.tasks.offline_detector import offline_detector_loop
    from app.tasks.alert_engine import alert_engine_loop
    from app.tasks.log_cleanup import log_cleanup_loop
    from app.tasks.db_metric_cleanup import db_metric_cleanup_loop
    from app.services.alert_seed import seed_builtin_rules
    from app.core.database import async_session

    # 启动阶段：应用初始化 (Startup Phase: Application Initialization)
    
    # 自动创建数据库表结构 (Automatically create database table structure)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化内置告警规则（CPU、内存、磁盘等默认规则） (Initialize built-in alert rules)
    async with async_session() as session:
        await seed_builtin_rules(session)

    # 启动后台定时任务 (Start background scheduled tasks)
    
    # 主机离线检测任务 (Host offline detection task)
    task = asyncio.create_task(offline_detector_loop())
    
    # 告警引擎任务 (Alert engine task)
    alert_task = asyncio.create_task(alert_engine_loop())
    
    # 日志清理任务 (Log cleanup task)
    retention_days = int(os.environ.get("LOG_RETENTION_DAYS", "7"))
    log_cleanup_task = asyncio.create_task(log_cleanup_loop(retention_days))
    
    # 数据库指标清理任务 (Database metric cleanup task)
    db_retention = int(os.environ.get("DB_METRIC_RETENTION_DAYS", "30"))
    db_cleanup_task = asyncio.create_task(db_metric_cleanup_loop(db_retention))

    # 启动 AI 异常扫描后台任务 (Start AI anomaly scanning background task)
    from app.services.anomaly_scanner import anomaly_scanner_loop
    anomaly_task = asyncio.create_task(anomaly_scanner_loop())

    # 启动报告定时生成任务 (Start scheduled report generation task)
    from app.tasks.report_scheduler import report_scheduler_loop
    report_task = asyncio.create_task(report_scheduler_loop())

    # 启动自动修复监听任务（仅在配置启用时） (Start auto-remediation listener task if enabled)
    remediation_task = None
    if app_settings.agent_enabled:
        from app.tasks.remediation_listener import remediation_listener_loop
        remediation_task = asyncio.create_task(remediation_listener_loop())

    # 应用运行阶段 (Application running phase)
    yield

    # 关闭阶段：清理资源和取消任务 (Shutdown Phase: Cleanup resources and cancel tasks)
    
    # 取消所有后台任务 (Cancel all background tasks)
    task.cancel()
    alert_task.cancel()
    log_cleanup_task.cancel()
    db_cleanup_task.cancel()
    anomaly_task.cancel()
    report_task.cancel()
    if remediation_task is not None:
        remediation_task.cancel()
    
    # 关闭连接池和资源 (Close connection pools and resources)
    await close_redis()
    await engine.dispose()


# 创建 FastAPI 应用实例 (Create FastAPI application instance)
app = FastAPI(
    title="VigilOps",
    description="AI-powered infrastructure monitoring platform | AI 驱动的基础设施监控平台",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置 CORS 中间件，允许前端跨域访问 (Configure CORS middleware for frontend cross-origin access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境应限制具体域名 (Allow all origins in dev, restrict in production)
    allow_credentials=True,  # 允许携带认证信息 (Allow credentials)
    allow_methods=["*"],  # 允许所有 HTTP 方法 (Allow all HTTP methods)
    allow_headers=["*"],  # 允许所有请求头 (Allow all headers)
)

# 注册所有 API 路由模块 (Register all API router modules)
app.include_router(auth.router)  # 用户认证 (User authentication)
app.include_router(agent_tokens.router)  # Agent 令牌管理 (Agent token management)
app.include_router(agent.router)  # Agent 数据上报 (Agent data reporting)
app.include_router(hosts.router)  # 主机管理 (Host management)
app.include_router(services.router)  # 服务监控 (Service monitoring)
app.include_router(alert_rules.router)  # 告警规则 (Alert rules)
app.include_router(alerts.router)  # 告警管理 (Alert management)
app.include_router(notifications.router)  # 通知管理 (Notification management)
app.include_router(settings.router)  # 系统设置 (System settings)
app.include_router(logs.router)  # 日志管理 (Log management)
app.include_router(logs.ws_router)  # WebSocket 日志流 (WebSocket log streaming)
app.include_router(databases.router)  # 数据库监控 (Database monitoring)
app.include_router(ai_analysis.router)  # AI 分析 (AI analysis)
app.include_router(users.router)  # 用户管理 (User management)
app.include_router(audit_logs.router)  # 审计日志 (Audit logs)
app.include_router(reports.router)  # 运维报告 (Operations reports)
app.include_router(notification_templates.router)  # 通知模板 (Notification templates)
app.include_router(dashboard_ws.router)  # 仪表盘 WebSocket (Dashboard WebSocket)
app.include_router(dashboard.router)  # 仪表盘数据 (Dashboard data)
app.include_router(topology.router)  # 服务拓扑 (Service topology)
app.include_router(sla.router)  # SLA 管理 (SLA management)
app.include_router(remediation.router)  # 自动修复 (Auto-remediation)
app.include_router(remediation.trigger_router)  # 修复触发器 (Remediation triggers)
app.include_router(servers.router)  # 服务器管理 (Server management)
app.include_router(server_groups.router)  # 服务器分组 (Server grouping)


@app.get("/health")
@app.get("/api/v1/health")
async def health():
    """
    健康检查接口 (Health Check Endpoint)
    
    验证 VigilOps 平台各个核心组件的连通性和状态，包括 API、数据库、Redis 缓存等。
    用于负载均衡器健康检查、监控系统状态检测和运维故障排查。
    
    Verifies connectivity and status of core VigilOps platform components,
    including API, database, Redis cache, etc. Used for load balancer health checks,
    monitoring system status detection, and operational troubleshooting.
    
    Returns:
        dict: 包含各组件状态和时间戳的健康检查结果 (Health check results with component status and timestamp)
    """
    checks = {"api": "ok"}

    # 数据库连通性检查 (Database connectivity check)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Redis 连通性检查 (Redis connectivity check)
    try:
        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    # 综合状态评估 (Overall status assessment)
    # 所有组件正常则返回 ok，否则返回 degraded (Return 'ok' if all components are healthy, otherwise 'degraded')
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    
    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
