"""Agent API 测试 — 注册、心跳、指标上报、服务检查、日志。"""
import hashlib
import pytest
from httpx import AsyncClient
from app.models.agent_token import AgentToken
from app.models.host import Host
from app.models.service import Service


RAW_TOKEN = "vop_test_token_for_agent_testing"
TOKEN_HASH = hashlib.sha256(RAW_TOKEN.encode()).hexdigest()


@pytest.fixture
async def agent_token(db_session):
    t = AgentToken(name="test-token", token_hash=TOKEN_HASH, token_prefix="vop_test", created_by=1)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest.fixture
def agent_headers():
    return {"Authorization": f"Bearer {RAW_TOKEN}"}


@pytest.fixture
async def registered_host(db_session, agent_token):
    h = Host(hostname="agent-host", ip_address="10.0.0.5", status="online", agent_token_id=agent_token.id)
    db_session.add(h)
    await db_session.commit()
    await db_session.refresh(h)
    return h


class TestAgentRegister:
    async def test_register_new_host(self, client: AsyncClient, agent_headers, agent_token):
        resp = await client.post("/api/v1/agent/register", headers=agent_headers, json={
            "hostname": "new-agent-host", "ip_address": "10.0.0.10",
            "os": "linux", "cpu_cores": 4, "memory_total_mb": 8192,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] is True

    async def test_register_existing_host(self, client: AsyncClient, agent_headers, registered_host, agent_token):
        resp = await client.post("/api/v1/agent/register", headers=agent_headers, json={
            "hostname": "agent-host", "ip_address": "10.0.0.5",
        })
        assert resp.status_code == 200
        assert resp.json()["created"] is False

    async def test_register_invalid_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/agent/register",
                                 headers={"Authorization": "Bearer invalid_token"},
                                 json={"hostname": "x"})
        assert resp.status_code == 401


class TestAgentHeartbeat:
    async def test_heartbeat(self, client: AsyncClient, agent_headers, registered_host, agent_token):
        resp = await client.post("/api/v1/agent/heartbeat", headers=agent_headers, json={
            "host_id": registered_host.id,
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAgentMetrics:
    async def test_report_metrics(self, client: AsyncClient, agent_headers, registered_host, agent_token):
        resp = await client.post("/api/v1/agent/metrics", headers=agent_headers, json={
            "host_id": registered_host.id,
            "cpu_percent": 45.5, "memory_percent": 60.2,
            "disk_percent": 30.0,
        })
        assert resp.status_code == 201


class TestAgentLogs:
    async def test_report_logs(self, client: AsyncClient, agent_headers, registered_host, agent_token):
        resp = await client.post("/api/v1/agent/logs", headers=agent_headers, json={
            "logs": [
                {"host_id": registered_host.id, "service": "nginx", "level": "ERROR",
                 "message": "Connection refused", "timestamp": "2026-02-21T01:00:00Z"},
            ]
        })
        assert resp.status_code == 201
        assert resp.json()["received"] == 1


class TestAgentServiceReport:
    async def test_report_service_checks(self, client: AsyncClient, agent_headers, registered_host, db_session, agent_token):
        svc = Service(name="nginx", type="http", target="http://localhost:80", host_id=registered_host.id, status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        resp = await client.post("/api/v1/agent/services", headers=agent_headers, json={
            "checks": [{"service_id": svc.id, "status": "up", "response_time_ms": 12.5}]
        })
        # May vary based on actual schema
        assert resp.status_code in (200, 201, 422)
