"""日志搜索路由测试。"""
import pytest
from httpx import AsyncClient
from app.models.log_entry import LogEntry
from app.models.host import Host
from datetime import datetime, timezone


@pytest.fixture
async def sample_logs(db_session):
    h = Host(hostname="log-host", status="online", agent_token_id=1)
    db_session.add(h)
    await db_session.commit()
    await db_session.refresh(h)

    for level in ["INFO", "ERROR", "WARN"]:
        entry = LogEntry(host_id=h.id, service="nginx", level=level,
                         message=f"Test {level} message",
                         timestamp=datetime.now(timezone.utc))
        db_session.add(entry)
    await db_session.commit()
    return h


class TestLogs:
    async def test_search_logs(self, client: AsyncClient, auth_headers, sample_logs):
        resp = await client.get("/api/v1/logs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3

    async def test_search_logs_by_level(self, client: AsyncClient, auth_headers, sample_logs):
        resp = await client.get("/api/v1/logs?level=ERROR", headers=auth_headers)
        assert resp.json()["total"] >= 1

    async def test_search_logs_by_host(self, client: AsyncClient, auth_headers, sample_logs):
        resp = await client.get(f"/api/v1/logs?host_id={sample_logs.id}", headers=auth_headers)
        assert resp.json()["total"] >= 3

    async def test_search_logs_by_keyword(self, client: AsyncClient, auth_headers, sample_logs):
        resp = await client.get("/api/v1/logs?q=Test", headers=auth_headers)
        assert resp.json()["total"] >= 1

    async def test_search_logs_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/logs")
        assert resp.status_code == 403

    async def test_log_stats(self, client: AsyncClient, auth_headers, sample_logs):
        resp = await client.get("/api/v1/logs/stats", headers=auth_headers)
        assert resp.status_code == 200
