"""
AI引擎服务 (AI Engine Service)

功能描述 (Description):
    VigilOps 核心 AI 服务模块，提供智能运维分析能力。
    封装与 AI API（兼容 OpenAI 接口）的交互逻辑，支持：
    1. 日志异常分析 (Log Anomaly Analysis) - 识别日志中的异常模式和风险
    2. 自然语言运维问答 (NLP Operations Q&A) - 基于系统数据的智能问答
    3. 告警根因分析 (Alert Root Cause Analysis) - 关联多源数据推断告警根因
    
    集成xiaoqiang-memory记忆系统，利用历史运维经验增强分析准确性。

主要组件 (Main Components):
    - AIEngine类：统一的AI分析能力入口
    - 三套专业化的系统提示词 (System Prompts)：针对不同分析场景优化
    - 记忆增强机制：基于历史经验的上下文召回
    
技术特性 (Technical Features):
    - 支持自动重试和错误恢复
    - JSON响应解析和容错处理
    - 异步记忆存储，不阻塞主流程
    - Token限制处理，避免超长输入
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

import httpx

from app.core.config import settings
from app.services.memory_client import memory_client

logger = logging.getLogger(__name__)

# 日志异常分析系统提示词 (Log Analysis System Prompt)
# Prompt工程核心1：专注于日志模式识别和风险评估，结构化输出便于后续处理
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

# 运维问答系统提示词 (Chat System Prompt)
# Prompt工程核心2：基于多源数据的上下文问答，强调数据溯源和具体建议
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

# 告警根因分析系统提示词 (Root Cause Analysis System Prompt)
# Prompt工程核心3：多维数据关联分析，强调证据链和置信度评估
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
    """
    AI引擎核心类 (AI Engine Core Class)
    
    功能描述 (Description):
        VigilOps AI服务的统一入口，封装所有AI分析能力。
        支持三种核心分析场景：日志异常分析、运维问答、告警根因分析。
    
    主要特性 (Features):
        - 统一的AI API调用封装，支持OpenAI兼容接口
        - 集成运维记忆系统，利用历史经验增强分析
        - 结构化响应解析，容错处理
        - 异步记忆存储，不阻塞主业务流程
    
    使用场景 (Use Cases):
        1. 日志监控系统调用analyze_logs进行异常检测
        2. 用户通过聊天界面调用chat进行运维咨询
        3. 告警系统调用analyze_root_cause进行根因分析
    """

    def __init__(self) -> None:
        """
        初始化AI引擎 (Initialize AI Engine)
        
        功能描述:
            从系统配置中读取AI API连接参数，初始化引擎实例。
            
        配置参数 (Configuration Parameters):
            - api_base: AI API服务的基础URL（支持OpenAI兼容接口）
            - api_key: API认证密钥
            - model: 使用的AI模型名称
            - max_tokens: 单次调用的最大token限制
        """
        # 从全局配置读取AI服务连接参数
        self.api_base = settings.ai_api_base  # AI API基础URL
        self.api_key = settings.ai_api_key    # API密钥
        self.model = settings.ai_model        # AI模型名称
        self.max_tokens = settings.ai_max_tokens  # Token限制

    async def _call_api(self, messages: List[Dict[str, str]], max_retries: int = 2) -> str:
        """
        AI API调用核心方法 (Core AI API Call Method)
        
        功能描述:
            封装对AI API的HTTP调用，支持OpenAI兼容接口格式。
            实现自动重试机制，提高调用成功率。
            
        Args:
            messages: OpenAI格式的消息列表，包含system和user角色
            max_retries: 最大重试次数，默认2次
            
        Returns:
            AI返回的文本内容字符串
            
        Raises:
            ValueError: API Key未配置时抛出
            Exception: 所有重试失败后抛出最后一次异常
            
        调用流程:
            1. 验证API Key配置
            2. 构建OpenAI兼容的请求payload
            3. 执行HTTP POST调用
            4. 解析响应并返回content字段
            5. 失败时自动重试
        """
        # 1. 检查API Key配置
        if not self.api_key:
            raise ValueError("AI API key not configured. Set AI_API_KEY environment variable.")

        # 2. 构建OpenAI兼容的API请求
        url = f"{self.api_base}/chat/completions"  # 标准的OpenAI chat endpoint
        headers = {
            "Authorization": f"Bearer {self.api_key}",  # Bearer token认证
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,                    # 使用配置的模型
            "messages": messages,                   # 对话消息列表
            "max_tokens": self.max_tokens,          # Token限制
            "temperature": 0.3,                     # 低温度确保输出稳定性
        }

        # 3. 实现重试机制的API调用循环
        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                # 使用异步HTTP客户端发送请求，30秒超时
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()  # 检查HTTP状态码
                    data = response.json()
                    # 解析OpenAI标准响应格式，返回AI生成的内容
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_error = e
                logger.warning("AI API call attempt %d failed: %s", attempt + 1, str(e))
                if attempt < max_retries:
                    continue  # 继续重试

        # 所有重试都失败，抛出最后一次的异常
        raise last_error  # type: ignore[misc]

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        AI响应JSON解析器 (AI Response JSON Parser)
        
        功能描述:
            解析AI返回的JSON内容，自动处理Markdown代码块包装。
            AI模型经常会用```json```包装JSON响应，此方法自动清理。
            
        Args:
            text: AI返回的原始文本内容
            
        Returns:
            解析后的Python字典对象
            
        Raises:
            json.JSONDecodeError: JSON格式无效时抛出
            
        处理逻辑:
            1. 去除文本首尾空白
            2. 检测并移除Markdown代码块标记（```json ... ```）
            3. 解析清理后的JSON文本
        """
        # 1. 基础文本清理
        cleaned = text.strip()
        
        # 2. 处理Markdown代码块包装（AI常见的输出格式）
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]  # 去掉开头的 ```json 或 ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # 去掉结尾的 ```
            cleaned = "\n".join(lines)
            
        # 3. 解析为Python字典对象
        return json.loads(cleaned)

    async def analyze_logs(self, logs: List[dict], context: str = "") -> dict:
        """
        日志异常分析方法 (Log Anomaly Analysis Method)
        
        功能描述:
            AI驱动的日志异常检测，识别错误模式、安全威胁和性能问题。
            使用专业化的系统提示词进行日志模式识别。
            
        Args:
            logs: 日志条目列表，包含timestamp、level、host_id、service、message等字段
            context: 附加上下文信息，如告警触发原因、用户查询意图等
            
        Returns:
            dict: 结构化分析结果，包含以下字段：
                - severity: 风险等级 (info/warning/critical)
                - title: 异常标题摘要
                - summary: 详细异常描述
                - anomalies: 异常模式列表，每项包含pattern、count、risk、suggestion
                - overall_assessment: 总体评估结论
                - error: 可选，分析失败时为True
                
        异常处理:
            - 空日志数据：返回info级别的无数据提示
            - JSON解析失败：将AI原文作为summary返回
            - API调用失败：返回错误信息和error标记
            
        性能优化:
            - Token限制：最多处理200条日志避免超长输入
            - 异步存储：异常发现时后台存储到记忆系统
            - 容错设计：解析失败时仍返回可用结果
        """
        # 1. 边界条件处理：无日志数据
        if not logs:
            return {
                "severity": "info",
                "title": "无日志数据",
                "summary": "指定时间范围内没有找到日志数据",
                "anomalies": [],
                "overall_assessment": "无数据可分析",
            }

        # 2. 日志文本预处理：格式化并限制数量（Token管理）
        log_text_parts = []
        for log in logs[:200]:  # 最多200条，避免超出AI API的token限制
            # 统一日志格式：时间戳、级别、主机、服务、消息
            log_text_parts.append(
                f"[{log.get('timestamp', '')}] [{log.get('level', '')}] "
                f"host={log.get('host_id', '')} service={log.get('service', '')} "
                f"{log.get('message', '')}"
            )
        log_text = "\n".join(log_text_parts)

        # 3. 构建AI分析请求消息
        user_msg = f"请分析以下 {len(logs)} 条服务器日志，识别异常和风险：\n\n{log_text}"
        if context:
            user_msg += f"\n\n附加上下文：{context}"  # 用户提供的分析上下文

        # 4. 使用日志分析专用的系统提示词
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},  # 专业日志分析师角色设定
            {"role": "user", "content": user_msg},
        ]

        try:
            # 5. 调用AI API进行日志分析
            result_text = await self._call_api(messages)
            result = self._parse_json_response(result_text)  # 解析结构化响应

            # 6. 智能记忆存储：仅当发现真正异常时才存储（降噪）
            if result.get("severity", "info") != "info":
                title = result.get("title", "未知异常")
                summary = result.get("summary", "")
                store_content = f"日志异常发现: {title}\n摘要: {summary}"
                # 异步存储，不阻塞主流程
                asyncio.create_task(
                    memory_client.store(store_content, source="vigilops-log-analysis")
                )

            return result
            
        except json.JSONDecodeError:
            # 7. 容错处理：AI返回非JSON格式时的降级方案
            return {
                "severity": "info",
                "title": "AI 分析完成",
                "summary": result_text,  # 直接使用AI的原始输出
                "anomalies": [],
                "overall_assessment": result_text,
            }
        except Exception as e:
            # 8. 异常处理：API调用失败时的错误响应
            logger.error("AI log analysis failed: %s", str(e))
            return {
                "severity": "info",
                "title": "分析失败",
                "summary": f"AI 分析过程中出现错误：{str(e)}",
                "anomalies": [],
                "overall_assessment": f"错误：{str(e)}",
                "error": True,  # 标记为错误状态
            }

    async def chat(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        智能运维问答接口 (Intelligent Operations Q&A Interface)
        
        功能描述:
            基于多源系统数据和历史运维经验的自然语言问答系统。
            整合实时监控数据、日志信息、告警状态等，提供上下文相关的运维建议。
            
        Args:
            question: 用户的自然语言问题，如"为什么CPU使用率这么高？"
            context: 系统上下文数据字典，可包含以下字段：
                - logs: 最近的错误/警告日志列表
                - metrics: 主机性能指标数据
                - alerts: 当前活跃告警列表
                - services: 服务健康状态列表
                
        Returns:
            Dict[str, Any]: 智能问答结果，包含：
                - answer: AI生成的中文回答内容
                - sources: 数据来源列表，每项包含type和summary
                - memory_context: 从记忆系统召回的相关历史经验
                - error: 可选，处理失败时为True
                
        核心特性:
            1. 多源数据整合：自动组装日志、指标、告警、服务状态
            2. 记忆增强：基于问题内容召回相关历史运维经验
            3. 上下文感知：基于当前系统状态提供针对性建议
            4. 异步记忆：问答记录自动存储供未来参考
        """
        # 1. 多源系统数据整合 (Multi-source System Data Integration)
        context_parts: List[str] = []

        if context:
            # 1.1 组装日志上下文：最近的错误和警告日志
            if context.get("logs"):
                log_lines = []
                for log in context["logs"][:50]:  # 限制50条避免过长
                    log_lines.append(
                        f"  [{log.get('timestamp', '')}] [{log.get('level', '')}] "
                        f"host={log.get('host_id', '')} service={log.get('service', '')} "
                        f"{log.get('message', '')}"
                    )
                context_parts.append(f"【最近日志（ERROR/WARN）】\n" + "\n".join(log_lines))

            # 1.2 组装性能指标上下文：主机资源使用情况
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

            # 1.3 组装告警上下文：当前活跃的告警信息
            if context.get("alerts"):
                alert_lines = []
                for a in context["alerts"]:
                    alert_lines.append(
                        f"  [{a.get('severity', '')}] {a.get('title', '')} "
                        f"(状态: {a.get('status', '')}, 触发: {a.get('fired_at', '')})"
                    )
                context_parts.append(f"【活跃告警】\n" + "\n".join(alert_lines))

            # 1.4 组装服务状态上下文：各服务的健康状况
            if context.get("services"):
                svc_lines = []
                for s in context["services"]:
                    svc_lines.append(
                        f"  {s.get('name', '?')}: {s.get('status', 'unknown')} "
                        f"(类型: {s.get('type', '?')}, 目标: {s.get('target', '?')})"
                    )
                context_parts.append(f"【服务健康状态】\n" + "\n".join(svc_lines))

        # 1.5 整合所有上下文数据为统一文本
        context_text = "\n\n".join(context_parts) if context_parts else "当前没有可用的系统数据。"

        # 2. 运维记忆召回 (Operations Memory Recall)
        # 基于用户问题从xiaoqiang-memory系统召回相关历史经验
        memories = await memory_client.recall(question)
        memory_context: List[Dict[str, Any]] = []
        memory_prompt = ""
        if memories:
            memory_context = memories  # 保存原始记忆数据供前端展示
            memory_lines = []
            # 格式化历史经验为可读文本，最多5条避免prompt过长
            for i, mem in enumerate(memories[:5], 1):
                # 兼容不同的记忆数据结构
                content = mem.get("content", mem.get("text", str(mem)))
                memory_lines.append(f"{i}. {content}")
            # 构建记忆增强的系统提示词扩展
            memory_prompt = (
                "\n\n【历史运维经验（来自记忆系统）】\n"
                + "\n".join(memory_lines)
                + "\n请参考以上历史经验回答问题。"
            )

        # 3. 构建AI问答请求 (Build AI Q&A Request)
        user_msg = f"系统上下文数据：\n{context_text}\n\n用户问题：{question}"
        
        # 动态扩展系统提示词：基础问答prompt + 记忆增强prompt
        system_prompt = CHAT_SYSTEM_PROMPT + memory_prompt

        messages = [
            {"role": "system", "content": system_prompt},  # 运维助手角色 + 历史经验
            {"role": "user", "content": user_msg},         # 用户问题 + 系统上下文
        ]

        try:
            # 4. 调用AI进行智能问答
            result_text = await self._call_api(messages)
            
            # 4.1 解析结构化响应（JSON格式）
            try:
                result = self._parse_json_response(result_text)
            except json.JSONDecodeError:
                # 降级处理：AI返回非JSON时包装为标准格式
                result = {"answer": result_text, "sources": []}

            # 5. 异步记忆存储：将问答记录存储供未来参考
            answer = result.get("answer", "")
            store_content = f"用户问题: {question}\nAI 回答: {answer[:500]}"  # 限制长度避免存储过大
            # 后台异步存储，不阻塞用户响应
            asyncio.create_task(
                memory_client.store(store_content, source="vigilops-chat")
            )

            # 6. 附加记忆上下文供前端展示
            result["memory_context"] = memory_context
            return result
            
        except Exception as e:
            # 7. 异常处理：API调用失败的降级响应
            logger.error("AI chat failed: %s", str(e))
            return {
                "answer": f"AI 对话出错：{str(e)}", 
                "sources": [], 
                "error": True, 
                "memory_context": []
            }

    async def analyze_root_cause(
        self, alert: dict, metrics: List[dict], logs: List[dict]
    ) -> Dict[str, Any]:
        """
        告警根因分析引擎 (Alert Root Cause Analysis Engine)
        
        功能描述:
            基于告警信息、系统指标和日志数据的多维关联分析，
            利用AI推断告警的根本原因并提供修复建议。
            结合历史类似告警经验，提高分析准确性。
            
        Args:
            alert: 告警详情字典，包含title、severity、message、metric_value等字段
            metrics: 相关时段的主机指标列表，用于分析性能趋势
            logs: 相关时段的日志列表，用于查找错误关联
            
        Returns:
            Dict[str, Any]: 根因分析结果，包含：
                - root_cause: 推断的根本原因描述
                - confidence: 分析置信度 (high/medium/low)
                - evidence: 支持该结论的证据列表
                - recommendations: 具体的修复建议列表
                - memory_context: 相关的历史告警处理经验
                - error: 可选，分析失败时为True
                
        分析方法:
            1. 告警信息解构：提取关键告警属性
            2. 指标趋势分析：查找性能异常模式
            3. 日志错误关联：识别相关错误和异常
            4. 历史经验召回：匹配类似告警的处理经验
            5. 多维数据融合：综合分析得出根因结论
            6. 置信度评估：基于证据质量给出可信度
        """
        # 1. 告警信息解构 (Alert Information Decomposition)
        # 将告警对象转换为结构化的分析文本
        alert_text = (
            f"告警标题: {alert.get('title', '')}\n"
            f"严重级别: {alert.get('severity', '')}\n"
            f"状态: {alert.get('status', '')}\n"
            f"告警消息: {alert.get('message', '')}\n"
            f"指标值: {alert.get('metric_value', 'N/A')}\n"
            f"阈值: {alert.get('threshold', 'N/A')}\n"
            f"触发时间: {alert.get('fired_at', '')}"
        )

        # 2. 性能指标趋势构建 (Performance Metrics Trend Building)
        # 组装告警前后时段的主机性能数据，用于趋势分析
        metric_lines = []
        for m in metrics[:30]:  # 限制30条避免上下文过长
            metric_lines.append(
                f"  [{m.get('recorded_at', '')}] host={m.get('host_id', '')} "
                f"CPU={m.get('cpu_percent', 'N/A')}% 内存={m.get('memory_percent', 'N/A')}% "
                f"磁盘={m.get('disk_percent', 'N/A')}%"
            )
        metrics_text = "\n".join(metric_lines) if metric_lines else "无相关指标数据"

        # 3. 错误日志关联 (Error Log Correlation)
        # 组装告警时段的日志数据，寻找错误和异常模式
        log_lines = []
        for log in logs[:50]:  # 限制50条，优先关注ERROR和WARN级别
            log_lines.append(
                f"  [{log.get('timestamp', '')}] [{log.get('level', '')}] "
                f"service={log.get('service', '')} {log.get('message', '')}"
            )
        logs_text = "\n".join(log_lines) if log_lines else "无相关日志数据"

        # 4. 历史经验召回 (Historical Experience Recall)
        # 基于告警标题从记忆系统召回类似告警的处理经验
        alert_title = alert.get("title", "")
        memories = await memory_client.recall(alert_title)
        memory_context: List[Dict[str, Any]] = []
        memory_prompt = ""
        if memories:
            memory_context = memories  # 保存完整记忆数据供前端展示
            memory_lines = []
            # 格式化历史告警处理经验，最多5条
            for i, mem in enumerate(memories[:5], 1):
                content = mem.get("content", mem.get("text", str(mem)))
                memory_lines.append(f"{i}. {content}")
            # 扩展系统提示词，加入历史经验指导
            memory_prompt = (
                "\n\n【历史类似告警处理经验】\n"
                + "\n".join(memory_lines)
                + "\n请参考以上历史经验进行分析。"
            )

        # 5. 构建多维分析请求 (Build Multi-dimensional Analysis Request)
        user_msg = (
            f"请分析以下告警的根因：\n\n"
            f"【告警信息】\n{alert_text}\n\n"
            f"【相关时段指标】\n{metrics_text}\n\n"
            f"【相关时段日志】\n{logs_text}"
        )

        # 组合根因分析专用prompt和历史经验
        system_prompt = ROOT_CAUSE_SYSTEM_PROMPT + memory_prompt

        messages = [
            {"role": "system", "content": system_prompt},  # 根因分析专家角色 + 历史经验
            {"role": "user", "content": user_msg},         # 多维数据输入
        ]

        try:
            # 6. 执行AI根因分析 (Execute AI Root Cause Analysis)
            result_text = await self._call_api(messages)
            
            # 6.1 解析结构化分析结果
            try:
                result = self._parse_json_response(result_text)
            except json.JSONDecodeError:
                # 降级处理：AI返回非JSON时包装为标准格式
                result = {
                    "root_cause": result_text,
                    "confidence": "low",  # 非结构化响应降低置信度
                    "evidence": [],
                    "recommendations": [],
                }

            # 7. 根因分析结果的智能记忆存储 (Intelligent Memory Storage)
            root_cause = result.get("root_cause", "")
            recommendations = result.get("recommendations", [])
            # 构建结构化的经验记录，便于未来召回
            store_content = (
                f"告警: {alert_title}\n"
                f"根因: {root_cause}\n"
                f"建议: {'; '.join(recommendations[:3]) if recommendations else '无'}"
            )
            # 异步存储到记忆系统，标记为根因分析来源
            asyncio.create_task(
                memory_client.store(store_content, source="vigilops-root-cause")
            )

            # 8. 附加记忆上下文供前端展示历史经验
            result["memory_context"] = memory_context
            return result
            
        except Exception as e:
            # 9. 异常处理：根因分析失败的降级响应
            logger.error("AI root cause analysis failed: %s", str(e))
            return {
                "root_cause": f"根因分析出错：{str(e)}",
                "confidence": "low",
                "evidence": [],
                "recommendations": [],
                "error": True,
                "memory_context": [],
            }


# 模块级单例实例 (Module-level Singleton Instance)
# 创建全局AI引擎实例，供其他模块直接导入使用
# 使用单例模式确保应用内共享同一个AI引擎实例，避免重复初始化
ai_engine = AIEngine()
