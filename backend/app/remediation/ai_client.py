"""
修复模块 AI 客户端。

复用 VigilOps 全局 AI 配置（DeepSeek），增加修复诊断专用 prompt。
支持 mock 模式用于测试。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from .models import Diagnosis, RemediationAlert

logger = logging.getLogger(__name__)

DIAGNOSIS_SYSTEM_PROMPT = """You are VigilOps, an expert SRE diagnostic AI.
Given a monitoring alert and system context, produce a JSON diagnosis.

Your response MUST be valid JSON with these fields:
{
    "root_cause": "concise description of the root cause",
    "confidence": 0.0 to 1.0,
    "suggested_runbook": "runbook_name or null",
    "reasoning": "step by step reasoning"
}

Available runbooks: disk_cleanup, service_restart, zombie_killer, memory_pressure, log_rotation, connection_reset

Be precise. High confidence only when evidence is clear. When uncertain, say so."""


def _build_diagnosis_prompt(alert: RemediationAlert, context: dict[str, Any]) -> str:
    parts = [
        f"ALERT: {alert.summary()}",
        f"Host: {alert.host}",
        f"Type: {alert.alert_type}",
        f"Severity: {alert.severity}",
        f"Labels: {json.dumps(alert.labels)}",
    ]
    if context:
        parts.append(f"Additional context: {json.dumps(context)}")
    return "\n".join(parts)


def _parse_diagnosis_response(text: str) -> Diagnosis:
    """解析 AI 响应为 Diagnosis，处理 markdown 代码块。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines[1:] if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    data = json.loads(cleaned)
    return Diagnosis(
        root_cause=data.get("root_cause", "unknown"),
        confidence=float(data.get("confidence", 0.5)),
        suggested_runbook=data.get("suggested_runbook"),
        reasoning=data.get("reasoning", ""),
    )


class RemediationAIClient:
    """修复诊断 AI 客户端，从 VigilOps 全局配置读取 API 参数。"""

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "",
        model: str = "",
        timeout: float = 30.0,
        mock_responses: Optional[list[Diagnosis]] = None,
    ) -> None:
        self.api_key = api_key or settings.ai_api_key
        self.api_base = (api_base or settings.ai_api_base).rstrip("/")
        self.model = model or settings.ai_model
        self.timeout = timeout
        self._mock_responses = list(mock_responses) if mock_responses else None
        self._mock_index = 0

    @property
    def is_mock(self) -> bool:
        return self._mock_responses is not None

    async def diagnose(
        self, alert: RemediationAlert, context: Optional[dict[str, Any]] = None
    ) -> Diagnosis:
        """诊断告警。支持 mock 模式。"""
        context = context or {}

        if self._mock_responses is not None:
            if self._mock_index < len(self._mock_responses):
                result = self._mock_responses[self._mock_index]
                self._mock_index += 1
                return result
            return Diagnosis(
                root_cause="mock diagnosis",
                confidence=0.8,
                suggested_runbook=None,
                reasoning="mock mode",
            )

        user_prompt = _build_diagnosis_prompt(alert, context)

        try:
            return await self._call_llm(
                system_prompt=DIAGNOSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
            )
        except Exception as e:
            logger.error("AI diagnosis failed: %s", e)
            return Diagnosis(
                root_cause="AI diagnosis unavailable",
                confidence=0.0,
                suggested_runbook=None,
                reasoning=f"AI call failed: {e}",
            )

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> Diagnosis:
        """调用 OpenAI 兼容接口。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": 1024,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return _parse_diagnosis_response(content)
