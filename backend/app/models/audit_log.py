"""
审计日志模型 (Audit Log Model)

记录用户在系统中的关键操作行为，用于安全审计、合规追踪和操作回溯。
详细记录操作类型、资源信息、IP 地址等关键信息，确保系统操作的可追溯性。

Records key user operations in the system for security auditing, compliance tracking,
and operation traceability. Captures operation types, resource information,
IP addresses, and other critical details to ensure system operation auditability.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """
    审计日志表 (Audit Log Table)
    
    记录用户在系统中执行的所有关键操作，包括创建、修改、删除等行为。
    每条记录包含操作用户、操作类型、目标资源和操作详情等信息，用于安全审计和问题排查。
    
    Table for recording all critical user operations in the system, including create,
    update, delete, and other actions. Each record contains the operating user,
    operation type, target resource, and operation details for security auditing and troubleshooting.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 操作用户 ID (Operating User ID)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 操作类型，如 create, update, delete (Action Type)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 资源类型，如 host, service, alert (Resource Type)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 资源 ID (Resource ID)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 操作详情描述 (Operation Detail Description)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # 操作者 IP 地址（支持 IPv6） (IP Address)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # 操作时间 (Operation Time)
