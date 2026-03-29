"""LLM 客户端服务测试（mock DeepSeek API）。"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm_client import chat_completion, LLMClientError


class TestLLMClient:
    @patch("app.services.llm_client.settings")
    @pytest.mark.asyncio
    async def test_chat_completion_missing_key_raises(self, mock_settings):
        mock_settings.ai_api_key = ""
        with pytest.raises(LLMClientError, match="AI API Key 未配置"):
            await chat_completion([{"role": "user", "content": "hi"}])

    @patch("httpx.AsyncClient.post")
    @patch("app.services.llm_client.settings")
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, mock_settings, mock_post):
        mock_settings.ai_api_key = "test-key"
        mock_settings.ai_api_base = "https://api.example.com"
        mock_settings.ai_model = "test-model"
        mock_settings.environment = "test"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"summary": "All normal"}'}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = await chat_completion([{"role": "user", "content": "test"}])
        assert result == '{"summary": "All normal"}'
        mock_post.assert_called_once()
