"""
告警聚合模型 (Alert Aggregation Model)

定义告警去重和聚合的表结构，防止告警风暴和重复告警。
支持基于时间窗口、规则相似性、主机/服务等维度的告警聚合。

Defines table structures for alert deduplication and aggregation to prevent alert storms
and duplicate alerts. Supports aggregation based on time windows, rule similarity,
and host/service dimensions.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.core.database import Base


class AlertGroup(Base):
    """
    告警聚合组表 (Alert Aggregation Group Table)
    
    管理聚合的告警组，将相似的告警合并到一个组中统一处理。
    减少告警噪音，提高运维效率。
    
    Table for managing aggregated alert groups, merging similar alerts
    into a single group for unified processing. Reduces alert noise
    and improves operational efficiency.
    """
    __tablename__ = "alert_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID
    group_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)  # 聚合键（规则+主机+服务等）
    title: Mapped[str] = mapped_column(String(500), nullable=False)  # 聚合告警标题
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 聚合描述
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # 最高严重程度
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="firing")  # 状态：firing/resolved/acknowledged
    alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 聚合的告警数量
    
    # 聚合维度信息
    rule_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # 涉及的规则 ID 列表
    host_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # 涉及的主机 ID 列表
    service_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # 涉及的服务 ID 列表
    
    # 聚合窗口控制
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # 聚合窗口开始时间
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # 聚合窗口结束时间
    last_occurrence: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # 最后一次告警时间
    
    # 通知控制
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已发送通知
    notification_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # 通知发送时间
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AlertDeduplication(Base):
    """
    告警去重记录表 (Alert Deduplication Record Table)
    
    记录告警的去重信息，防止短时间内重复创建相同的告警。
    
    Table for recording alert deduplication information to prevent
    creating duplicate alerts in a short time period.
    """
    __tablename__ = "alert_deduplications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)  # 告警指纹（规则+主机+服务的哈希）
    rule_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 告警规则 ID
    host_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # 主机 ID
    service_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # 服务 ID
    
    first_occurrence: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # 首次触发时间
    last_occurrence: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # 最后触发时间
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 触发次数
    
    # 去重控制
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否被抑制
    suppression_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 抑制原因
    
    # 关联的告警组
    alert_group_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("alert_groups.id"), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# 修改现有 Alert 模型，添加去重和聚合支持
# 注意：这需要通过数据库迁移来添加字段，暂时在这里定义结构

"""
为现有 Alert 表添加的字段（需要数据库迁移）:

- fingerprint: String(255), nullable=True, index=True  # 告警指纹
- alert_group_id: Integer, ForeignKey("alert_groups.id"), nullable=True  # 所属告警组
- is_deduplicated: Boolean, default=False  # 是否为去重告警
- deduplication_count: Integer, default=0  # 去重次数
"""