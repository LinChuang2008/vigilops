"""记忆客户端深度测试。"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.memory_client import MemoryClient


@pytest.fixture
def client():
    c = MemoryClient()
    return c


class TestRecall:
    @pytest.mark.asyncio
    async def test_disabled(self, client):
        with patch.object(type(client), "_enabled", new_callable=lambda: property(lambda self: False)):
            result = await client.recall("test query")
            assert result == []

    @pytest.mark.asyncio
    async def test_success_list_response(self, client):
        with patch.object(type(client), "_enabled", new_callable=lambda: property(lambda self: True)):
            with patch("app.services.memory_client.httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.raise_for_status = MagicMock()
                mock_resp.json.return_value = [{"content": "past experience"}]
                mock_client.post.return_value = mock_resp
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await client.recall("CPU issue")
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_success_dict_response(self, client):
        with patch.object(type(client), "_enabled", new_callable=lambda: property(lambda self: True)):
            with patch("app.services.memory_client.httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.raise_for_status = MagicMock()
                mock_resp.json.return_value = {"memories": [{"content": "data"}]}
                mock_client.post.return_value = mock_resp
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await client.recall("test")
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_failure_returns_empty(self, client):
        with patch.object(type(client), "_enabled", new_callable=lambda: property(lambda self: True)):
            with patch("app.services.memory_client.httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.side_effect = Exception("timeout")
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await client.recall("test")
                assert result == []


class TestStore:
    @pytest.mark.asyncio
    async def test_disabled(self, client):
        with patch.object(type(client), "_enabled", new_callable=lambda: property(lambda self: False)):
            result = await client.store("test content")
            assert result is False

    @pytest.mark.asyncio
    async def test_success(self, client):
        with patch.object(type(client), "_enabled", new_callable=lambda: property(lambda self: True)):
            with patch("app.services.memory_client.httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.raise_for_status = MagicMock()
                mock_client.post.return_value = mock_resp
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await client.store("test content", source="test")
                assert result is True

    @pytest.mark.asyncio
    async def test_failure_returns_false(self, client):
        with patch.object(type(client), "_enabled", new_callable=lambda: property(lambda self: True)):
            with patch("app.services.memory_client.httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.side_effect = Exception("connection refused")
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await client.store("test")
                assert result is False
