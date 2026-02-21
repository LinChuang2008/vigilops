"""服务器管理路由测试。"""
import pytest
from httpx import AsyncClient
from app.models.server import Server


@pytest.fixture
async def sample_server(db_session):
    s = Server(hostname="web-01", ip_address="10.0.0.1", label="Web-01",
               status="online", is_simulated=False)
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


class TestServers:
    async def test_list_servers(self, client: AsyncClient, auth_headers, sample_server):
        resp = await client.get("/api/v1/servers", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_list_servers_search(self, client: AsyncClient, auth_headers, sample_server):
        resp = await client.get("/api/v1/servers?search=web", headers=auth_headers)
        assert resp.json()["total"] >= 1

    async def test_create_server(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/v1/servers", headers=auth_headers, json={
            "hostname": "db-01", "ip_address": "10.0.0.2", "label": "DB-01",
        })
        assert resp.status_code in (200, 201)

    async def test_get_server(self, client: AsyncClient, auth_headers, sample_server):
        resp = await client.get(f"/api/v1/servers/{sample_server.id}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_delete_server(self, client: AsyncClient, auth_headers, sample_server):
        resp = await client.delete(f"/api/v1/servers/{sample_server.id}", headers=auth_headers)
        assert resp.status_code in (200, 204)
