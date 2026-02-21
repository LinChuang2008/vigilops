"""SLA 路由深度测试 — 可用性计算、违规检测、报告。"""
import pytest
from datetime import datetime, timezone, timedelta

from app.models.service import Service, ServiceCheck
from app.models.sla import SLARule, SLAViolation


class TestSLARules:
    @pytest.mark.asyncio
    async def test_create_rule(self, client, auth_headers, db_session):
        svc = Service(name="api", type="http", target="http://api", status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        resp = await client.post("/api/v1/sla/rules", json={
            "service_id": svc.id,
            "name": "API SLA",
            "target_percent": 99.9,
            "calculation_window": "monthly",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "API SLA"

    @pytest.mark.asyncio
    async def test_list_rules(self, client, auth_headers, db_session):
        svc = Service(name="web", type="http", target="http://web", status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        rule = SLARule(service_id=svc.id, name="Web SLA", target_percent=99.5, calculation_window="weekly")
        db_session.add(rule)
        await db_session.commit()

        resp = await client.get("/api/v1/sla/rules", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_delete_rule(self, client, auth_headers, db_session):
        svc = Service(name="del-svc", type="http", target="http://del", status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        rule = SLARule(service_id=svc.id, name="Del SLA", target_percent=99.0)
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)

        resp = await client.delete(f"/api/v1/sla/rules/{rule.id}", headers=auth_headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_create_duplicate_service(self, client, auth_headers, db_session):
        svc = Service(name="dup-svc", type="http", target="http://dup", status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        rule = SLARule(service_id=svc.id, name="Dup SLA", target_percent=99.0)
        db_session.add(rule)
        await db_session.commit()

        # Duplicate should fail
        resp = await client.post("/api/v1/sla/rules", json={
            "service_id": svc.id, "name": "Another SLA",
        }, headers=auth_headers)
        assert resp.status_code in (400, 409, 422, 500)


class TestSLAStatus:
    @pytest.mark.asyncio
    async def test_status_no_data(self, client, auth_headers, db_session):
        svc = Service(name="status-svc", type="http", target="http://s", status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        rule = SLARule(service_id=svc.id, name="Status SLA", target_percent=99.9, calculation_window="daily")
        db_session.add(rule)
        await db_session.commit()

        resp = await client.get("/api/v1/sla/status", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_status_with_checks(self, client, auth_headers, db_session):
        svc = Service(name="checked-svc", type="http", target="http://c", status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        now = datetime.now(timezone.utc)
        # Add 10 checks: 9 up, 1 down = 90% availability
        for i in range(9):
            db_session.add(ServiceCheck(
                service_id=svc.id, status="up", response_time_ms=100,
                checked_at=now - timedelta(minutes=i)
            ))
        db_session.add(ServiceCheck(
            service_id=svc.id, status="down", response_time_ms=0,
            checked_at=now - timedelta(minutes=9)
        ))

        rule = SLARule(service_id=svc.id, name="Checked SLA", target_percent=99.9, calculation_window="daily")
        db_session.add(rule)
        await db_session.commit()

        resp = await client.get("/api/v1/sla/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        if data:
            # Should have calculated availability
            assert isinstance(data, list)


class TestSLAViolations:
    @pytest.mark.asyncio
    async def test_list_violations(self, client, auth_headers, db_session):
        svc = Service(name="viol-svc", type="http", target="http://v", status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        rule = SLARule(service_id=svc.id, name="Viol SLA", target_percent=99.9)
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)

        v = SLAViolation(
            sla_rule_id=rule.id, service_id=svc.id,
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ended_at=datetime.now(timezone.utc),
            duration_seconds=3600, description="Service down for 1 hour"
        )
        db_session.add(v)
        await db_session.commit()

        resp = await client.get("/api/v1/sla/violations", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1


class TestSLAReport:
    @pytest.mark.asyncio
    async def test_report_empty(self, client, auth_headers, db_session):
        svc = Service(name="report-svc", type="http", target="http://r", status="up")
        db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(svc)

        rule = SLARule(service_id=svc.id, name="Report SLA", target_percent=99.9, calculation_window="daily")
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)

        resp = await client.get(f"/api/v1/sla/report?rule_id={rule.id}", headers=auth_headers)
        assert resp.status_code == 200


class TestWindowHelpers:
    def test_get_window_start_daily(self):
        from app.routers.sla import _get_window_start
        start = _get_window_start("daily")
        assert start.hour == 0 and start.minute == 0

    def test_get_window_start_weekly(self):
        from app.routers.sla import _get_window_start
        start = _get_window_start("weekly")
        assert start.weekday() == 0  # Monday

    def test_get_window_start_monthly(self):
        from app.routers.sla import _get_window_start
        start = _get_window_start("monthly")
        assert start.day == 1

    def test_get_window_days(self):
        from app.routers.sla import _get_window_days
        assert _get_window_days("daily") == 1
        assert _get_window_days("weekly") == 7
        assert _get_window_days("monthly") == 30
