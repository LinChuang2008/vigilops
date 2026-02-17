"""
AI 引擎服务模块。

封装与 AI API（兼容 OpenAI 接口）的交互逻辑，提供日志异常分析、
自然语言运维问答、告警根因分析等核心 AI 能力。
集成运维记忆系统，利用历史经验增强分析能力。
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

import httpx

from app.core.config import settings
from app.services.memory_client import memory_client

logger = logging.getLogger(__name__)

# 日志异常分析的系统提示词
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

# 运维问答的系统提示词
CHAT_SYSTEM_PROMPT = """你是 VigilOps AI 运维助手，基于以下系统数据回答运维问题。用中文回答，简洁明了。

回答要求：
1. 基于提供的系统数据进行分析和回答
2. 如果数据不足以回答，明确说明
3. 给出具体的建议和操作步骤
4. 保持简洁，重点突出

请以 JSON 格式返回：
{
  "answer": "你的回答内容",
  "sources": [
    {"type": "log/metric/alert/service", "summary": "数据来源摘要"}
  ]
}"""

# 告警根因分析的系统提示词
ROOT_CAUSE_SYSTEM_PROMPT = """你是 VigilOps AI 运维专家，擅长告警根因分析。基于提供的告警信息、系统指标和日志，分析告警的可能根因。

分析要求：
1. 关联指标异常和日志错误，找出根本原因
2. 评估置信度
3. 列出支持证据
4. 给出排查和修复建议

