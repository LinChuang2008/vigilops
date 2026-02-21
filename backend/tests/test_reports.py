"""运维报告路由测试。"""
import pytest
from httpx import AsyncClient
from app.models.report import Report
from datetime import datetime, timezone


@pytest.fixture
async def sample_report(db_session):
    r = Report(
        title="日报 2026-02-21", report_type="daily",
        period_start=datetime(2026, 2, 20, tzinfo=timezone.utc),
        period_end=datetime(2026, 2, 21, tzinfo=timezone.utc),
        content="# Report\n\nAll systems normal.",
        summary="正常运行", status="completed",
    )
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)
    return r


class TestReports:
    async def test_list_reports(self, client: AsyncClient, auth_headers, sample_report):
        resp = await client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_list_reports_filter_type(self, client: AsyncClient, auth_headers, sample_report):
        resp = await client.get("/api/v1/reports?report_type=weekly", headers=auth_headers)
        assert resp.json()["total"] == 0

    async def test_get_report(self, client: AsyncClient, auth_headers, sample_report):
        resp = await client.get(f"/api/v1/reports/{sample_report.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert "日报" in resp.json()["title"]

    async def test_get_nonexistent_report(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/reports/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_report(self, client: AsyncClient, auth_headers, sample_report):
        resp = await client.delete(f"/api/v1/reports/{sample_report.id}", headers=auth_headers)
        assert resp.status_code in (200, 204)

    async def test_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/reports")
        assert resp.status_code == 403
