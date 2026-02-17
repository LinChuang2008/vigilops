"""
Redis 连接模块

管理 Redis 客户端的创建和关闭，提供全局单例访问。
"""
import redis.asyncio as redis

from app.core.config import settings

# 全局 Redis 客户端实例
redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """获取 Redis 客户端实例，首次调用时自动创建连接。"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


async def close_redis() -> None:
    """关闭 Redis 连接，释放资源。"""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
