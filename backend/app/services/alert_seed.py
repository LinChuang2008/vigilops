"""
内置告警规则初始化模块。

在应用启动时向数据库插入预定义的告警规则（CPU、内存、磁盘、主机离线、服务不可用），
仅在规则不存在时插入，避免重复。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertRule

# 内置告警规则定义列表
BUILTIN_RULES = [
    {
        "name": "CPU 使用率过高",
        "description": "CPU 使用率超过阈值持续一段时间",
        "severity": "warning",
        "metric": "cpu_percent",
        "operator": ">",
        "threshold": 90.0,
        "duration_seconds": 300,
        "target_type": "host",
        "is_builtin": True,
    },
    {
        "name": "内存使用率过高",
        "description": "内存使用率超过阈值",
        "severity": "warning",
        "metric": "memory_percent",
        "operator": ">",
        "threshold": 90.0,
        "duration_seconds": 300,
        "target_type": "host",
        "is_builtin": True,
    },
    {
        "name": "磁盘使用率过高",
        "description": "磁盘使用率超过阈值",
        "severity": "critical",
        "metric": "disk_percent",
        "operator": ">",
        "threshold": 95.0,
        "duration_seconds": 0,
        "target_type": "host",
        "is_builtin": True,
    },
    {
        "name": "主机离线",
        "description": "主机心跳丢失",
        "severity": "critical",
        "metric": "host_offline",
        "operator": "==",
        "threshold": 1.0,
        "duration_seconds": 0,
        "target_type": "host",
        "is_builtin": True,
    },
    {
        "name": "服务不可用",
        "description": "服务健康检查失败",
        "severity": "critical",
        "metric": "service_down",
        "operator": "==",
        "threshold": 1.0,
        "duration_seconds": 0,
        "target_type": "service",
        "is_builtin": True,
    },
]


async def seed_builtin_rules(session: AsyncSession):
    """将内置告警规则写入数据库，跳过已存在的规则。"""
    result = await session.execute(
        select(AlertRule).where(AlertRule.is_builtin == True)  # noqa: E712
    )
    existing = {r.name for r in result.scalars().all()}

    for rule_data in BUILTIN_RULES:
        if rule_data["name"] not in existing:
            session.add(AlertRule(**rule_data))

    await session.commit()
