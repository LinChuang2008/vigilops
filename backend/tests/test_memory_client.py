"""MemoryClient 单元测试（mock API）。"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.memory_client import MemoryClient


@pytest.fixture
def client():
    return MemoryClient()


@pytest.mark.asyncio
async def test_recall_success(client):
    """recall 正常返回记忆列表。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {"content": "磁盘满故障，清理 /tmp 解决", "score": 0.9},
            {"content": "OOM 导致服务重启", "score": 0.7},
        ]
    }

    with patch("app.services.memory_client.settings") as mock_settings:
        mock_settings.memory_enabled = True
        mock_settings.memory_api_url = "http://test:8002/api/v1/memory"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http

            results = await client.recall("磁盘告警")
            assert len(results) == 2
            assert "磁盘满" in results[0]["content"]


@pytest.mark.asyncio
async def test_recall_disabled(client):
    """memory_enabled=False 时直接返回空。"""
    with patch("app.services.memory_client.settings") as mock_settings:
        mock_settings.memory_enabled = False
        results = await client.recall("any query")
        assert results == []


@pytest.mark.asyncio
async def test_recall_api_failure(client):
    """API 失败时静默返回空列表，不抛异常。"""
    with patch("app.services.memory_client.settings") as mock_settings:
        mock_settings.memory_enabled = True
        mock_settings.memory_api_url = "http://test:8002/api/v1/memory"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post.side_effect = Exception("connection refused")
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http

            results = await client.recall("test")
            assert results == []


@pytest.mark.asyncio
async def test_store_success(client):
    """store 正常存储返回 True。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    with patch("app.services.memory_client.settings") as mock_settings:
        mock_settings.memory_enabled = True
        mock_settings.memory_api_url = "http://test:8002/api/v1/memory"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http

            ok = await client.store("test content", source="test")
            assert ok is True


@pytest.mark.asyncio
async def test_store_failure_silent(client):
    """store 失败时静默返回 False。"""
    with patch("app.services.memory_client.settings") as mock_settings:
        mock_settings.memory_enabled = True
        mock_settings.memory_api_url = "http://test:8002/api/v1/memory"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post.side_effect = Exception("timeout")
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http

            ok = await client.store("test")
            assert ok is False


@pytest.mark.asyncio
async def test_recall_list_format(client):
    """API 直接返回列表格式时正常处理。"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [{"content": "memory 1"}, {"content": "memory 2"}]

    with patch("app.services.memory_client.settings") as mock_settings:
        mock_settings.memory_enabled = True
        mock_settings.memory_api_url = "http://test:8002/api/v1/memory"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http

            results = await client.recall("test")
            assert len(results) == 2
