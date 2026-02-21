"""修复操作路由测试。"""
import pytest
from httpx import AsyncClient
from app.models.remediation_log import RemediationLog
from app.models.alert import Alert, AlertRule
from app.models.host import Host


@pytest.fixture
async def sample_remediation(db_session):
    h = Host(hostname="rem-host", status="online", agent_token_id=1)
    db_session.add(h)
    rule = AlertRule(name="R", severity="warning", metric="cpu", operator=">", threshold=80, duration_seconds=60)
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(h)
    await db_session.refresh(rule)

    alert = Alert(rule_id=rule.id, host_id=h.id, severity="warning", status="firing", title="CPU High")
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    rem = RemediationLog(
        alert_id=alert.id, host_id=h.id, status="success",
        runbook_name="service_restart", triggered_by="auto",
        risk_level="auto",
    )
    db_session.add(rem)
    await db_session.commit()
    await db_session.refresh(rem)
    return rem


class TestRemediationRoutes:
    async def test_list_remediations(self, client: AsyncClient, auth_headers, sample_remediation):
        resp = await client.get("/api/v1/remediations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_list_filter_status(self, client: AsyncClient, auth_headers, sample_remediation):
        resp = await client.get("/api/v1/remediations?status=failed", headers=auth_headers)
        assert resp.json()["total"] == 0

    async def test_get_remediation(self, client: AsyncClient, auth_headers, sample_remediation):
        resp = await client.get(f"/api/v1/remediations/{sample_remediation.id}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_remediation_stats(self, client: AsyncClient, auth_headers, sample_remediation):
        resp = await client.get("/api/v1/remediations/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/remediations")
        assert resp.status_code == 403
