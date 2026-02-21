"""
VigilOps 自动修复系统 - 告警监听器
VigilOps Remediation System - Alert Event Listener

这是自动修复系统的事件驱动入口，负责监听 Redis PubSub 告警事件并触发修复流程。
This is the event-driven entry point of the remediation system, responsible for listening 
to Redis PubSub alert events and triggering remediation processes.

架构设计 (Architecture Design):
采用发布-订阅模式实现松耦合的事件驱动架构：
- 告警系统发布事件到 Redis 频道
- 监听器订阅频道并接收事件
- 收到事件后异步调用 RemediationAgent 处理

技术特性 (Technical Features):
- 异步非阻塞：使用 asyncio 确保高并发性能
- 故障隔离：单个告警处理失败不影响其他告警
- 优雅关闭：支持 SIGTERM 信号的优雅停机
- 延迟导入：避免循环依赖问题

配置控制 (Configuration Control):
- AGENT_ENABLED: 控制是否启用自动修复功能
- AGENT_DRY_RUN: 控制是否为测试模式
- Redis 连接配置通过全局设置管理

监听频道 (Monitored Channel):
- vigilops:alert:new: 新告警事件通知

事件格式 (Event Format):
{"alert_id": "12345", "host": "web01", "alert_type": "high_cpu", ...}

作者：VigilOps Team  
版本：v1.0
"""
import asyncio
import json
import logging

from app.core.redis import get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis PubSub 频道名称 - 新告警事件通知
# Redis PubSub channel name - new alert event notifications
CHANNEL = "vigilops:alert:new"


async def start_listener():
    """启动告警事件监听器 (Start Alert Event Listener)
    
    这是自动修复系统的主循环，负责持续监听 Redis PubSub 频道上的新告警事件。
    This is the main loop of the remediation system, responsible for continuously listening 
    to new alert events on Redis PubSub channels.
    
    工作流程 (Workflow):
    1. 连接到 Redis 并订阅告警频道
    2. 进入监听循环，等待告警事件
    3. 收到事件后解析 JSON 数据
    4. 验证事件格式和必要字段
    5. 创建 RemediationAgent 实例处理告警
    6. 异步执行修复流程，不阻塞监听循环
    
    错误处理 (Error Handling):
    - JSON 解析错误：记录警告并跳过该事件
    - 告警处理异常：记录错误但不中断监听
    - 连接断开：自动重连机制（由 Redis 客户端处理）
    
    生命周期管理 (Lifecycle Management):
    - 支持 asyncio.CancelledError 的优雅关闭
    - 关闭时自动取消订阅并清理资源
    - 适合作为后台任务长期运行
    
    配置依赖 (Configuration Dependencies):
    - settings.agent_dry_run: 控制修复模式（测试/生产）
    - Redis 连接配置：通过 get_redis() 获取
    
    注意事项 (Notes):
    - 使用延迟导入避免与 agent 模块的循环依赖
    - 每个告警事件创建新的 Agent 实例，确保状态隔离
    - 监听是阻塞操作，建议在独立的 asyncio Task 中运行
    """
    # 获取 Redis 连接实例 (Get Redis connection instance)
    redis = await get_redis()
    
    # 创建 PubSub 对象用于订阅消息 (Create PubSub object for message subscription)
    pubsub = redis.pubsub()
    
    # 订阅告警事件频道 (Subscribe to alert event channel)
    await pubsub.subscribe(CHANNEL)
    logger.info(f"Remediation listener subscribed to {CHANNEL}")

    try:
        # 主监听循环：持续接收和处理告警事件 (Main listening loop: continuously receive and process alert events)
        async for message in pubsub.listen():
            # 过滤非消息类型的事件（如订阅确认等） (Filter non-message type events like subscription confirmations)
            if message["type"] != "message":
                continue
                
            try:
                # 解析告警事件 JSON 数据 (Parse alert event JSON data)
                data = json.loads(message["data"])
                
                # 验证必要的告警 ID 字段 (Validate required alert ID field)
                alert_id = data.get("alert_id")
                if alert_id is None:
                    logger.warning("Received alert event without alert_id, skipping")
                    continue
                    
                logger.info(f"Received alert event: alert_id={alert_id}")
                
                # 延迟导入避免与 agent 模块的循环依赖 (Delayed import to avoid circular dependency with agent module)
                from app.remediation.agent import RemediationAgent
                
                # 创建修复 Agent 实例，使用配置的运行模式 (Create remediation agent instance with configured mode)
                agent = RemediationAgent(dry_run=settings.agent_dry_run)
                
                # 异步处理告警，不阻塞监听循环 (Process alert asynchronously without blocking listening loop)
                await agent.handle_alert(data)
                
            except Exception:
                # 单个告警处理失败不应中断整个监听服务 (Individual alert processing failure shouldn't interrupt entire listening service)
                logger.exception("Error handling alert event")
    except asyncio.CancelledError:
        # 接收到取消信号，开始优雅关闭 (Received cancellation signal, start graceful shutdown)
        logger.info("Remediation listener shutting down")
    finally:
        # 资源清理：取消订阅并关闭 PubSub 连接 (Resource cleanup: unsubscribe and close PubSub connection)
        await pubsub.unsubscribe(CHANNEL)  # 取消频道订阅 (Unsubscribe from channel)
        await pubsub.close()  # 关闭 PubSub 连接 (Close PubSub connection)
