"""
运维记忆系统客户端 (Operations Memory System Client)

功能描述 (Description):
    VigilOps与Engram系统的集成客户端，实现运维经验的持久化存储和智能召回。
    为AI引擎提供历史经验支持，增强分析准确性和决策质量。
    
核心功能 (Core Features):
    1. 记忆存储 (Memory Storage) - 将运维经验、处理结果存储到记忆系统
    2. 记忆召回 (Memory Recall) - 基于关键词搜索相关历史经验
    3. 容错设计 (Fault Tolerance) - 记忆系统异常不影响主业务流程
    4. 配置控制 (Configuration Control) - 支持动态启用/禁用记忆功能
    
集成场景 (Integration Scenarios):
    - AI日志分析：召回类似日志模式的历史处理经验
    - 告警根因分析：基于告警标题查找相关处理记录
    - 运维问答：结合历史经验提供更准确的回答
    - 自动修复：存储修复成功/失败的经验供后续参考
    
技术特性 (Technical Features):
    - 异步HTTP客户端：支持高并发访问
    - 超时控制：避免记忆系统响应慢影响主流程
    - 静默失败：API异常时静默降级，不中断业务
    - 单例模式：全局共享客户端实例，减少连接开销
"""
import httpx
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryClient:
    """
    运维记忆系统客户端类 (Operations Memory System Client Class)
    
    功能描述:
        封装与Engram系统的HTTP API交互，提供统一的记忆操作接口。
        设计为轻量级客户端，专注于数据传输和错误处理。
        
    主要方法:
        - recall(): 记忆召回，基于关键词搜索相关经验
        - store(): 记忆存储，保存新的运维经验
        
    设计原则:
        1. 非阻塞：记忆操作异常不影响主业务流程
        2. 可配置：支持动态启用/禁用记忆功能
        3. 容错性：网络异常时优雅降级
        4. 高性能：短超时避免长时间等待
    """

    @property
    def _base_url(self) -> str:
        """
        记忆系统API基地址获取器 (Memory System API Base URL Getter)
        
        功能描述:
            从全局配置获取Engram系统的API基础URL。
            支持运行时配置更新。
            
        Returns:
            str: 记忆系统API的基础URL，如 http://localhost:8002/api/v1/memory
        """
        return settings.memory_api_url

    @property
    def _enabled(self) -> bool:
        """
        记忆功能启用状态检查器 (Memory Feature Enable Status Checker)
        
        功能描述:
            检查记忆功能是否在全局配置中启用。
            用于在记忆系统不可用时快速跳过相关操作。
            
        Returns:
            bool: True表示记忆功能启用，False表示禁用
        """
        return settings.memory_enabled

    async def recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        记忆召回接口 (Memory Recall Interface)
        
        功能描述:
            基于语义搜索从记忆系统召回与查询相关的历史运维经验。
            支持自然语言查询，返回最相关的经验记录供AI参考。
            
        Args:
            query: 搜索查询文本，支持自然语言描述（如"CPU使用率过高"）
            top_k: 返回最相关的记忆条数，默认5条，避免上下文过长
            
        Returns:
            List[Dict[str, Any]]: 相关记忆列表，每项包含content、importance、timestamp等字段
                                  失败时返回空列表，确保业务流程不中断
                                  
        使用场景:
            - AI日志分析前召回类似问题的处理经验
            - 告警根因分析时查找相关告警的历史处理记录  
            - 运维问答时提供历史经验作为回答依据
            
        容错机制:
            - 功能禁用时直接返回空列表
            - 网络异常时静默失败，记录debug日志
            - API响应格式兼容处理
        """
        # 1. 功能开关检查 (Feature Switch Check)
        if not self._enabled:
            return []  # 记忆功能禁用时直接返回空列表
            
        try:
            # 2. HTTP API调用 (HTTP API Call)
            async with httpx.AsyncClient(timeout=5.0) as client:  # 5秒超时，避免阻塞主流程
                resp = await client.post(
                    f"{self._base_url}/recall",  # 记忆召回端点
                    json={"query": query, "top_k": top_k},  # 查询参数
                )
                resp.raise_for_status()  # 检查HTTP状态码
                data = resp.json()
                
                # 3. 响应格式兼容处理 (Response Format Compatibility)
                # 适配不同版本的Engram API返回格式
                if isinstance(data, list):
                    return data  # 直接返回列表格式
                # 尝试从嵌套对象中提取记忆列表
                return data.get("memories", data.get("results", []))
                
        except Exception as e:
            # 4. 异常静默处理 (Silent Exception Handling)
            # 记忆系统异常不应该影响主业务，只记录debug级别日志
            logger.debug("记忆召回失败（不影响主流程）: %s", str(e))
            return []  # 静默返回空列表

    async def store(self, content: str, source: str = "vigilops") -> bool:
        """
        记忆存储接口 (Memory Storage Interface)
        
        功能描述:
            将运维经验、分析结果、处理记录存储到记忆系统中。
            构建组织的运维知识库，为后续的AI分析提供历史经验支持。
            
        Args:
            content: 要存储的文本内容，如"告警: CPU使用率过高\n根因: 进程泄漏\n解决: 重启服务"
            source: 来源标识，用于数据溯源和分类（默认"vigilops"）
            
        Returns:
            bool: 存储是否成功
                  - True: 成功存储到记忆系统
                  - False: 存储失败或功能禁用，但不影响主业务
                  
        存储内容类型:
            - AI日志分析结果：异常发现和处理建议
            - 告警根因分析：告警标题、根因、解决方案
            - 运维问答记录：用户问题和AI回答
            - 自动修复结果：修复成功/失败的经验记录
            
        设计考虑:
            - 异步存储：不阻塞主业务流程
            - 静默失败：存储异常不影响用户体验  
            - 来源标识：便于数据分类和溯源管理
            - 短超时：避免记忆系统响应慢影响性能
        """
        # 1. 功能开关检查 (Feature Switch Check)
        if not self._enabled:
            return False  # 记忆功能禁用时直接返回失败
            
        try:
            # 2. HTTP API调用 (HTTP API Call)
            async with httpx.AsyncClient(timeout=5.0) as client:  # 5秒超时，避免阻塞
                resp = await client.post(
                    f"{self._base_url}/store",  # 记忆存储端点
                    json={"content": content, "source": source},  # 存储内容和来源
                )
                resp.raise_for_status()  # 检查HTTP状态码
                return True  # 存储成功
                
        except Exception as e:
            # 3. 异常静默处理 (Silent Exception Handling)
            # 记忆存储失败不应该影响主业务流程，只记录debug日志
            logger.debug("记忆存储失败（不影响主流程）: %s", str(e))
            return False  # 静默返回失败状态


# 模块级单例实例 (Module-level Singleton Instance)
# 创建全局记忆客户端实例，供其他模块直接导入使用
# 单例模式确保应用内共享同一个客户端连接，减少HTTP连接开销
memory_client = MemoryClient()
