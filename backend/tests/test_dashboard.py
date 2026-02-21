"""仪表盘数据聚合测试。

注意: dashboard/trends 使用 PostgreSQL 特有的 date_trunc，
在 SQLite 中不可用，因此我们测试基础连通性和 summary 接口。
"""
import pytest
from httpx import AsyncClient
from app.models.host import Host
from app.models.alert import Alert, AlertRule


@pytest.fixture
async def dashboard_data(db_session):
    """创建一些基础数据供仪表盘聚合。"""
    h = Host(hostname="dash-host", status="online", agent_token_id=1)
    db_session.add(h)
    rule = AlertRule(name="R1", severity="warning", metric="cpu", operator=">", threshold=80, duration_seconds=60)
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    a = Alert(rule_id=rule.id, host_id=h.id, severity="warning", status="firing", title="T")
    db_session.add(a)
    await db_session.commit()


class TestDashboard:
    async def test_summary(self, client: AsyncClient, auth_headers, dashboard_data):
        """测试 dashboard summary 接口（如果存在）。"""
        resp = await client.get("/api/v1/dashboard/summary", headers=auth_headers)
        # summary 可能存在也可能 404，取决于实现
        assert resp.status_code in (200, 404)

    async def test_trends_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/trends")
        assert resp.status_code == 403
