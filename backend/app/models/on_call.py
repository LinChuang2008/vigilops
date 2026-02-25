"""
值班排期模型 (On-Call Schedule Model)

定义值班组和值班排期的数据结构，支持多值班组管理和灵活的排期配置。
包含值班组信息管理、成员排期安排、临时调班等功能的数据模型。

Defines data structures for on-call groups and schedules, supporting
multi-group management and flexible scheduling configuration.
"""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OnCallGroup(Base):
    """
    值班组表 (On-Call Group Table)
    
    管理不同的值班小组，每个小组负责特定的业务领域或系统模块。
    支持值班组的基本信息管理和状态控制。
    
    Table for managing different on-call groups, each responsible for
    specific business domains or system modules.
    """
    __tablename__ = "on_call_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 值班组名称 (Group Name)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 值班组描述 (Group Description)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否激活 (Is Active)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 创建时间 (Creation Time)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 更新时间 (Update Time)


class OnCallSchedule(Base):
    """
    值班排期表 (On-Call Schedule Table)
    
    记录具体的值班安排，包括值班人员、值班时间段等信息。
    支持按日期范围安排值班，实现灵活的轮班制度。
    
    Table for recording specific on-call arrangements, including
    on-call personnel and time periods. Supports flexible shift scheduling.
    """
    __tablename__ = "on_call_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    group_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 值班组 ID (Group ID)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 值班用户 ID (User ID)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)  # 值班开始日期 (Start Date)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)  # 值班结束日期 (End Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否激活 (Is Active)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # 创建时间 (Creation Time)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # 更新时间 (Update Time)