请以 JSON 格式返回：
{
  "root_cause": "根因描述",
  "confidence": "high/medium/low",
  "evidence": ["证据1", "证据2"],
  "recommendations": ["建议1", "建议2"]
}"""


class AIEngine:
    """AI 引擎类，封装所有 AI 分析能力的统一入口。"""

    def __init__(self) -> None:
        """根据配置初始化 API 连接参数。"""
        self.api_base = settings.ai_api_base
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model
        self.max_tokens = settings.ai_max_tokens

    async def _call_api(self, messages: List[Dict[str, str]], max_retries: int = 2) -> str:
        """调用 AI API，支持自动重试。

        Args:
            messages: OpenAI 格式的消息列表
            max_retries: 最大重试次数

        Returns:
            AI 返回的文本内容

        Raises:
            ValueError: API Key 未配置时抛出
            Exception: 所有重试失败后抛出最后一次异常
        """
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

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """解析 AI 返回的 JSON 内容，自动去除 Markdown 代码块标记。"""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]  # 去掉开头的 ```json
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # 去掉结尾的 ```
            cleaned = "\n".join(lines)
        return json.loads(cleaned)

    async def analyze_logs(self, logs: List[dict], context: str = "") -> dict:
        """分析日志数据，识别异常模式和潜在风险。

        Args:
            logs: 日志条目列表
            context: 附加上下文信息

        Returns:
            包含 severity、title、anomalies 等字段的分析结果
        """
        if not logs:
            return {
                "severity": "info",
                "title": "无日志数据",
                "summary": "指定时间范围内没有找到日志数据",
                "anomalies": [],
                "overall_assessment": "无数据可分析",
            }

        # 拼接日志文本，最多取 200 条避免超出 token 限制
        log_text_parts = []
        for log in logs[:200]:
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
            result = self._parse_json_response(result_text)

            # 如果发现异常（severity 不是 info），异步存储到记忆系统
            if result.get("severity", "info") != "info":
                title = result.get("title", "未知异常")
                summary = result.get("summary", "")
                store_content = f"日志异常发现: {title}\n摘要: {summary}"
                asyncio.create_task(memory_client.store(store_content, source="vigilops-log-analysis"))

            return result
        except json.JSONDecodeError:
            # AI 返回的不是有效 JSON，将原文作为摘要返回
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

    async def chat(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """自然语言运维问答接口，结合系统上下文数据回答用户问题。

        Args:
            question: 用户的自然语言问题
            context: 系统上下文数据（日志、指标、告警、服务状态等）

        Returns:
            包含 answer 和 sources 字段的回答结果
        """
        context_parts: List[str] = []

        if context:
            # 组装最近错误/警告日志
            if context.get("logs"):
                log_lines = []
                for log in context["logs"][:50]:
                    log_lines.append(
                        f"  [{log.get('timestamp', '')}] [{log.get('level', '')}] "
                        f"host={log.get('host_id', '')} service={log.get('service', '')} "
                        f"{log.get('message', '')}"
                    )
                context_parts.append(f"【最近日志（ERROR/WARN）】\n" + "\n".join(log_lines))

            # 组装主机指标摘要
            if context.get("metrics"):
                metric_lines = []
                for m in context["metrics"]:
                    metric_lines.append(
                        f"  主机{m.get('host_id', '?')}({m.get('hostname', '?')}): "
                        f"CPU={m.get('cpu_percent', 'N/A')}%, "
                        f"内存={m.get('memory_percent', 'N/A')}%, "
                        f"磁盘={m.get('disk_percent', 'N/A')}%"
                    )
                context_parts.append(f"【主机指标摘要】\n" + "\n".join(metric_lines))

            # 组装活跃告警信息
            if context.get("alerts"):
                alert_lines = []
                for a in context["alerts"]:
                    alert_lines.append(
                        f"  [{a.get('severity', '')}] {a.get('title', '')} "
                        f"(状态: {a.get('status', '')}, 触发: {a.get('fired_at', '')})"
                    )
                context_parts.append(f"【活跃告警】\n" + "\n".join(alert_lines))

            # 组装服务健康状态
            if context.get("services"):
                svc_lines = []
                for s in context["services"]:
                    svc_lines.append(
                        f"  {s.get('name', '?')}: {s.get('status', 'unknown')} "
                        f"(类型: {s.get('type', '?')}, 目标: {s.get('target', '?')})"
                    )
                context_parts.append(f"【服务健康状态】\n" + "\n".join(svc_lines))

        context_text = "\n\n".join(context_parts) if context_parts else "当前没有可用的系统数据。"

        # 召回相关运维记忆
        memories = await memory_client.recall(question)
        memory_context: List[Dict[str, Any]] = []
        memory_prompt = ""
        if memories:
            memory_context = memories
            memory_lines = []
            for i, mem in enumerate(memories[:5], 1):
                content = mem.get("content", mem.get("text", str(mem)))
                memory_lines.append(f"{i}. {content}")
            memory_prompt = (
                "\n\n【历史运维经验（来自记忆系统）】\n"
                + "\n".join(memory_lines)
                + "\n请参考以上历史经验回答问题。"
            )

        user_msg = f"系统上下文数据：\n{context_text}\n\n用户问题：{question}"

        system_prompt = CHAT_SYSTEM_PROMPT + memory_prompt

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]

        try:
            result_text = await self._call_api(messages)
            try:
                result = self._parse_json_response(result_text)
            except json.JSONDecodeError:
                result = {"answer": result_text, "sources": []}

            # 异步存储问答记录到记忆系统（不阻塞响应）
            answer = result.get("answer", "")
            store_content = f"用户问题: {question}\nAI 回答: {answer[:500]}"
            asyncio.create_task(memory_client.store(store_content, source="vigilops-chat"))

            # 附加记忆上下文信息
            result["memory_context"] = memory_context
            return result
        except Exception as e:
            logger.error("AI chat failed: %s", str(e))
            return {"answer": f"AI 对话出错：{str(e)}", "sources": [], "error": True, "memory_context": []}

    async def analyze_root_cause(
        self, alert: dict, metrics: List[dict], logs: List[dict]
    ) -> Dict[str, Any]:
        """告警根因分析，关联告警、指标和日志数据推断根本原因。

        Args:
            alert: 告警详情字典
            metrics: 相关时段的主机指标列表
            logs: 相关时段的日志列表

        Returns:
            包含 root_cause、confidence、evidence、recommendations 的分析结果
        """
        # 构建告警信息文本
        alert_text = (
            f"告警标题: {alert.get('title', '')}\n"
            f"严重级别: {alert.get('severity', '')}\n"
            f"状态: {alert.get('status', '')}\n"
            f"告警消息: {alert.get('message', '')}\n"
            f"指标值: {alert.get('metric_value', 'N/A')}\n"
            f"阈值: {alert.get('threshold', 'N/A')}\n"
            f"触发时间: {alert.get('fired_at', '')}"
        )

        # 构建指标上下文，最多取 30 条
        metric_lines = []
        for m in metrics[:30]:
            metric_lines.append(
                f"  [{m.get('recorded_at', '')}] host={m.get('host_id', '')} "
                f"CPU={m.get('cpu_percent', 'N/A')}% 内存={m.get('memory_percent', 'N/A')}% "
                f"磁盘={m.get('disk_percent', 'N/A')}%"
            )
        metrics_text = "\n".join(metric_lines) if metric_lines else "无相关指标数据"

        # 构建日志上下文，最多取 50 条
        log_lines = []
        for log in logs[:50]:
            log_lines.append(
                f"  [{log.get('timestamp', '')}] [{log.get('level', '')}] "
                f"service={log.get('service', '')} {log.get('message', '')}"
            )
        logs_text = "\n".join(log_lines) if log_lines else "无相关日志数据"

        # 召回相关告警历史经验
        alert_title = alert.get("title", "")
        memories = await memory_client.recall(alert_title)
        memory_context: List[Dict[str, Any]] = []
        memory_prompt = ""
        if memories:
            memory_context = memories
            memory_lines = []
            for i, mem in enumerate(memories[:5], 1):
                content = mem.get("content", mem.get("text", str(mem)))
                memory_lines.append(f"{i}. {content}")
            memory_prompt = (
                "\n\n【历史类似告警处理经验】\n"
                + "\n".join(memory_lines)
                + "\n请参考以上历史经验进行分析。"
            )

        user_msg = (
            f"请分析以下告警的根因：\n\n"
            f"【告警信息】\n{alert_text}\n\n"
            f"【相关时段指标】\n{metrics_text}\n\n"
            f"【相关时段日志】\n{logs_text}"
        )

        system_prompt = ROOT_CAUSE_SYSTEM_PROMPT + memory_prompt

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]

        try:
            result_text = await self._call_api(messages)
            try:
                result = self._parse_json_response(result_text)
            except json.JSONDecodeError:
                result = {
                    "root_cause": result_text,
                    "confidence": "low",
                    "evidence": [],
                    "recommendations": [],
                }

            # 异步存储根因分析结果到记忆系统
            root_cause = result.get("root_cause", "")
            recommendations = result.get("recommendations", [])
            store_content = (
                f"告警: {alert_title}\n"
                f"根因: {root_cause}\n"
                f"建议: {'; '.join(recommendations[:3]) if recommendations else '无'}"
            )
            asyncio.create_task(memory_client.store(store_content, source="vigilops-root-cause"))

            result["memory_context"] = memory_context
            return result
        except Exception as e:
            logger.error("AI root cause analysis failed: %s", str(e))
            return {
                "root_cause": f"根因分析出错：{str(e)}",
                "confidence": "low",
                "evidence": [],
                "recommendations": [],
                "error": True,
                "memory_context": [],
            }


# 模块级单例，供其他模块直接导入使用
ai_engine = AIEngine()
