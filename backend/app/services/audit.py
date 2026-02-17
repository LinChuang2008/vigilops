"""
审计日志工具函数

提供统一的审计日志记录接口，供各路由模块调用。
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """记录一条审计日志。

    Args:
        db: 数据库会话
        user_id: 操作用户 ID
        action: 操作类型，如 login / create_user / update_user 等
        resource_type: 资源类型，如 user / alert / alert_rule 等
        resource_id: 被操作资源的 ID
        detail: JSON 格式的变更详情
        ip_address: 客户端 IP 地址
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
