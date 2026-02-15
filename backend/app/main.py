from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import get_redis, close_redis
from app.models import User, AgentToken, Host, HostMetric, Service, ServiceCheck, Alert, AlertRule  # noqa: F401 — register models
from app.routers import auth
from app.routers import agent_tokens
from app.routers import agent
from app.routers import hosts
from app.routers import services
from app.routers import alert_rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from app.tasks.offline_detector import offline_detector_loop
    from app.tasks.alert_engine import alert_engine_loop
    from app.services.alert_seed import seed_builtin_rules
    from app.core.database import async_session

    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed built-in alert rules
    async with async_session() as session:
        await seed_builtin_rules(session)

    # Start background tasks
    task = asyncio.create_task(offline_detector_loop())
    alert_task = asyncio.create_task(alert_engine_loop())

    yield

    # Shutdown
    task.cancel()
    alert_task.cancel()
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="VigilOps",
    description="AI-powered infrastructure monitoring platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agent_tokens.router)
app.include_router(agent.router)
app.include_router(hosts.router)
app.include_router(services.router)
app.include_router(alert_rules.router)


@app.get("/health")
async def health():
    checks = {"api": "ok"}

    # DB check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Redis check
    try:
        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}
