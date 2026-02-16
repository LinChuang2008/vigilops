from datetime import datetime, time
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, JSON, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")  # critical/warning/info
    metric: Mapped[str] = mapped_column(String(100), nullable=False)  # cpu_percent, memory_percent, disk_percent, etc.
    operator: Mapped[str] = mapped_column(String(10), nullable=False, default=">")  # >, <, >=, <=, ==, !=
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)  # must exceed for N seconds
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default="host")  # host / service
    target_filter: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # optional filter: {"group": "prod"}
    # F069: log keyword alert fields
    rule_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="metric")  # metric/log_keyword/db_metric
    log_keyword: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    log_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    log_service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # F071: database alert fields
    db_metric_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # connections_total, slow_queries, etc.
    db_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # monitored_databases.id
    # Phase 2.5: cooldown + silence
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300)
    silence_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    silence_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    host_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    service_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical/warning/info
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="firing")  # firing/resolved/acknowledged
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # user_id
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
