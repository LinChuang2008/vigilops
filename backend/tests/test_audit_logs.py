"""审计日志路由测试。"""
import pytest
from httpx import AsyncClient
from app.models.audit_log import AuditLog


@pytest.fixture
async def sample_audit(db_session, admin_user):
    entry = AuditLog(user_id=admin_user.id, action="login", resource_type="user",
                     resource_id=admin_user.id, ip_address="127.0.0.1")
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)
    return entry


class TestAuditLogs:
    async def test_list_audit_logs_admin(self, client: AsyncClient, auth_headers, sample_audit):
        resp = await client.get("/api/v1/audit-logs", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_filter_by_action(self, client: AsyncClient, auth_headers, sample_audit):
        resp = await client.get("/api/v1/audit-logs?action=login", headers=auth_headers)
        assert resp.json()["total"] >= 1

    async def test_filter_by_resource_type(self, client: AsyncClient, auth_headers, sample_audit):
        resp = await client.get("/api/v1/audit-logs?resource_type=user", headers=auth_headers)
        assert resp.json()["total"] >= 1

    async def test_viewer_cannot_access(self, client: AsyncClient, viewer_headers):
        resp = await client.get("/api/v1/audit-logs", headers=viewer_headers)
        assert resp.status_code == 403
