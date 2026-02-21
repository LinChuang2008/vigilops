"""服务组管理路由测试。"""
import pytest
from httpx import AsyncClient
from app.models.service_group import ServiceGroup


@pytest.fixture
async def sample_group(db_session):
    g = ServiceGroup(name="redis", category="cache")
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g


class TestServerGroups:
    async def test_list_groups(self, client: AsyncClient, auth_headers, sample_group):
        resp = await client.get("/api/v1/server-groups", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_create_group(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/v1/server-groups", headers=auth_headers, json={
            "name": "nginx", "category": "web",
        })
        assert resp.status_code in (200, 201)

    async def test_get_group(self, client: AsyncClient, auth_headers, sample_group):
        resp = await client.get(f"/api/v1/server-groups/{sample_group.id}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_get_nonexistent_group(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/server-groups/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_group(self, client: AsyncClient, auth_headers, sample_group):
        resp = await client.delete(f"/api/v1/server-groups/{sample_group.id}", headers=auth_headers)
        assert resp.status_code in (200, 204)
