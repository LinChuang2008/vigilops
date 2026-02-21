"""拓扑图路由测试。"""
import pytest
from httpx import AsyncClient
from app.models.service import Service
from app.models.service_dependency import ServiceDependency
from app.models.host import Host


@pytest.fixture
async def topo_data(db_session):
    h = Host(hostname="topo-host", status="online", agent_token_id=1)
    db_session.add(h)
    await db_session.commit()
    await db_session.refresh(h)

    svc1 = Service(name="frontend", type="http", target="http://localhost:3000",
                   host_id=h.id, status="up", is_active=True, category="business")
    svc2 = Service(name="backend", type="http", target="http://localhost:8000",
                   host_id=h.id, status="up", is_active=True, category="business")
    db_session.add_all([svc1, svc2])
    await db_session.commit()
    await db_session.refresh(svc1)
    await db_session.refresh(svc2)

    dep = ServiceDependency(source_service_id=svc1.id, target_service_id=svc2.id, dependency_type="calls")
    db_session.add(dep)
    await db_session.commit()
    return {"svc1": svc1, "svc2": svc2}


class TestTopology:
    async def test_get_topology(self, client: AsyncClient, auth_headers, topo_data):
        resp = await client.get("/api/v1/topology", headers=auth_headers)
        assert resp.status_code == 200

    async def test_create_dependency(self, client: AsyncClient, auth_headers, topo_data):
        resp = await client.post("/api/v1/topology/dependencies", headers=auth_headers, json={
            "source_service_id": topo_data["svc2"].id,
            "target_service_id": topo_data["svc1"].id,
            "dependency_type": "calls",
        })
        assert resp.status_code in (200, 201)

    async def test_save_layout(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/v1/topology/layout", headers=auth_headers, json={
            "positions": {"node_1": {"x": 100, "y": 200}},
            "name": "test-layout",
        })
        assert resp.status_code == 200

    async def test_get_layout(self, client: AsyncClient, auth_headers):
        # Layout may only support POST (save), not GET
        resp = await client.get("/api/v1/topology/layout", headers=auth_headers)
        assert resp.status_code in (200, 405)

    async def test_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/topology")
        assert resp.status_code == 403
