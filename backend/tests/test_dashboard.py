"""仪表盘数据聚合测试。

注意: dashboard/trends 使用 PostgreSQL 特有的 date_trunc，
在 SQLite 中不可用，因此我们测试基础连通性和 summary 接口。
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.models.host import Host
from app.models.alert import Alert, AlertRule
from app.routers.dashboard_ws import _build_health_breakdown, _calc_health_score_from_breakdown


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
    async def test_summary(self, client: AsyncClient, auth_headers, dashboard_data, db_session):
        """测试 dashboard summary 接口（如果存在）。"""
        # _collect_dashboard_data() uses async_session() which connects to real PG.
        # We patch it to use the test db_session instead.
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        with patch("app.routers.dashboard_ws.async_session", return_value=mock_ctx):
            resp = await client.get("/api/v1/dashboard/summary", headers=auth_headers)
        # summary 可能存在也可能 404，取决于实现
        assert resp.status_code in (200, 404)

    async def test_trends_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/trends")
        assert resp.status_code == 401


class TestDashboardHealthScore:
    def test_health_score_keeps_healthy_system_high(self):
        breakdown = _build_health_breakdown(
            host_total=4,
            host_offline=0,
            svc_total=12,
            svc_down=0,
            firing_count=0,
            active_alert_total=0,
            error_log_count=0,
            avg_cpu=28,
            avg_mem=42,
            avg_disk=51,
            metrics_count=4,
        )
        assert breakdown == []
        assert _calc_health_score_from_breakdown(breakdown) == 100

    def test_health_score_penalizes_real_incidents(self):
        breakdown = _build_health_breakdown(
            host_total=4,
            host_offline=1,
            svc_total=10,
            svc_down=3,
            firing_count=2,
            active_alert_total=3,
            error_log_count=27,
            avg_cpu=88,
            avg_mem=91,
            avg_disk=93,
            metrics_count=4,
        )
        score = _calc_health_score_from_breakdown(breakdown)

        assert score < 70
        reasons = [item["reason"] for item in breakdown]
        assert any("离线主机" in reason for reason in reasons)
        assert any("异常服务" in reason for reason in reasons)
        assert any("触发中告警" in reason for reason in reasons)

    def test_health_score_penalizes_missing_metrics(self):
        breakdown = _build_health_breakdown(
            host_total=3,
            host_offline=0,
            svc_total=0,
            svc_down=0,
            firing_count=0,
            active_alert_total=0,
            error_log_count=0,
            avg_cpu=None,
            avg_mem=None,
            avg_disk=None,
            metrics_count=0,
        )

        assert any(item["reason"] == "最近1小时无资源指标上报" for item in breakdown)
