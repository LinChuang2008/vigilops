import json
import logging
from typing import List, Dict, Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位资深运维专家和日志分析师。你的任务是分析服务器日志，识别异常模式、潜在风险和安全威胁。

分析要求：
1. 识别异常模式和错误聚类
2. 评估风险等级（info/warning/critical）
3. 提供具体的建议操作
4. 用中文回复

请以 JSON 格式返回分析结果：
{
  "severity": "info|warning|critical",
  "title": "简短的异常标题",
  "summary": "异常摘要描述",
  "anomalies": [
    {
      "pattern": "异常模式描述",
      "count": 出现次数,
      "risk": "风险等级",
      "suggestion": "建议操作"
    }
  ],
  "overall_assessment": "总体评估"
}"""


class AIEngine:
    def __init__(self) -> None:
        self.api_base = settings.ai_api_base
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model
        self.max_tokens = settings.ai_max_tokens

    async def _call_api(self, messages: List[Dict[str, str]], max_retries: int = 2) -> str:
        """Call the AI API with retry logic."""
        if not self.api_key:
            raise ValueError("AI API key not configured. Set AI_API_KEY environment variable.")

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
        }

        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_error = e
                logger.warning("AI API call attempt %d failed: %s", attempt + 1, str(e))
                if attempt < max_retries:
                    continue

        raise last_error  # type: ignore[misc]

    async def analyze_logs(self, logs: List[dict], context: str = "") -> dict:
        """Analyze logs and return anomaly insights."""
        if not logs:
            return {
                "severity": "info",
                "title": "无日志数据",
                "summary": "指定时间范围内没有找到日志数据",
                "anomalies": [],
                "overall_assessment": "无数据可分析",
            }

        # Format logs for the prompt
        log_text_parts = []
        for log in logs[:200]:  # Limit to 200 logs to avoid token overflow
            log_text_parts.append(
                f"[{log.get('timestamp', '')}] [{log.get('level', '')}] "
                f"host={log.get('host_id', '')} service={log.get('service', '')} "
                f"{log.get('message', '')}"
            )
        log_text = "\n".join(log_text_parts)

        user_msg = f"请分析以下 {len(logs)} 条服务器日志，识别异常和风险：\n\n{log_text}"
        if context:
            user_msg += f"\n\n附加上下文：{context}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        try:
            result_text = await self._call_api(messages)
            # Try to parse JSON from the response
            # Strip markdown code fences if present
            cleaned = result_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = lines[1:]  # remove opening fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "severity": "info",
                "title": "AI 分析完成",
                "summary": result_text,
                "anomalies": [],
                "overall_assessment": result_text,
            }
        except Exception as e:
            logger.error("AI log analysis failed: %s", str(e))
            return {
                "severity": "info",
                "title": "分析失败",
                "summary": f"AI 分析过程中出现错误：{str(e)}",
                "anomalies": [],
                "overall_assessment": f"错误：{str(e)}",
                "error": True,
            }

    async def chat(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Natural language query interface (placeholder for next round)."""
        # TODO: Implement full chat with context retrieval in next round
        return "AI 对话功能即将上线，敬请期待。"

    async def analyze_root_cause(
        self, alert: dict, metrics: List[dict], logs: List[dict]
    ) -> dict:
        """Root cause analysis (placeholder for next round)."""
        # TODO: Implement root cause analysis in next round
        return {
            "severity": "info",
            "title": "根因分析功能即将上线",
            "summary": "该功能将在下一轮迭代中实现。",
            "root_cause": None,
            "suggestions": [],
        }


ai_engine = AIEngine()
