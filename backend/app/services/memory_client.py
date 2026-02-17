"""运维记忆客户端，连接小强记忆系统 API。"""
import httpx
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryClient:
    """记忆系统客户端，提供 store/recall 操作。"""

    @property
    def _base_url(self) -> str:
        """获取记忆系统 API 基地址。"""
        return settings.memory_api_url

    @property
    def _enabled(self) -> bool:
        """检查记忆功能是否启用。"""
        return settings.memory_enabled

    async def recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """召回相关运维记忆。

        Args:
            query: 搜索关键词
            top_k: 返回最相关的前 N 条记忆

        Returns:
            相关记忆列表，失败时返回空列表
        """
        if not self._enabled:
            return []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base_url}/recall",
                    json={"query": query, "top_k": top_k},
                )
                resp.raise_for_status()
                data = resp.json()
                # 兼容不同返回格式
                if isinstance(data, list):
                    return data
                return data.get("memories", data.get("results", []))
        except Exception as e:
            logger.debug("记忆召回失败（不影响主流程）: %s", str(e))
            return []

    async def store(self, content: str, source: str = "vigilops") -> bool:
        """存储运维经验。

        Args:
            content: 要存储的文本内容
            source: 来源标识

        Returns:
            是否存储成功，失败时静默返回 False
        """
        if not self._enabled:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base_url}/store",
                    json={"content": content, "source": source},
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.debug("记忆存储失败（不影响主流程）: %s", str(e))
            return False


# 模块级单例
memory_client = MemoryClient()
