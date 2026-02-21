"""服务监控路由测试。"""
import pytest
from httpx import AsyncClient
from app.models.service import Service, ServiceCheck
from app.models.host import Host


@pytest.fixture
async def sample_service(db_session):
    h = Host(hostname="svc-host", status="online", agent_token_id=1)
    db_session.add(h)
    await db_session.commit()
    await db_session.refresh(h)

    svc = Service(name="backend", type="http", target="http://localhost:8000",
                  host_id=h.id, status="up", is_active=True, category="business")
    db_session.add(svc)
    await db_session.commit()
    await db_session.refresh(svc)
    return svc


class TestServices:
    async def test_list_services(self, client: AsyncClient, auth_headers, sample_service):
        resp = await client.get("/api/v1/services", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_list_services_filter_status(self, client: AsyncClient, auth_headers, sample_service):
        resp = await client.get("/api/v1/services?status=down", headers=auth_headers)
        assert resp.json()["total"] == 0

    async def test_list_services_filter_category(self, client: AsyncClient, auth_headers, sample_service):
        resp = await client.get("/api/v1/services?category=business", headers=auth_headers)
        assert resp.json()["total"] >= 1

    async def test_get_service(self, client: AsyncClient, auth_headers, sample_service):
        resp = await client.get(f"/api/v1/services/{sample_service.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "backend"

    async def test_get_nonexistent_service(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/services/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_get_service_checks(self, client: AsyncClient, auth_headers, sample_service, db_session):
        sc = ServiceCheck(service_id=sample_service.id, status="up", response_time_ms=15.0)
        db_session.add(sc)
        await db_session.commit()
        resp = await client.get(f"/api/v1/services/{sample_service.id}/checks", headers=auth_headers)
        assert resp.status_code == 200

    async def test_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/services")
        assert resp.status_code == 403
