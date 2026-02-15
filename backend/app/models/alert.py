from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")  # critical/warning/info
    metric: Mapped[str] = mapped_column(String(100), nullable=False)  # cpu_percent, memory_percent, disk_percent, etc.
    operator: Mapped[str] = mapped_column(String(10), nullable=False, default=">")  # >, <, >=, <=, ==, !=
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)  # must exceed for N seconds
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default="host")  # host / service
    target_filter: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # optional filter: {"group": "prod"}
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
    host_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    service_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical/warning/info
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="firing")  # firing/resolved/acknowledged
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[int | None] = mapped_column(Integer, nullable=True)  # user_id
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
