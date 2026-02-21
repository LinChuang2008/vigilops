"""Topology 路由深度测试 — 拓扑查询、依赖管理、布局保存、AI推荐。"""
import pytest
from unittest.mock import AsyncMock, patch

from app.models.service import Service
from app.models.service_dependency import ServiceDependency
from app.models.topology_layout import TopologyLayout


class TestTopologyGet:
    @pytest.mark.asyncio
    async def test_get_topology_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/topology", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data

    @pytest.mark.asyncio
    async def test_get_topology_with_services(self, client, auth_headers, db_session):
        s1 = Service(name="api", type="http", target="http://api:8000", status="up", category="business")
        s2 = Service(name="postgres", type="tcp", target="db:5432", status="up", category="middleware")
        db_session.add_all([s1, s2])
        await db_session.commit()
        await db_session.refresh(s1)
        await db_session.refresh(s2)

        dep = ServiceDependency(source_service_id=s1.id, target_service_id=s2.id, dependency_type="calls")
        db_session.add(dep)
        await db_session.commit()

        resp = await client.get("/api/v1/topology", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1

    @pytest.mark.asyncio
    async def test_get_topology_hierarchical(self, client, auth_headers, db_session):
        s = Service(name="redis", type="tcp", target="redis:6379", status="up", category="middleware")
        db_session.add(s)
        await db_session.commit()

        resp = await client.get("/api/v1/topology?layout=hierarchical", headers=auth_headers)
        assert resp.status_code == 200


class TestDependencies:
    @pytest.mark.asyncio
    async def test_create_dependency(self, client, auth_headers, db_session):
        s1 = Service(name="frontend", type="http", target="http://fe:3000", status="up")
        s2 = Service(name="backend", type="http", target="http://be:8000", status="up")
        db_session.add_all([s1, s2])
        await db_session.commit()
        await db_session.refresh(s1)
        await db_session.refresh(s2)

        resp = await client.post("/api/v1/topology/dependencies", json={
            "source_service_id": s1.id,
            "target_service_id": s2.id,
            "dependency_type": "calls",
        }, headers=auth_headers)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_delete_dependency(self, client, auth_headers, db_session):
        s1 = Service(name="a", type="http", target="http://a", status="up")
        s2 = Service(name="b", type="http", target="http://b", status="up")
        db_session.add_all([s1, s2])
        await db_session.commit()
        await db_session.refresh(s1)
        await db_session.refresh(s2)

        dep = ServiceDependency(source_service_id=s1.id, target_service_id=s2.id, dependency_type="calls")
        db_session.add(dep)
        await db_session.commit()
        await db_session.refresh(dep)

        resp = await client.delete(f"/api/v1/topology/dependencies/{dep.id}", headers=auth_headers)
        assert resp.status_code == 204


class TestLayoutSave:
    @pytest.mark.asyncio
    async def test_save_layout(self, client, auth_headers, db_session):
        resp = await client.post("/api/v1/topology/layout", json={
            "positions": {"node_1": {"x": 100, "y": 200}},
            "name": "default",
        }, headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_load_layout(self, client, auth_headers, db_session):
        # Save first
        await client.post("/api/v1/topology/layout", json={
            "positions": {"node_1": {"x": 100, "y": 200}},
            "name": "test-layout",
        }, headers=auth_headers)

        resp = await client.get("/api/v1/topology/layout?name=test-layout", headers=auth_headers)
        assert resp.status_code == 200


class TestAIRecommend:
    @pytest.mark.asyncio
    async def test_recommend_dependencies(self, client, auth_headers, db_session):
        s1 = Service(name="nginx", type="http", target="http://nginx", status="up")
        s2 = Service(name="backend-api", type="http", target="http://api", status="up")
        db_session.add_all([s1, s2])
        await db_session.commit()

        ai_resp = '[{"source": "nginx", "target": "backend-api", "type": "proxy", "reason": "reverse proxy"}]'
        with patch("app.routers.topology.ai_engine") as mock_ai:
            mock_ai._call_api = AsyncMock(return_value=ai_resp)
            resp = await client.get("/api/v1/topology/recommend-dependencies", headers=auth_headers)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_classify_service(self):
        from app.routers.topology import _classify_service
        assert _classify_service("PostgreSQL") == "database"
        assert _classify_service("Redis Cache") == "cache"
        assert _classify_service("RabbitMQ") == "mq"
        assert _classify_service("Nginx") == "web"
        assert _classify_service("backend-api") == "api"
        assert _classify_service("my-app") == "app"
