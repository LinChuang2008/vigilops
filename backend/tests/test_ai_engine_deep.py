"""AI 引擎服务深度测试 — mock DeepSeek API，覆盖日志分析、对话、根因分析。"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.ai_engine import AIEngine


@pytest.fixture
def engine():
    e = AIEngine()
    e.api_key = "test-key"
    return e


def _mock_api_response(content: str):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    resp.raise_for_status = MagicMock()
    return resp


class TestCallApi:
    @pytest.mark.asyncio
    async def test_call_api_success(self, engine):
        content = '{"answer": "hello"}'
        with patch("app.services.ai_engine.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_api_response(content)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await engine._call_api([{"role": "user", "content": "hi"}])
            assert result == content

    @pytest.mark.asyncio
    async def test_call_api_no_key(self):
        e = AIEngine()
        e.api_key = ""
        with pytest.raises(ValueError, match="API key not configured"):
            await e._call_api([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_call_api_retry_on_failure(self, engine):
        with patch("app.services.ai_engine.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            # First call fails, second succeeds
            mock_client.post.side_effect = [
                Exception("timeout"),
                _mock_api_response('{"ok": true}'),
            ]
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await engine._call_api([{"role": "user", "content": "hi"}])
            assert result == '{"ok": true}'

    @pytest.mark.asyncio
    async def test_call_api_all_retries_fail(self, engine):
        with patch("app.services.ai_engine.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("always fail")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            with pytest.raises(Exception, match="always fail"):
                await engine._call_api([{"role": "user", "content": "hi"}], max_retries=1)


class TestParseJsonResponse:
    def test_plain_json(self, engine):
        result = engine._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_wrapped(self, engine):
        text = '```json\n{"key": "value"}\n```'
        result = engine._parse_json_response(text)
        assert result == {"key": "value"}

    def test_invalid_json(self, engine):
        with pytest.raises(json.JSONDecodeError):
            engine._parse_json_response("not json")


class TestAnalyzeLogs:
    @pytest.mark.asyncio
    async def test_empty_logs(self, engine):
        result = await engine.analyze_logs([])
        assert result["severity"] == "info"
        assert result["title"] == "无日志数据"

    @pytest.mark.asyncio
    async def test_analyze_logs_success(self, engine):
        ai_response = json.dumps({
            "severity": "warning",
            "title": "High error rate",
            "summary": "Found errors",
            "anomalies": [{"pattern": "OOM", "count": 5, "risk": "high", "suggestion": "add memory"}],
            "overall_assessment": "needs attention",
        })
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_response):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.analyze_logs([{"timestamp": "2026-01-01", "level": "ERROR", "message": "OOM"}])
                assert result["severity"] == "warning"
                assert len(result["anomalies"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_logs_non_json_response(self, engine):
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value="plain text response"):
            result = await engine.analyze_logs([{"timestamp": "t", "level": "ERROR", "message": "err"}])
            assert result["summary"] == "plain text response"

    @pytest.mark.asyncio
    async def test_analyze_logs_api_error(self, engine):
        with patch.object(engine, "_call_api", new_callable=AsyncMock, side_effect=Exception("API down")):
            result = await engine.analyze_logs([{"timestamp": "t", "level": "ERROR", "message": "err"}])
            assert result.get("error") is True

    @pytest.mark.asyncio
    async def test_analyze_logs_with_context(self, engine):
        ai_resp = json.dumps({"severity": "info", "title": "ok", "summary": "ok", "anomalies": [], "overall_assessment": "ok"})
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_resp):
            result = await engine.analyze_logs(
                [{"timestamp": "t", "level": "INFO", "message": "ok"}],
                context="triggered by alert"
            )
            assert result["severity"] == "info"

    @pytest.mark.asyncio
    async def test_analyze_logs_truncates_to_200(self, engine):
        logs = [{"timestamp": "t", "level": "ERROR", "message": f"msg{i}"} for i in range(300)]
        ai_resp = json.dumps({"severity": "info", "title": "ok", "summary": "ok", "anomalies": [], "overall_assessment": "ok"})
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_resp) as mock_call:
            await engine.analyze_logs(logs)
            call_args = mock_call.call_args[0][0]
            # user message should only contain 200 logs worth of text
            assert "msg199" in call_args[1]["content"]


class TestChat:
    @pytest.mark.asyncio
    async def test_chat_success(self, engine):
        ai_resp = json.dumps({"answer": "CPU is high due to process X", "sources": [{"type": "metric", "summary": "cpu 95%"}]})
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_resp):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[])
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.chat("Why is CPU high?")
                assert "CPU" in result["answer"]

    @pytest.mark.asyncio
    async def test_chat_with_context(self, engine):
        ai_resp = json.dumps({"answer": "check logs", "sources": []})
        context = {
            "logs": [{"timestamp": "t", "level": "ERROR", "host_id": 1, "service": "app", "message": "err"}],
            "metrics": [{"host_id": 1, "hostname": "h1", "cpu_percent": 90, "memory_percent": 50, "disk_percent": 30}],
            "alerts": [{"severity": "critical", "title": "CPU", "status": "firing", "fired_at": "t"}],
            "services": [{"name": "api", "type": "http", "target": "http://x", "status": "up"}],
        }
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_resp):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[{"content": "past experience"}])
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.chat("What's wrong?", context)
                assert "memory_context" in result

    @pytest.mark.asyncio
    async def test_chat_non_json_response(self, engine):
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value="just text"):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[])
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.chat("hello")
                assert result["answer"] == "just text"

    @pytest.mark.asyncio
    async def test_chat_api_error(self, engine):
        with patch.object(engine, "_call_api", new_callable=AsyncMock, side_effect=Exception("fail")):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[])
                result = await engine.chat("hello")
                assert result.get("error") is True

    @pytest.mark.asyncio
    async def test_chat_no_context(self, engine):
        ai_resp = json.dumps({"answer": "no data", "sources": []})
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_resp):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[])
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.chat("hello", None)
                assert result["answer"] == "no data"


class TestAnalyzeRootCause:
    @pytest.mark.asyncio
    async def test_root_cause_success(self, engine):
        ai_resp = json.dumps({
            "root_cause": "disk full",
            "confidence": "high",
            "evidence": ["disk 99%"],
            "recommendations": ["clean disk"],
        })
        alert = {"title": "Disk Alert", "severity": "critical", "status": "firing",
                 "message": "disk full", "metric_value": 99, "threshold": 90, "fired_at": "t"}
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_resp):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[])
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.analyze_root_cause(alert, [], [])
                assert result["root_cause"] == "disk full"
                assert result["confidence"] == "high"

    @pytest.mark.asyncio
    async def test_root_cause_with_memories(self, engine):
        ai_resp = json.dumps({"root_cause": "OOM", "confidence": "medium", "evidence": [], "recommendations": []})
        alert = {"title": "Memory Alert", "severity": "warning", "status": "firing",
                 "message": "mem", "metric_value": 95, "threshold": 80, "fired_at": "t"}
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_resp):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[{"content": "last time OOM was from java"}])
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.analyze_root_cause(alert, [], [])
                assert len(result["memory_context"]) == 1

    @pytest.mark.asyncio
    async def test_root_cause_non_json(self, engine):
        alert = {"title": "Test", "severity": "info", "status": "firing",
                 "message": "", "metric_value": None, "threshold": None, "fired_at": ""}
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value="plain analysis"):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[])
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.analyze_root_cause(alert, [], [])
                assert result["root_cause"] == "plain analysis"
                assert result["confidence"] == "low"

    @pytest.mark.asyncio
    async def test_root_cause_api_error(self, engine):
        alert = {"title": "Test", "severity": "info", "status": "firing",
                 "message": "", "metric_value": None, "threshold": None, "fired_at": ""}
        with patch.object(engine, "_call_api", new_callable=AsyncMock, side_effect=Exception("fail")):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[])
                result = await engine.analyze_root_cause(alert, [], [])
                assert result.get("error") is True

    @pytest.mark.asyncio
    async def test_root_cause_with_metrics_and_logs(self, engine):
        ai_resp = json.dumps({"root_cause": "CPU spike", "confidence": "high", "evidence": ["cpu 100%"], "recommendations": ["scale up"]})
        alert = {"title": "CPU", "severity": "critical", "status": "firing",
                 "message": "cpu high", "metric_value": 100, "threshold": 80, "fired_at": "t"}
        metrics = [{"recorded_at": "t", "host_id": 1, "cpu_percent": 100, "memory_percent": 50, "disk_percent": 30}]
        logs = [{"timestamp": "t", "level": "ERROR", "service": "app", "message": "process killed"}]
        with patch.object(engine, "_call_api", new_callable=AsyncMock, return_value=ai_resp):
            with patch("app.services.ai_engine.memory_client") as mock_mem:
                mock_mem.recall = AsyncMock(return_value=[])
                mock_mem.store = AsyncMock(return_value=True)
                result = await engine.analyze_root_cause(alert, metrics, logs)
                assert result["confidence"] == "high"
